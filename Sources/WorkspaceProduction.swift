import SwiftUI

/// Submitted settings are immutable. Both workspaces resolve the same video-bound
/// request before consulting editable defaults or an older review.
struct WorkspaceVoiceSelection:Equatable {
    let engines:[String],primary:String,languages:[String],includeOriginal:Bool
    let productionMode:String
    var languageMode:String {languages.count>1 ? "both":languages.first ?? "yue"}
    init?(_ cfg:[String:Any]) {
        let raw=cfg["selectedEngines"] as? [String] ?? (cfg["ttsBackend"] as? String).map {[$0]} ?? []
        engines=Array(NSOrderedSet(array:raw)) as? [String] ?? []
        guard !engines.isEmpty else{return nil}
        let preferred=cfg["defaultAudioEngine"] as? String ?? cfg["ttsBackend"] as? String ?? engines[0]
        primary=engines.contains(preferred) ? preferred:engines[0]
        languages=["yue","en"].filter {(cfg["dubLanguages"] as? [String] ?? ["yue"]).contains($0)}
        includeOriginal=cfg["includeOriginal"] as? Bool ?? true
        productionMode=cfg["productionMode"] as? String ?? "normal"
    }
}
extension AppModel {
    /// Keep editable project controls aligned with the shared defaults. Submitted
    /// requests remain immutable and are resolved separately by both workspaces.
    func synchronizeWorkspaceEngines() {
        guard !workspaceEngineSyncing,let review=projectEditor.document?.review,
              let selection=projectEditor.productionSelections[review] else{return}
        let engines=Set(selectedEngines)
        if selection.engines != engines {selection.engines=engines}
    }
    func submittedVoiceSelection(video:String?)->WorkspaceVoiceSelection? {
        guard let video else{return nil}
        func decode(_ data:Data)->[String:Any]? {WorkspaceRequestCache.decode(data)}
        func matches(_ cfg:[String:Any])->Bool {
            if let videos=cfg["videos"] as? [[String:Any]],!videos.isEmpty {return videos.contains {$0["video"] as? String==video}}
            return cfg["video"] as? String==video
        }
        let batches=(busy ? currentBatchRequest.map {[$0]} ?? []:[])+pendingBatchRequests
        for data in batches {if let cfg=decode(data),matches(cfg),let value=WorkspaceVoiceSelection(cfg) {return value}}
        for task in editorTasks where task.id==activeEditorTask || task.status=="queued" {
            let row=ProcessingAudioIndex.read(URL(fileURLWithPath:task.submission))
            guard row["previewOnly"] as? Bool != true,row["previewSegment"]==nil,let settings=row["settings"] as? [String:Any] else{continue}
            let review=ProcessingAudioIndex.read(URL(fileURLWithPath:task.review))
            let base=review["config"] as? [String:Any] ?? [:]
            let cfg=base.merging(settings) {_,new in new}
            if matches(cfg),let value=WorkspaceVoiceSelection(cfg) {return value}
        }
        return nil
    }
    func selectSimpleEngine(_ id:String) {
        guard !busy,VoiceEngineChoice.all.contains(where:{$0.id==id}) else{return}
        ttsBackend=id;reviewBackend=id;extraEngines=[]
        if let _=projectEditor.document {projectEditor.productionSelection(self).engines=[id];projectEditor.previewEngine=id}
        if id=="wsyue" {selectWorkspaceLanguage("yue")}
    }
    func selectWorkspaceLanguage(_ language:String) {
        guard !busy,["yue","en","both"].contains(language) else{return}
        if projectEditor.document != nil {projectEditor.setOutputDubMode(language);projectEditor.productionSelection(self).languages=Set(language=="both" ? ["yue","en"]:[language])}
        dubMode=language
    }
    var workspaceVoiceSelection:WorkspaceVoiceSelection {
        guard projectEditor.document != nil else{return WorkspaceVoiceSelection(outputSettings)!}
        let choices=projectEditor.productionSelection(self)
        let primary=choices.engines.contains(ttsBackend) ? ttsBackend:choices.engines.sorted().first ?? ttsBackend
        return WorkspaceVoiceSelection(["selectedEngines":choices.engines.isEmpty ? [primary]:choices.engines.sorted(),"defaultAudioEngine":primary,
            "dubLanguages":projectEditor.document?.dubLanguages ?? choices.languages.sorted(),"includeOriginal":choices.includeOriginal])!
    }
    func setWorkspaceOriginal(_ value:Bool) {
        includeOriginal=value
        if projectEditor.document != nil {projectEditor.productionSelection(self).includeOriginal=value}
    }
    var workspaceTranslationSource:String {projectEditor.document?.translationSource ?? projectEditor.config["translationSource"] as? String ?? translationSource}
    func setWorkspaceTranslationSource(_ value:String) {translationSource=value;projectEditor.update {$0.translationSource=value}}
    var workspaceOPDetect:Bool {projectEditor.document?.autoSkipOP ?? projectEditor.config["autoSkipOP"] as? Bool ?? autoSkipOP}
    var workspaceOPTranslate:Bool {projectEditor.document?.translateOPED ?? projectEditor.config["translateOPED"] as? Bool ?? translateOPED}
    func setWorkspaceOPDetect(_ value:Bool) {autoSkipOP=value;projectEditor.update {$0.autoSkipOP=value}}
    func setWorkspaceOPTranslate(_ value:Bool) {translateOPED=value;projectEditor.update {$0.translateOPED=value}}
    /// Preserve the user's old simple preference once, then use shared model
    /// settings in both modes. Never rewrite existing submitted jobs.
    func migrateSimpleVoiceSelection() {
        let defaults=UserDefaults.standard
        guard !defaults.bool(forKey:"sharedWorkspaceVoiceSelection") else{return}
        if (defaults.string(forKey:"studioInterfaceMode") ?? "simple")=="simple",let id=defaults.string(forKey:"simpleVoiceEngine"),!id.isEmpty {
            selectSimpleEngine(id)
            if let language=defaults.string(forKey:"simpleDubLanguage"),["yue","en","both"].contains(language) {dubMode=id=="wsyue" ? "yue":language}
            if defaults.object(forKey:"simpleKeepOriginal") != nil {includeOriginal=defaults.bool(forKey:"simpleKeepOriginal")}
        }
        defaults.set(true,forKey:"sharedWorkspaceVoiceSelection")
    }
}
struct StudioLanguagePicker:View {
    @AppStorage("studioLanguage") private var language="system"
    var body:some View {
        Menu {
            ForEach(["system","zh-HK","en"],id:\.self) {value in
                Button {language=value} label:{
                    HStack {Text(verbatim:value=="en" ? "English":value=="zh-HK" ? "香港繁體中文":L("跟隨系統"));if language==value {Image(systemName:"checkmark")}}
                }
            }
        } label: {
            HStack(spacing:7) {Image(systemName:"globe");Text(verbatim:language=="en" ? "English":language=="zh-HK" ? "香港繁體中文":L("跟隨系統"));Image(systemName:"chevron.down").font(.caption2)}.fixedSize()
        }.menuStyle(.borderlessButton).fixedSize().accessibilityLabel(L("介面語言")).help(L("介面語言"))
    }
}

extension AppModel {
    var simpleBatchPending:[BatchItem] {batchItems.filter {item in
        item.review==nil && item.output==nil && ["待處理","需要處理","已中斷，可重試","已暫停"].contains(item.status)
    }}
    /// Probe each source independently: stream indices from one episode must
    /// never be copied to another. Prepare all snapshots before starting workers.
    func submitSimpleBatch(_ plan:SimpleProductionPlan,selectedVideo:String?) {
        guard !busy,!simpleQueuePreparing else{return}
        do {try plan.validate();guard engineReady(plan.engine) else{throw AppFailure(message:L("請先在模型中心部署所選引擎。"))}}
        catch {self.error=error.localizedDescription;return}
        let items=simpleBatchPending
        guard !items.isEmpty else{return}
        let base=conversionConfig(URL(fileURLWithPath:items[0].video),start:0),probe=engine
        simpleQueuePreparing=true
        Task {
            defer {simpleQueuePreparing=false}
            do {
                let streams=try await Task.detached {() throws -> [String:[Int]] in
                    guard plan.subtitles.contains("original") else{return [:]}
                    var result:[String:[Int]]=[:]
                    for item in items where item.video != selectedVideo {
                        let raw=try probe.run(probe.ffprobe,["-v","error","-select_streams","s","-show_streams","-of","json",item.video])
                        let obj=try JSONSerialization.jsonObject(with:Data(raw.utf8)) as? [String:Any]
                        result[item.video]=(obj?["streams"] as? [[String:Any]] ?? []).compactMap {row in
                            guard let id=row["index"] as? Int else{return nil}
                            let track=SubtitleTrack(id:id,language:"",title:"",codec:row["codec_name"] as? String ?? "")
                            return track.supported ? id:nil
                        }
                    }
                    return result
                }.value
                guard !busy else{return}
                guard exportFolder.isEmpty || FileManager.default.isWritableFile(atPath:exportFolder) else{throw AppFailure(message:L("輸出資料夾唔存在或冇寫入權限，請重新選擇。"))}
                let scheduled=normalizeBatchRequests()
                let requests=try SimpleBatchRequests.make(plan:plan,items:items.filter {!scheduled.contains($0.id)},base:base,selectedVideo:selectedVideo,originalStreams:streams)
                pendingBatchRequests += requests;persistBatchRequests();resumeProcessing()
            } catch {self.error=error.localizedDescription}
        }
    }
}
enum SimpleBatchRequests {
    static func make(plan:SimpleProductionPlan,items:[BatchItem],base:[String:Any],selectedVideo:String?,originalStreams:[String:[Int]]) throws -> [Data] {
        try plan.validate()
        return try items.map {item in
            var current=plan
            if item.video != selectedVideo {current.originalStreams=originalStreams[item.video] ?? []}
            var cfg=base.merging(current.settings()) {_,new in new}
            cfg["video"]=item.video;cfg["videos"]=[["id":item.id,"video":item.video]]
            cfg["limit"]=0;cfg["startOffset"]=0;cfg["batchAutoSubtitles"]=true
            cfg["subtitleSource"]="burned";cfg["subtitle"]=NSNull();cfg["subtitleStream"] = -1;cfg["ocr"]=false
            return try JSONSerialization.data(withJSONObject:cfg)
        }
    }
}

extension SimpleWorkspace {
    var simpleListReservedHeight:CGFloat {model.batchItems.isEmpty ? 0:CGFloat(min(5,model.batchItems.count))*54+84}
    @ViewBuilder var batchList:some View {
        if !model.batchItems.isEmpty {
            VStack(alignment:.leading,spacing:10) {
                HStack {
                    Text(L("影片清單")+" (\(model.batchItems.count))").font(.headline)
                    Spacer()
                    if !model.busy,!model.simpleBatchPending.isEmpty {
                        Button {model.submitSimpleBatch(plan,selectedVideo:source)} label:{Text(L(model.simpleQueuePreparing ? "正在準備…":"開始全部待處理")+" (\(model.simpleBatchPending.count))")}
                            .disabled(model.simpleQueuePreparing || !model.engineReady(selectedEngine) || originalsLoading)
                            .help(L("其他影片會自動保留可用原片字幕軌。"))
                    }
                }
                ScrollViewReader {scroll in
                    ScrollView {
                        LazyVStack(spacing:0) {
                            ForEach(model.batchItems) {item in
                                HStack(spacing:8) {
                                    Button {
                                        if let row=editor.projects.first(where:{$0.id==item.id}) ?? editor.projects.first(where:{$0.video==item.video}) {editor.open(row);refreshPreview()}
                                    } label:{
                                        HStack(spacing:10) {
                                            Image(systemName:source==item.video ? "play.circle.fill":"film").foregroundStyle(source==item.video ? accent:Color.secondary)
                                            Text(URL(fileURLWithPath:item.video).lastPathComponent).lineLimit(2).multilineTextAlignment(.leading).frame(maxWidth:.infinity,alignment:.leading).help(item.video)
                                            Text(L(item.status=="待處理" ? "等候":item.status)).font(.caption).foregroundStyle(.secondary).frame(width:110,alignment:.trailing)
                                        }.padding(.leading,10).frame(maxWidth:.infinity,minHeight:54).contentShape(Rectangle())
                                    }.buttonStyle(.plain)
                                    Button(role:.destructive) {removeSimpleVideo(item)} label:{Label(L("移除"),systemImage:"trash")}
                                        .help(L("移除影片同處理資料，保留輸出成品")).disabled(model.busy || model.simpleQueuePreparing || model.simpleCleanupBusy)
                                        .padding(.trailing,10)
                                }.frame(height:54).id(item.id).background(source==item.video ? accent.opacity(0.08):Color.clear)
                                .overlay(alignment:.bottom) {Divider()}
                            }
                        }
                    }.frame(height:CGFloat(min(5,model.batchItems.count))*54)
                    .onChange(of:editor.selected) {id in if let id {withAnimation {scroll.scrollTo(id,anchor:.center)}}}
                }
                Text(L("移除會清理該片處理資料，保留成品同原片。")).font(.caption).foregroundStyle(.secondary)
            }.padding(12).background(StudioPalette.panel,in:RoundedRectangle(cornerRadius:12))
            .disabled(model.simpleCleanupBusy)
        }
    }
}


extension AppModel {
    /// Welcome sets defaults for future submissions, never the selected draft or frozen jobs.
    func applyWelcomeLanguageDefaults(_ language:String,force:Bool=false) {
        let english=language=="en" || (language=="system" && Locale.preferredLanguages.first?.hasPrefix("en")==true)
        guard english,force || !UserDefaults.standard.bool(forKey:"welcomeEnglishDefaults.v1") else{return}
        UserDefaults.standard.set(true,forKey:"welcomeEnglishDefaults.v1")
        dubMode="both";includeOriginal=true;subtitleOutput="separate";burnOutputCaptions=false
        UserDefaults.standard.set("yue,english",forKey:"simpleSubtitleModes")
        saveStudioPreset()
    }
}
