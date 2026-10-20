import SwiftUI
import AVKit
import UniformTypeIdentifiers

struct BatchItem: Codable, Identifiable {
    var id = UUID().uuidString
    var video: String
    var status = "待處理"
    var message = ""
    var review: String?
    var previewJob: String? = nil
    var output: String?
    var manualApproval: Bool? = nil
    var startOverride: Double? = nil
    var limitOverride: Int? = nil
    var subtitleOverride: String? = nil
    var subtitlePath: String? = nil
    var subtitleIndex: Int? = nil
    var ocrRectOverride: [String:Double]? = nil
}

extension AppModel {
    var batchNeedsAttention:Bool {batchItems.contains {$0.status=="需要處理" && !$0.message.isEmpty}}
    func removeBatchItem(id: String) {
        guard !busy else { return }
        batchItems.removeAll { $0.id == id }; persistBatch()
    }
    func requeueBatchItem(id: String) {
        guard !busy, let index = batchItems.firstIndex(where: { $0.id == id }) else { return }
        if let path=batchItems[index].review {
            projectEditor.refresh(self)
            if let row=projectEditor.projects.first(where:{$0.review?.path==path}) {projectEditor.open(row)}
            section = .history;return
        }
        batchItems[index].status = "待處理"; persistBatch()
    }
    func persistBatch() {
        try? JSONEncoder().encode(batchItems).write(to: engine.root.appendingPathComponent("batch-queue.json"), options: .atomic)
    }
    func loadBatch() {
        if let data = try? Data(contentsOf: engine.root.appendingPathComponent("batch-queue.json")),
           let saved = try? JSONDecoder().decode([BatchItem].self, from: data) {
            batchItems = saved.map { item in
                var item = item
                if item.status == "處理中" { item.status = "已中斷，可重試" }
                return item
            }
        }
    }
    func addBatch(_ urls: [URL]) {
        for url in urls where ["mp4", "mkv", "mov", "webm", "avi"].contains(url.pathExtension.lowercased()) {
            if !batchItems.contains(where: { $0.video == url.path }) { batchItems.append(BatchItem(video: url.path)) }
        }
        persistBatch(); section = .studio; projectEditor.refresh(self)
    }
    func chooseBatch() {
        let panel = NSOpenPanel(); panel.allowsMultipleSelection = true
        panel.allowedContentTypes = [.movie, UTType(filenameExtension: "mkv")!]
        if panel.runModal() == .OK { addBatch(panel.urls) }
    }
    func conversionConfig(_ video: URL, start: Double) -> [String:Any] {
        var cfg: [String:Any] = ["video":video.path, "subtitle":subtitleSource == "external" ? (subtitle?.path as Any? ?? NSNull()) : NSNull(), "subtitleSource":subtitleSource, "subtitleStream":subtitleStream, "storage":engine.root.path, "ffmpeg":engine.ffmpeg.path, "ffprobe":engine.ffprobe.path, "executable":Bundle.main.executableURL!.path, "translate":translate, "model":selectedModel, "port":engine.port, "limit":limit, "startOffset":start, "ocr":subtitleSource == "burned", "mixOriginal":mixOriginal, "autoApprove":autoApprove, "speechTiming":translate, "autoFit":autoFit, "burnOutputCaptions":burnOutputCaptions]
        cfg.merge(outputSettings) { _,new in new }
        cfg["subtitleLanguage"] = subtitleTracks.first(where: { $0.id == subtitleStream })?.language
        cfg["subtitleTitle"] = subtitleTracks.first(where: { $0.id == subtitleStream })?.title
        cfg.merge(ocrSettings) { _,new in new }; cfg.merge(dubbingSettings) { _,new in new }
        return ProductionModePolicy.applying(to:cfg)
    }
    func startBatch() {
        guard !busy else {return}
        reconcileBatchProjects()
        guard validateDubbing(), let start = startSeconds else { return }
        queuePaused=false
        let pending = batchItems.filter { $0.status == "待處理" || $0.status == "需要處理" || $0.status == "已中斷，可重試" || $0.status == "已暫停" }
        guard let first = pending.first else { if hasSavedWork {resumeProcessing()} else {error = "冇待處理影片。可以加入影片或按重試。"}; return }
        var cfg = conversionConfig(URL(fileURLWithPath: first.video), start: start)
        cfg["batchAutoSubtitles"] = batchAutoSubtitles
        if batchAutoSubtitles && subtitleSource == "none" { cfg["subtitleSource"] = "burned" }
        let scheduled = normalizeBatchRequests()
        pendingBatchRequests += pending.filter { !scheduled.contains($0.id) }.map { item in
            var current=cfg
            if let manual=item.manualApproval {current["autoApprove"] = !manual}
            if let start=item.startOverride {current["startOffset"]=start}
            if let limit=item.limitOverride {current["limit"]=limit}
            if let source=item.subtitleOverride {current["subtitleSource"]=source;current["batchAutoSubtitles"]=false;current["subtitle"]=NSNull();current["ocr"] = source=="burned"}
            if item.subtitleOverride=="external",let path=item.subtitlePath {current["subtitle"]=path;current["batchExplicitSubtitle"]=true}
            if item.subtitleOverride=="embedded",let index=item.subtitleIndex {current["subtitleStream"]=index;current["batchExplicitStream"]=true}
            if let rect=item.ocrRectOverride {current["ocrRect"]=rect}
            current["videos"]=[["id":item.id,"video":item.video]]
            return try! JSONSerialization.data(withJSONObject:current)
        }
        persistBatchRequests();resumeProcessing()
    }
    @discardableResult func normalizeBatchRequests()->Set<String> {
        var scheduled=Set<String>()
        pendingBatchRequests=pendingBatchRequests.compactMap { data in
            guard var cfg=try? JSONSerialization.jsonObject(with:data) as? [String:Any],let videos=cfg["videos"] as? [[String:Any]] else{return nil}
            let bound=videos.compactMap { video -> [String:Any]? in
                guard let path=video["video"] as? String,let item=batchItems.first(where:{$0.video==path}),item.output==nil,scheduled.insert(item.id).inserted else{return nil}
                return ["id":item.id,"video":item.video]
            }
            guard !bound.isEmpty else{return nil};cfg["videos"]=bound
            return try? JSONSerialization.data(withJSONObject:cfg)
        }
        persistBatchRequests();return scheduled
    }
    func reconcileBatchProjects() {
        var changed=false
        for i in batchItems.indices where batchItems[i].review==nil {
            let item=batchItems[i]
            let candidates=savedDrafts.filter { draft in
                guard let data=try? Data(contentsOf:draft.url),let obj=try? JSONSerialization.jsonObject(with:data) as? [String:Any],let cfg=obj["config"] as? [String:Any],cfg["video"] as? String==item.video else{return false}
                if let start=item.startOverride,abs((cfg["startOffset"] as? Double ?? 0)-start) > 0.001 {return false}
                if let limit=item.limitOverride,cfg["limit"] as? Int != limit {return false}
                return true
            }
            // Ambiguous variants require an explicit choice; never attach a different cut.
            guard candidates.count==1,let draft=candidates.first else{continue}
            batchItems[i].review=draft.url.path;changed=true
        }
        for i in batchItems.indices {
            guard let path=batchItems[i].review,let bytes=try? Data(contentsOf:URL(fileURLWithPath:path)),let review=try? JSONSerialization.jsonObject(with:bytes) as? [String:Any] else{continue}
            let reportPath=URL(fileURLWithPath:path).deletingLastPathComponent().appendingPathComponent("report.json")
            let report=(try? JSONSerialization.jsonObject(with:Data(contentsOf:reportPath))) as? [String:Any] ?? [:]
            let exported=report["exportedOutput"] as? String ?? report["output"] as? String
            let output=exported.flatMap {FileManager.default.fileExists(atPath:$0) ? $0:nil}
            let status:String
            if output != nil {status=review["status"] as? String=="partial" || report["qualityStatus"] as? String=="needs-review" ? "已輸出，待覆核":"完成"}
            else if ["處理中","已暫停","已中斷，可重試","需要處理"].contains(batchItems[i].status) {continue}
            else {let cfg=review["config"] as? [String:Any] ?? [:];status=cfg["autoApprove"] as? Bool==true ? "需要處理":"等待校稿"}
            if batchItems[i].output != output || batchItems[i].status != status {batchItems[i].output=output;batchItems[i].status=status;changed=true}
        }
        if changed {persistBatch()}
    }
    func persistBatchRequests() {
        do {try JSONEncoder().encode(pendingBatchRequests).write(to:engine.root.appendingPathComponent("batch-submissions.json"),options:.atomic)} catch {self.error=error.localizedDescription}
    }
    func pumpBatchRequests() {
        guard !busy,!queuePaused,!pendingBatchRequests.isEmpty else{return}
        let data=pendingBatchRequests[0]
        do {try data.write(to:engine.root.appendingPathComponent("batch-inflight.json"),options:.atomic)} catch {self.error=error.localizedDescription;return}
        currentBatchRequest=data;pendingBatchRequests.removeFirst();persistBatchRequests()
        guard let cfg=try? JSONSerialization.jsonObject(with:data) as? [String:Any] else{return}
        launchBatchRequest(cfg)
    }
    func launchBatchRequest(_ cfg:[String:Any]) {
        let data = try! JSONSerialization.data(withJSONObject: cfg), e = engine, automatic = cfg["autoSpeakers"] as? Bool ?? false, useAI = (cfg["translate"] as? Bool ?? true) || ["english","dual","all","original-english","complete"].contains(cfg["subtitleOutput"] as? String ?? ""), model = cfg["model"] as? String ?? selectedModel
        player.pause(); audioPlayer.pause(); batchRunning = true;activePreviewJob=nil;section = .studio
        task("開始批量處理",timingConfiguration:cfg) {
            if !e.runtimeReady { try e.installRuntime() }
            if automatic { try e.ensureAutoSpeakers(independent:cfg["roleAnalysisMode"] as? String=="independent") }
            if useAI { try e.ensureSpeechTiming(qualityChecks:cfg["productionMode"] as? String != "fast"); try e.startTextModel(model); guard e.availableModels().contains(model) else { throw AppFailure(message: "請先下载選用嘅翻譯模型。") } }
            try e.worker("batch", config: try JSONSerialization.jsonObject(with: data) as! [String:Any])
        }
    }
    func rebuildDialogue() {
        guard !busy, let reviewURL else { return }
        do { try saveScript() } catch { self.error = error.localizedDescription; return }
        let e = engine
        task("按日語原聲重建稿") {
            try e.ensureSpeechTiming()
            try e.ensureAutoSpeakers()
            try e.worker("rebuild-dialogue", config: ["review":reviewURL.path])
        }
    }
    func autoAssignReview() {
        guard !busy, let reviewURL else { return }
        do { try saveScript() } catch { self.error = error.localizedDescription; return }
        let e = engine
        task("自動配對全部角色") {
            try e.ensureAutoSpeakers()
            try e.worker("auto-speakers", config: ["review":reviewURL.path])
        }
    }
    func detectOP() {
        guard let video else { return }
        let e = engine
        task("分析頭 5 分鐘嘅 OP") {
            if !e.runtimeReady { try e.installRuntime() }
            try e.worker("detect-op", config: ["video":video.path, "ffprobe":e.ffprobe.path, "ffmpeg":e.ffmpeg.path, "storage":e.root.path, "executable":Bundle.main.executableURL!.path])
        }
    }
}

extension ContentView {
    var batchQueue: some View {BatchQueueView(m:m)}
    var batchActions: some View {
        HStack {
            Text("\(m.batchItems.count) 集").font(.caption).foregroundStyle(.secondary)
            Text(LocalizedStringKey(m.autoApprove ? "自動翻譯 → 配音 → 輸出" : "手動校對模式：配音前會暫停")).font(.caption)
            Spacer()
            if !m.pendingBatchRequests.isEmpty {Button(L("繼續已保存排程")) {m.resumeWorkspaceProcessing()}.disabled(m.busy);Button(L("清除未開始排程")) {m.pendingBatchRequests=[];m.persistBatchRequests()}.disabled(m.busy)}
            Button(m.batchItems.filter {$0.status=="待處理" || $0.status=="需要處理" || $0.status=="已中斷，可重試"}.count>1 ? "開始處理佇列":"開始轉換",action:m.startBatch).buttonStyle(.borderedProminent).disabled(m.busy || m.batchItems.isEmpty || !m.pendingBatchRequests.isEmpty)
        }
    }
    var batchView: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                Text(L("一次加入多集，逐集喺本機處理")).font(.title2.bold())
                Spacer(); Button(L("加入多條影片"), action: m.chooseBatch).disabled(m.busy)
            }
            Text(L("全局設定作為新工作預設；字幕準備好後可隨時進入影片編輯，逐集批准或提交修改。")).font(.caption).foregroundStyle(.secondary)
            ViewThatFits(in:.horizontal) {
                HStack(alignment:.top,spacing:16) {
                    batchQueue.frame(minWidth:400,maxWidth:.infinity)
                    essentialSettings.frame(width:340)
                }
                VStack(spacing:16) { essentialSettings;batchQueue }
            }
        }.onDrop(of: [.fileURL], isTargeted: nil) { providers in
            guard !m.busy else { return false }
            for p in providers { _ = p.loadObject(ofClass: URL.self) { url,_ in if let url { Task { @MainActor in m.addBatch([url]) } } } }
            return true
        }
    }
}

extension AppModel {
    func inspectBatchSubtitles(_ item:BatchItem) {
        let e=Engine(port:engine.port)
        Task {
            do {
                let info=try await Task.detached {try e.inspectVideo(URL(fileURLWithPath:item.video))}.value
                batchSubtitleTracks[item.id]=info.tracks
                if let i=batchItems.firstIndex(where:{$0.id==item.id}),batchItems[i].subtitleIndex==nil {batchItems[i].subtitleIndex=info.tracks.first(where:{$0.supported})?.id;persistBatch()}
            } catch {self.error=error.localizedDescription}
        }
    }
}

struct BatchQueueView:View {
    @ObservedObject var m:AppModel
    var body: some View {
        VStack(alignment:.leading,spacing:12) {
            Label(L("轉換佇列"),systemImage:"list.bullet.rectangle").font(.headline)
            Toggle(L("逐集自動選字幕（同名外掛 → 內置字幕 → 畫面 OCR）"),isOn:$m.batchAutoSubtitles).disabled(m.busy)
            Text(L("字幕方框同起點會套用到每集；不同片源可以先用個別影片檢查設定。")).font(.caption).foregroundStyle(.secondary)
            if m.batchItems.isEmpty { Text(L("加入 MP4／MKV，或者將多條影片拖入呢度。")).frame(maxWidth: .infinity, minHeight: 180).card() }
            ForEach(m.batchItems) { item in
                VStack(alignment: .leading, spacing: 10) {
                    HStack {
                        Text(URL(fileURLWithPath: item.video).lastPathComponent).font(.headline)
                        Spacer(); Text(L(item.status)).foregroundStyle(.secondary)
                    }
                    if let i=m.batchItems.firstIndex(where:{$0.id==item.id}) {
                        DisclosureGroup(L("本片設定（未開始前套用）")) {
                            Button(L("重設為全局設定")) {m.batchItems[i].manualApproval=nil;m.batchItems[i].startOverride=nil;m.batchItems[i].limitOverride=nil;m.batchItems[i].subtitleOverride=nil;m.batchItems[i].subtitlePath=nil;m.batchItems[i].subtitleIndex=nil;m.batchItems[i].ocrRectOverride=nil;m.persistBatch()}
                            Toggle(L("本片需要手動批核"),isOn:Binding(get:{m.batchItems[i].manualApproval ?? !m.autoApprove},set:{m.batchItems[i].manualApproval=$0;m.persistBatch()}))
                            HStack {
                                Text(L("開始（秒）"));TextField(L("開始"),value:Binding(get:{m.batchItems[i].startOverride ?? m.startSeconds ?? 0},set:{m.batchItems[i].startOverride=$0;m.persistBatch()}),format:.number).frame(width:80)
                                Text(L("長度（0＝全片）"));TextField(L("長度"),value:Binding(get:{m.batchItems[i].limitOverride ?? m.limit},set:{m.batchItems[i].limitOverride=$0;m.persistBatch()}),format:.number).frame(width:80)
                            }
                            Picker(L("字幕來源"),selection:Binding(get:{m.batchItems[i].subtitleOverride ?? "auto"},set:{m.batchItems[i].subtitleOverride=$0=="auto" ? nil:$0;m.persistBatch()})) {
                                Text(L("繼承自動／全局")).tag("auto");Text(L("內置字幕")).tag("embedded");Text(L("外掛字幕")).tag("external");Text(L("畫面 OCR")).tag("burned");Text(L("無字幕")).tag("none")
                            }
                            if item.subtitleOverride=="embedded" {
                                Button(L("讀取本片字幕軌")) {m.inspectBatchSubtitles(item)}
                                if let tracks=m.batchSubtitleTracks[item.id] {
                                    Picker(L("本片字幕軌"),selection:Binding(get:{m.batchItems[i].subtitleIndex ?? tracks.first?.id ?? -1},set:{m.batchItems[i].subtitleIndex=$0;m.persistBatch()})) {ForEach(tracks.filter(\.supported)) {track in Text(track.label).tag(track.id)}}
                                    if tracks.filter(\.supported).isEmpty {Text(L("未有可用文字字幕軌")).font(.caption).foregroundStyle(.orange)}
                                }
                            }
                            if item.subtitleOverride=="external" {Button(item.subtitlePath.map{URL(fileURLWithPath:$0).lastPathComponent} ?? L("選擇本片字幕")) {let p=NSOpenPanel();p.allowedContentTypes=[UTType(filenameExtension:"srt")!,UTType(filenameExtension:"ass")!,UTType(filenameExtension:"vtt")!];if p.runModal() == .OK,let url=p.url {m.batchItems[i].subtitlePath=url.path;m.persistBatch()}}}
                            if item.subtitleOverride=="burned" {Button(L("套用工作區目前 OCR 範圍")) {m.batchItems[i].ocrRectOverride=m.ocrRegion.config;m.persistBatch()}}
                        }.disabled(m.busy)
                    }
                    if !item.message.isEmpty { Text(item.message).font(.caption).foregroundStyle(.orange).textSelection(.enabled) }
                    HStack {
                        Button(L("用呢集檢查設定")) {m.loadVideo(URL(fileURLWithPath:item.video));m.projectEditor.refresh(m);if let row=m.projectEditor.projects.first(where:{$0.id==item.id}) {m.projectEditor.open(row)};m.section = .studio}
                        if let path = item.review { Button(L("編輯／批核／成品")) { m.projectEditor.refresh(m); if let row=m.projectEditor.projects.first(where:{$0.review?.path==path}) {m.projectEditor.open(row)};m.section = .history } }
                        if let path = item.output { Button(L("播放成品")) { let url = URL(fileURLWithPath: path); m.output = url; m.preview(url, isOutput: true); m.section = .studio } }
                        Spacer()
                        if item.status != "待處理" { Button(L(item.review == nil ? "重新排隊" : "修改後重新排程")) { m.requeueBatchItem(id:item.id) } }
                        Button(L("移出清單")) { m.removeBatchItem(id:item.id) }
                    }
                }.card()
            }
        }
    }
}
