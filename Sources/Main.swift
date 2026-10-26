import SwiftUI
import AVKit
import UniformTypeIdentifiers
import Vision

// A local OCR helper uses Apple's Vision framework. It never sends frames anywhere.
func runOCR() {
    let folder=URL(fileURLWithPath:CommandLine.arguments[2])
    let rows=subtitleOCRRows(folder,recognize:recognizeSubtitleFrame)
    let data=(try? JSONSerialization.data(withJSONObject:rows)) ?? Data("[]".utf8)
    FileHandle.standardOutput.write(data)
}

#if !PREVIEW_QA
@main struct Launcher {
    static func main() {
        runManagedToolIfNeeded()
        if runSharedStudioBridgeIfNeeded() {return}
        if CommandLine.arguments.count > 1 && ["--traditional-text", "--simplified-text"].contains(CommandLine.arguments[1]) {
            let data = FileHandle.standardInput.readDataToEndOfFile()
            guard let text = String(data: data, encoding: .utf8) else { exit(1) }
            let result = text.applyingTransform(StringTransform("Simplified-Traditional"), reverse: CommandLine.arguments[1] == "--simplified-text") ?? text
            FileHandle.standardOutput.write(Data(result.utf8))
            return
        }
        if CommandLine.arguments.count > 2 && ["--classify-opening", "--classify-performance"].contains(CommandLine.arguments[1]) {
            do { try classifyOpeningAudio(CommandLine.arguments[2], detailed: CommandLine.arguments[1] == "--classify-performance") }
            catch { fputs("聲音分類失敗：\(error.localizedDescription)\n", stderr); exit(1) }
            return
        }
        if CommandLine.arguments.count > 2 && CommandLine.arguments[1] == "--render-subtitles" {
            do { try renderSubtitleImages(URL(fileURLWithPath:CommandLine.arguments[2])) }
            catch { FileHandle.standardError.write(Data(error.localizedDescription.utf8)); exit(1) }
            return
        }
        if CommandLine.arguments.count > 2 && CommandLine.arguments[1] == "--ocr" { runOCR(); return }
        StudioThemeChoice.restoreDefaultIfNeeded()
        if UserDefaults.standard.bool(forKey:"randomAnimeTheme") {
            let allowed = (UserDefaults.standard.string(forKey:"randomThemes") ?? "energy,ocean,ninja,retro,forest,future").split(separator:",").map(String.init)
            UserDefaults.standard.set(allowed.randomElement() ?? "studio",forKey:"animeTheme")
        }
        CantoApp.main()
    }
}

#endif

struct CantoApp: App {
    @NSApplicationDelegateAdaptor(CantoAppDelegate.self) var appDelegate
    @StateObject var model = AppModel()
    var body: some Scene {
        WindowGroup {
            ContentView().environmentObject(model)
                .frame(minWidth: 1280, minHeight: 820)
                .onAppear { appDelegate.engine = model.engine; appDelegate.model = model; DesktopPet.shared.start(model:model) }
                .onDisappear { DesktopPet.shared.stop() }
        }
        .windowStyle(.hiddenTitleBar)
        .defaultSize(width: 1680, height: 1050)
        .commands { CommandGroup(replacing: .appInfo) { Button("About AniCanto") { model.showAbout = true; NSApp.activate(ignoringOtherApps:true) } }; CommandGroup(replacing: .newItem) { Button(L("匯入影片…")) { model.chooseVideo() }.keyboardShortcut("o") } }
    }
}

final class CantoAppDelegate: NSObject, NSApplicationDelegate {
    var engine: Engine?
    weak var model: AppModel?
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
    func applicationWillTerminate(_ notification: Notification) { model?.saveWorkspaceForExit(); DesktopPet.shared.stop(); engine?.shutdown() }
}

enum Section: String, CaseIterable {
    case studio = "影片工作區", batch = "批量影片", voices = "角色與聲線", script = "字幕編輯", environment = "環境與模型", history = "影片編輯與成品", settings = "設定與關於", presets = "製作預設", projects = "專案／成品管理"
    var icon: String { switch self { case .studio: return "film.stack"; case .batch: return "list.bullet.rectangle"; case .voices: return "person.wave.2"; case .script: return "text.badge.checkmark"; case .environment: return "shippingbox"; case .history: return "clock.arrow.circlepath"; case .settings: return "slider.horizontal.3";case .presets:return "slider.horizontal.3";case .projects:return "folder" } }
}

struct ScriptCue: Codable, Identifiable {
    var start: Double
    var end: Double
    var sourceStart: Double?
    var sourceEnd: Double?
    var text: String
    var originalCantonese: String?
    var japanese: String?
    var subtitleHint: String?
    var timingSource: String?
    var asrConfidence: Double?
    var deliveryEnd: Double?
    var cantonese: String
    var enabled: Bool?
    var reviewNote: String?
    var speakerId: String?
    var speakerNote: String?
    var speechStart: Double?
    var speechEnd: Double?
    var id: String { "\(start)-\(end)-\(text)" }
    var included: Bool { get { enabled ?? true } set { enabled = newValue } }
    var timing: String {
        func stamp(_ value: Double) -> String { String(format: "%02d:%05.2f", Int(value) / 60, value.truncatingRemainder(dividingBy: 60)) }
        return "\(stamp(sourceStart ?? start)) → \(stamp(sourceEnd ?? end))"
    }
}

@MainActor final class AppModel: ObservableObject {
    @Published var downloadTransfer:DownloadTransfer?
    @Published var componentProgress:ComponentProgress?
    @Published var activeAudioTrack:AudioTrackProgress?
    @Published var audioSkipRequested=false
    @Published var presetSavedAt:Date?
    @Published var modelSelectionRevision=0
    let engine = Engine()
    let projectEditor = ProjectEditor()
    let workspaceOptions = ProjectWorkspaceOptions()
    let workspacePreview = LiveVideoPreview()
    @Published var editorTasks: [EditorialTask] = []
    var activeEditorTask: String?
    @Published var pendingBatchRequests: [Data] = []
    @Published var simpleQueuePreparing=false
    @Published var simpleCleanupBusy=false
    var currentBatchRequest: Data?
    @Published var queuePaused=false {didSet {try? JSONEncoder().encode(queuePaused).write(to:engine.root.appendingPathComponent("queue-paused.json"),options:.atomic)}}
    @Published var pauseRequested=false
    @Published var pauseStopping=false
    @Published var batchSubtitleTracks: [String:[SubtitleTrack]] = [:]

    @Published var section: Section = .studio
    @Published var video: URL?
    @Published var previewURL: URL?
    @Published var preparingPreview = false
    @Published var playbackError: String?
    @Published var subtitlePreviewMessage = ""
    @Published var previewCaptions: [PreviewCaption] = []
    private var subtitleRequest = UUID()
    @Published var subtitleTracks: [SubtitleTrack] = []
    @Published var translationSource=UserDefaults.standard.string(forKey:"translationSource") ?? "audio-and-subtitles" {didSet {UserDefaults.standard.set(translationSource,forKey:"translationSource")}}
    @Published var subtitleSource = "burned"
    @Published var subtitleStream = -1
    @Published var subtitle: URL?
    @Published var qwenModel = UserDefaults.standard.string(forKey:"qwenModel") ?? "qwen-0.6b-4bit" {didSet {UserDefaults.standard.set(qwenModel,forKey:"qwenModel");persistModelChoice("qwen-tts",qwenModel)}}
    @Published var cosyModel = (UserDefaults.standard.string(forKey:"cosyModel")=="cosy-0.5b-4bit" ? "cosy-native-0.5b" : UserDefaults.standard.string(forKey:"cosyModel") ?? "cosy-native-0.5b") {didSet {UserDefaults.standard.set(cosyModel,forKey:"cosyModel");persistModelChoice("cosyvoice3",cosyModel)}}
    @Published var voxcpmModel=UserDefaults.standard.string(forKey:"voxcpmModel") ?? "voxcpm2-2b-bf16" {didSet {UserDefaults.standard.set(voxcpmModel,forKey:"voxcpmModel");persistModelChoice("voxcpm2",voxcpmModel)}}
    @Published var wsyueModel=UserDefaults.standard.string(forKey:"wsyueModel") ?? "wsyue-cosy2-zjg" {didSet {UserDefaults.standard.set(wsyueModel,forKey:"wsyueModel");persistModelChoice("wsyue",wsyueModel)}}
    @Published var drama3Model=UserDefaults.standard.string(forKey:"drama3Model") ?? "drama3-35b-4bit" {didSet {UserDefaults.standard.set(drama3Model,forKey:"drama3Model");persistModelChoice("drama3",drama3Model)}}
    @Published var voxcpmDevice=UserDefaults.standard.string(forKey:"voxcpmDevice") ?? "mps" {didSet {UserDefaults.standard.set(voxcpmDevice,forKey:"voxcpmDevice")}}
    @Published var dubMode = UserDefaults.standard.string(forKey:"dubMode") ?? "yue" {didSet {UserDefaults.standard.set(dubMode,forKey:"dubMode")}}
    @Published var environmentCategory="presets"
    @Published var modelLibraryEngine="cosyvoice3"
    @Published var ttsBackend = VoiceEngineChoice.active(UserDefaults.standard.string(forKey: "ttsBackend") ?? StudioContract.catalog.defaultEngine) {
        didSet { UserDefaults.standard.set(ttsBackend, forKey: "ttsBackend");if oldValue != ttsBackend {synchronizeWorkspaceEngines()} }
    }
    var workspaceEngineSyncing=false
    @Published var extraEngines: Set<String> = [] {didSet {UserDefaults.standard.set(extraEngines.sorted(),forKey:"workspaceExtraEngines");if oldValue != extraEngines {synchronizeWorkspaceEngines()}}}
    @Published var includeOriginal = true {didSet {UserDefaults.standard.set(includeOriginal,forKey:"workspaceIncludeOriginal")}}
    @Published var pronunciationText = ""
    @Published var cantonesePronunciationText = ""
    @Published var subtitleOutput = "yue"
    @Published var burnSubtitleMode = "dual"
    var needsEnglishSubtitles: Bool { ["english","dual","all","original-english","complete","separate"].contains(subtitleOutput) || (burnOutputCaptions && ["english","dual","original-english"].contains(burnSubtitleMode)) }
    @Published var exportFolder = UserDefaults.standard.string(forKey: "exportFolder") ?? "" { didSet { UserDefaults.standard.set(exportFolder, forKey: "exportFolder") } }
    @Published var qwenTTSReady = false
    @Published var customTextModel = ""
    @Published var separateBackground = true
    @Published var backgroundGain = 0.8
    @Published var backgroundDucking = false
    @Published var allowCrossEngineRepair = UserDefaults.standard.object(forKey:"allowCrossEngineRepair") as? Bool ?? false { didSet {UserDefaults.standard.set(allowCrossEngineRepair,forKey:"allowCrossEngineRepair")} }
    @Published var gsvDevice = "mps"
    @Published var voiceRenderMode=UserDefaults.standard.string(forKey:"voiceRenderMode") ?? "detail" {didSet {UserDefaults.standard.set(voiceRenderMode,forKey:"voiceRenderMode")}}
    @Published var gsvReady = false
    @Published var cosyReady = false
    @Published var comparisonGSV: URL?
    @Published var comparisonCosy: URL?
    @Published var reviewBackend = "gpt-sovits"
    @Published var separatorReady = false
    @Published var speakersReady = false
    @Published var speechReady = false
    @Published var autoSpeakers = true
    @Published var productionMode=UserDefaults.standard.string(forKey:"productionMode") ?? "normal" {didSet {UserDefaults.standard.set(productionMode,forKey:"productionMode")}}
    @Published var roleAnalysisMode = "audio"
    @Published var visualRoleAnalysisEnabled=UserDefaults.standard.bool(forKey:"visualRoleAnalysisEnabled") {didSet {UserDefaults.standard.set(visualRoleAnalysisEnabled,forKey:"visualRoleAnalysisEnabled")}}
    @Published var voiceStyleMode=UserDefaults.standard.string(forKey:"voiceStyleMode") ?? "clone" {didSet {UserDefaults.standard.set(voiceStyleMode,forKey:"voiceStyleMode")}}
    @Published var showSavedVoiceChoices = false
    @Published var autoFit = true
    @Published var burnOutputCaptions = false
    @Published var reviewAutoFit = true
    @Published var advancedSettings:WorkflowDraft?
    @Published var showLogs = false
    @Published var showAbout = false
    @Published var autoSkipOP = true
    @Published var translateOPED = false
    @Published var availableHeight: CGFloat = 900
    @Published var largePreview = false
    @Published var batchItems: [BatchItem] = []
    @Published var batchRunning = false
    @Published var reviewVoiceProfiles:[VoiceProfile]=[]
    @Published var voiceProfiles: [VoiceProfile] = [] { didSet { persistProfiles() } }
    @Published var referenceSeconds = 6.0
    @Published var referenceStart = "00:00"
    @Published var auditionText = "喂，等埋我呀！我哋一齊出發啦。"
    @Published var backgroundAudio: URL?
    @Published var dialogueAudio: URL?
    @Published var voicePreview: URL?
    @Published var audioPreviewLabel = ""
    @Published var audioPlayer = AVPlayer()
    @Published var reviewUsesGSV = false
    @Published var timingRows: [VoiceTiming] = []
    @Published var output: URL?
    @Published var player = CantoPlayer()
    @Published var showingOutput = false
    @Published var busy = false
    @Published var processingClock = ProcessingClock()
    @Published var productionJourney:ProductionJourney?
    private var awaitingProductionJourney=false
    @Published var stage = "準備開始"
    @Published var detail = "匯入影片，再揀字幕來源同翻譯設定。"
    @Published var progress: Double?
    @Published var logs: [String] = []
    @Published var resultSummary=""
    @Published var aiAutoFix=UserDefaults.standard.object(forKey:"aiAutoFix") as? Bool ?? true {didSet {UserDefaults.standard.set(aiAutoFix,forKey:"aiAutoFix")}}
    @Published var showAIResultSummary=false
    var autoRepairResultPending=false
    @Published var voicePreviewLanguage="yue"
    @Published var qwenReferenceMode=UserDefaults.standard.string(forKey:"qwenReferenceMode") ?? "original" {didSet {UserDefaults.standard.set(qwenReferenceMode,forKey:"qwenReferenceMode")}}
    @Published var gsvReferenceMode=UserDefaults.standard.string(forKey:"gsvReferenceMode") ?? "original" {didSet {UserDefaults.standard.set(gsvReferenceMode,forKey:"gsvReferenceMode")}}
    @Published var developerJob: String?
    @Published var error: String?
    @Published var runtimeReady = false
    @Published var ollamaReady = false
    @Published var sttReady = false
    @Published var models: [String] = []
    @Published var selectedModel = UserDefaults.standard.string(forKey: "textModel") ?? "qwen3:14b" { didSet { UserDefaults.standard.set(selectedModel, forKey: "textModel");persistModelChoice("text",selectedModel) } }
    @Published var autoApprove = UserDefaults.standard.object(forKey: "automaticConversion") as? Bool ?? true {
        didSet { UserDefaults.standard.set(autoApprove, forKey: "automaticConversion") }
    }
    @Published var reviewURL: URL?
    @Published var scriptCues: [ScriptCue] = []
    @Published var scriptVideo = ""
    @Published var scriptApproved = false
    @Published var translate = true
    @Published var ocr = true
    @Published var ocrRegion = OCRRegion() { didSet { clearOCRPreview() } }
    @Published var selectingOCR = false
    @Published var ocrColor = "original" { didSet { clearOCRPreview() } }
    @Published var ocrStable = true
    @Published var ocrOriginal: URL?
    @Published var ocrPreview: URL?
    @Published var ocrText = ""
    @Published var playbackSeconds = 0.0
    @Published var playbackDuration = 1.0
    @Published var selectedCue: Int?
    private var playbackObserver: Any?
    private var presentationObserver: NSKeyValueObservation?
    private var playbackStatusObserver: NSKeyValueObservation?
    private var cueStopTime: Double?
    var seeking = false
    @Published var mixOriginal = false
    @Published var batchAutoSubtitles = true
    @Published var limit = 180
    @Published var startTimeText = "00:00"
    @Published var sourceDuration = 0.0
    @Published var videoAspect = 16.0 / 9.0
    private var activeOutputOffset = 0.0
    @Published var history: [URL] = []
    @Published var activePreviewJob: String?
    @Published var previewCueIndex:Int?
    @Published var setupCategory="general"
    @Published var showWorkspaceSettings=false
    @Published var continueOnError=true
    private var catalogue:ProjectDatabase?
    private var catalogueStamps:[String:String]=[:]
    var pauseAfterVoiceRegeneration=false
    @Published var showProjectManager=false
    @Published var workspaceControlTab="play"
    func projectDB() throws -> ProjectDatabase {if let catalogue{return catalogue};let db=try ProjectDatabase(root:engine.root);catalogue=db;return db}
    @Published var savedDrafts: [SavedDraft] = []

    init() {
        if UserDefaults.standard.integer(forKey:"independentReferencePolicy") < 1 {
            UserDefaults.standard.set("original",forKey:"qwenReferenceMode");UserDefaults.standard.set("original",forKey:"gsvReferenceMode");UserDefaults.standard.set(1,forKey:"independentReferencePolicy")
            qwenReferenceMode="original";gsvReferenceMode="original"
        }
        restoreStudioChoices()
        migrateSimpleVoiceSelection()
        if UserDefaults.standard.integer(forKey:"voiceStyleDefaultRevision")<3 {voiceStyleMode="clone";UserDefaults.standard.set(3,forKey:"voiceStyleDefaultRevision")}
        engine.notify = { [weak self] event in Task { @MainActor in self?.receive(event) } }
        resultSummary=(try? String(contentsOf:engine.root.appendingPathComponent("latest-result-summary.txt"),encoding:.utf8)) ?? ""
        refresh()
        loadProfiles()
        loadBatch()
        loadEditorQueue()
        if let data=try? Data(contentsOf:engine.root.appendingPathComponent("batch-submissions.json")),let saved=try? JSONDecoder().decode([Data].self,from:data) {pendingBatchRequests=saved}
        if let data=try? Data(contentsOf:engine.root.appendingPathComponent("batch-inflight.json")) {if !pendingBatchRequests.contains(data) {pendingBatchRequests.insert(data,at:0)};persistBatchRequests();try? FileManager.default.removeItem(at:engine.root.appendingPathComponent("batch-inflight.json"))}
        queuePaused = (try? JSONDecoder().decode(Bool.self,from:Data(contentsOf:engine.root.appendingPathComponent("queue-paused.json")))) ?? false
        if hasSavedWork {queuePaused=true;stage="已暫停";detail="有已保存工作，按繼續處理接續。"}
        projectEditor.configure(root:engine.root)
        workspacePreview.configurePersistence(root:engine.root)
        if let index=CommandLine.arguments.firstIndex(of:"--regenerate-voices"),CommandLine.arguments.indices.contains(index+1) {
            let review=CommandLine.arguments[index+1]
            DispatchQueue.main.asyncAfter(deadline:.now()+0.5) { [weak self] in self?.regenerateExistingVoices(review:review) }
        }
        playbackObserver = player.addPeriodicTimeObserver(forInterval: CMTime(seconds: 0.1, preferredTimescale: 600), queue: .main) { [weak self] time in
            Task { @MainActor in
                guard let self else { return }
                if let failure = self.player.failure { self.playbackError = failure }
                let seconds = time.seconds
                if seconds.isFinite && !self.seeking { self.playbackSeconds = seconds }
                if let duration = Optional(self.player.duration), duration.isFinite && duration > 0 { self.playbackDuration = duration }
                if let size = self.player.currentItem?.presentationSize, size.width > 0, size.height > 0 { self.videoAspect = size.width / size.height }
                if let end = self.cueStopTime, seconds >= end { self.player.pause(); self.cueStopTime = nil }
            }
        }

    }
    func refresh() {
        qwenTTSReady = FileManager.default.fileExists(atPath: engine.root.appendingPathComponent("qwen-ready.json").path)
        gsvReady = engine.gsvReady; cosyReady = engine.cosyReady; separatorReady = engine.separatorReady; speakersReady = engine.speakersReady; speechReady = engine.speechReady
        runtimeReady = engine.runtimeReady; ollamaReady = engine.ollamaReady; sttReady = engine.whisperReady
        models = engine.installedModelsOnDisk()
        let jobs = engine.root.appendingPathComponent("jobs")
        history = ((try? FileManager.default.contentsOfDirectory(at: jobs, includingPropertiesForKeys: nil)) ?? []).flatMap { (try? FileManager.default.contentsOfDirectory(at: $0, includingPropertiesForKeys: nil)) ?? [] }.filter { OutputStore.isOutputName($0.lastPathComponent) && FileManager.default.fileExists(atPath: $0.path) }.compactMap { original -> URL? in
            guard let data = try? Data(contentsOf:original.deletingLastPathComponent().appendingPathComponent("report.json")), let report = try? JSONSerialization.jsonObject(with:data) as? [String:Any], let exported = report["exportedOutput"] as? String else { return original }
            let url = URL(fileURLWithPath:exported)
            return FileManager.default.fileExists(atPath:url.path) ? url : nil
        }.sorted { $0.path > $1.path }
        var seenOutputs=Set<String>()
        history=history.filter {seenOutputs.insert($0.resolvingSymlinksInPath().standardizedFileURL.path).inserted}
        savedDrafts = ((try? FileManager.default.contentsOfDirectory(at: jobs, includingPropertiesForKeys: nil)) ?? []).compactMap { folder in
            let url = folder.appendingPathComponent("review.json")
            guard let data = try? Data(contentsOf: url), let obj = try? JSONSerialization.jsonObject(with: data) as? [String:Any], let cfg = obj["config"] as? [String:Any], let video = cfg["video"] as? String else { return nil }
            let kind = cfg["speechTiming"] as? Bool == true ? "日語原聲稿" : "舊字幕稿"
            let start = cfg["startOffset"] as? Double ?? 0
            return SavedDraft(url: url, title: URL(fileURLWithPath: video).lastPathComponent, note: "\(kind) · 原片 \(Int(start)/60):\(String(format: "%02d", Int(start)%60)) · \((obj["cues"] as? [Any])?.count ?? 0) 句", date: (try? url.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? .distantPast)
        }.sorted { $0.date > $1.date }
        do {
            let db=try projectDB()
            for draft in savedDrafts {
                let output=history.first {editableReview(for:$0)==draft.url}
                let stamp=String(draft.date.timeIntervalSince1970)+"|"+(output?.path ?? "")
                if catalogueStamps[draft.url.path] != stamp {try db.sync(review:draft.url,output:output);catalogueStamps[draft.url.path]=stamp}
            }
            let indexed=try db.rows("SELECT path FROM outputs ORDER BY updated DESC").compactMap {row -> URL? in guard let path=row.first,FileManager.default.fileExists(atPath:path) else{return nil};return URL(fileURLWithPath:path)}
            var seen=Set<String>()
            history=try (history+indexed).filter {try !db.isRemoved($0) && seen.insert($0.resolvingSymlinksInPath().standardizedFileURL.path).inserted}
        } catch {self.error=error.localizedDescription}
        reconcileBatchProjects()
    }
    func editableReview(for output: URL) -> URL? {
        savedDrafts.first { draft in
            let folder=draft.url.deletingLastPathComponent()
            if output.deletingLastPathComponent().standardizedFileURL == folder.standardizedFileURL { return true }
            guard let data=try? Data(contentsOf:folder.appendingPathComponent("report.json")),
                  let report=try? JSONSerialization.jsonObject(with:data) as? [String:Any],
                  let exported=report["exportedOutput"] as? String else { return false }
            return URL(fileURLWithPath:exported).standardizedFileURL == output.standardizedFileURL
        }?.url
    }
    func openDraft(_ url: URL) {
        do {
            let obj = try JSONSerialization.jsonObject(with: Data(contentsOf: url)) as! [String:Any]
            let cfg = obj["config"] as! [String:Any]
            loadVideo(URL(fileURLWithPath: cfg["video"] as! String), review: url)
        } catch { self.error = "讀唔到校稿：\(error.localizedDescription)" }
    }
    func trashOutput(_ url: URL) {
        guard !busy else { return }
        let file = url.standardizedFileURL
        let jobs = engine.root.appendingPathComponent("jobs").resolvingSymlinksInPath().standardizedFileURL
        let internalOutput = file.resolvingSymlinksInPath().deletingLastPathComponent().deletingLastPathComponent() == jobs
        let recordedExport = history.contains { $0.standardizedFileURL == file } || ((try? ProjectCleanupPlan(root:engine.root,mode:.outputs).outputs.contains { $0.standardizedFileURL==file }) == true)
        guard OutputStore.isOutputName(file.lastPathComponent), file != video?.standardizedFileURL,
              internalOutput || recordedExport,
              (try? file.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey])).map({ $0.isRegularFile == true && $0.isSymbolicLink != true }) == true else {
            error = "只可以移走工作紀錄入面已生成嘅 MP4。檔案可能已被移走，請重新整理。"
            stage = "未能刪除"; detail = error!; refresh(); return
        }
        let playingFile = (player.currentItem?.asset as? AVURLAsset)?.url.standardizedFileURL
        let wasPlaying = playingFile == file
        if wasPlaying { player.pause() }
        do {
            try FileManager.default.trashItem(at: file, resultingItemURL: nil)
            try projectDB().removeOutput(file)
            for i in batchItems.indices where batchItems[i].output==file.path {batchItems[i].output=nil};persistBatch()
            if output?.standardizedFileURL == file { output = nil }
            if wasPlaying {
                cueStopTime = nil
                if let previewURL, previewURL.standardizedFileURL != file {
                    preview(previewURL, isOutput: false)
                } else {
                    player.replaceCurrentItem(with: nil); showingOutput = false
                    playbackSeconds = 0; playbackDuration = 1
                }
            }
            error = nil; stage = "已移到垃圾桶"; progress = 1
            detail = "已移走 MP4。原片、字幕、校稿同配音快取保留；可以重新輸出，亦可以喺 Finder 垃圾桶還原。"
            logs.append("[刪除成品] \(file.deletingLastPathComponent().lastPathComponent) 嘅 MP4 已移到垃圾桶。")
            refresh()
        } catch {
            self.error = "移到垃圾桶失敗：\(error.localizedDescription)"
            stage = "未能刪除"; detail = self.error!
        }
    }
    func trashDrafts(_ urls: [URL]) {
        guard !busy, !urls.isEmpty else { return }
        let alert = NSAlert()
        alert.messageText = urls.count == 1 ? "清除呢份校稿？" : "清除全部 \(urls.count) 份校稿？"
        alert.informativeText = "校稿同翻譯草稿會移到垃圾桶。原片、已輸出 MP4、字幕、模型同音訊快取會保留。"
        alert.addButton(withTitle: "移到垃圾桶"); alert.addButton(withTitle: "取消")
        guard alert.runModal() == .alertFirstButtonReturn else { return }
        var removed = 0
        do {
            for url in urls {
                try DraftStore.trash(url, jobs: engine.root.appendingPathComponent("jobs"))
                try projectDB().removeProject(url)
                removed += 1
                if reviewURL == url {
                    reviewURL = nil; scriptCues = []; timingRows = []; scriptApproved = false
                    audioPlayer.pause(); audioPlayer.replaceCurrentItem(with: nil)
                    voicePreview = nil; selectedCue = nil
                }
                for i in batchItems.indices where batchItems[i].review == url.path {
                    batchItems[i].review = nil
                    if batchItems[i].output == nil { batchItems[i].status = "待處理" }
                }
            }
            error = nil; stage = "校稿已清除"; detail = "\(removed) 份校稿已移到垃圾桶；成品同模型保留。"
        } catch {
            self.error = "已清除 \(removed) 份；其餘未能清除：\(error.localizedDescription)"
            stage = "未能完成清除"; detail = self.error!
        }
        persistBatch(); refresh()
    }
    func receive(_ event: WorkerEvent) {
        componentProgress=event.componentProgress
        if event.productionPending==true {awaitingProductionJourney=true;productionJourney=nil;progress=nil}
        if let track=event.audioTrack {activeAudioTrack=track.state=="running" ? track:nil;audioSkipRequested=false}
        let previousDownloadState=downloadTransfer?.state
        downloadTransfer=event.download
        if event.download != nil && !awaitingProductionJourney {progress=event.progress}
        processingClock.observe(stage: event.stage, message: event.message,passID:activeAudioTrack?.token,workID:event.workID,historyID:activeAudioTrack.map {$0.engine+"|"+$0.language},cached:event.workCached ?? false,completed:event.workCompleted,units:event.workTotal)
        var batchIndex=event.batchId.flatMap {id in batchItems.firstIndex(where:{$0.id==id})}
        if batchIndex==nil,event.batchId != nil,let path=event.review,let data=try? Data(contentsOf:URL(fileURLWithPath:path)),let obj=try? JSONSerialization.jsonObject(with:data) as? [String:Any],let cfg=obj["config"] as? [String:Any],let source=cfg["video"] as? String {
            let matches=batchItems.indices.filter {batchItems[$0].video==source}
            if matches.count==1 {batchIndex=matches[0]}
        }
        if let i=batchIndex {
            if let value = event.batchStatus { batchItems[i].status = value;if value == "處理中" || value == "完成" {batchItems[i].message=""} }
            if let value = event.review { batchItems[i].review = value }
            if let value = event.job { batchItems[i].previewJob = value }
            if let value = event.output { batchItems[i].output = value }
            if event.stage == "批量錯誤" { batchItems[i].message = event.message }
            persistBatch()
        }
        if let start = event.opStart { startTimeText = String(format: "%.3f", start) }
        if let text=event.rewriteText,let target=projectEditor.suggestionTarget {
            if projectEditor.document?.review==target.review,projectEditor.document?.segments.contains(where:{$0.id==target.segment && (target.language=="en" ? $0.english ?? "":$0.text)==target.text})==true {projectEditor.suggestion=text}
        }
        else if let index = event.rewriteIndex, let text = event.rewriteText, scriptCues.indices.contains(index) {
            scriptCues[index].cantonese = text; scriptApproved = false
        }
        if let job = event.job { developerJob = job;if activePreviewJob != job {previewCueIndex=nil};activePreviewJob=job }
        if let index=event.cueIndex {previewCueIndex=index}
        if let path = event.background { backgroundAudio = URL(fileURLWithPath: path) }
        if let path = event.dialogue { dialogueAudio = URL(fileURLWithPath: path) }
        if let path = event.comparisonGSV { comparisonGSV = URL(fileURLWithPath: path) }
        if let path = event.comparisonCosy { comparisonCosy = URL(fileURLWithPath: path) }
        if let path = event.voicePreview { voicePreview = URL(fileURLWithPath: path); audition(voicePreview!, label: "角色配音試聽") }
        if let path = event.reference, let id = event.profileId, let i = voiceProfiles.firstIndex(where: { $0.id == id }) {
            voiceProfiles[i].reference = path; voiceProfiles[i].promptText = event.promptText ?? ""
        }
        if event.stage != "工具" && event.stage != "耗時摘要" { stage = event.partial==true ? "部分完成":event.stage; detail = event.message }
        if let journey=event.journey {
            awaitingProductionJourney=false
            let same=productionJourney?.job==journey.job
            productionJourney=journey
            progress=same ? max(progress ?? 0,journey.progress):journey.progress
        } else if !awaitingProductionJourney,productionJourney==nil,let p=event.progress {progress=max(progress ?? 0,p)}
        if let path = event.output {
            if event.partial != true {processingClock.markSuccessful()}
            output = URL(fileURLWithPath: path); refresh()
            if event.batchId == nil, let reviewURL, let i = batchItems.firstIndex(where: { $0.review == reviewURL.path }) {
                batchItems[i].output = path; batchItems[i].status = event.partial==true ? "需要處理":"完成"; batchItems[i].message = event.partial==true ? event.message:""; persistBatch()
            }
        }
        if let path = event.ocrOriginal { ocrOriginal = URL(fileURLWithPath: path) }
        if let path = event.ocrPreview { ocrPreview = URL(fileURLWithPath: path) }
        if let text = event.ocrText { ocrText = text }
        if let path = event.review {
            do {
                try projectDB().sync(review:URL(fileURLWithPath:path))
                let url = URL(fileURLWithPath: path)
                let data = try Data(contentsOf: url)
                let object = try JSONSerialization.jsonObject(with: data) as! [String:Any]
                scriptCues = try JSONDecoder().decode([ScriptCue].self, from: JSONSerialization.data(withJSONObject: object["cues"]!))
                scriptVideo = URL(fileURLWithPath: (object["config"] as? [String:Any])?["video"] as? String ?? "").lastPathComponent
                reviewURL = url; scriptApproved = false
                let savedBackend = (object["config"] as? [String:Any])?["ttsBackend"] as? String
                reviewBackend = VoiceEngineChoice.active(savedBackend ?? "cosyvoice3")
                ttsBackend = reviewBackend
                if let config = object["config"] as? [String:Any] {
                    extraEngines = Set(config["selectedEngines"] as? [String] ?? []).subtracting([ttsBackend,"qwen-tts","gpt-sovits-v3"])
                    includeOriginal = config["includeOriginal"] as? Bool ?? true
                    pronunciationText = config["pronunciationText"] as? String ?? ""
                    cantonesePronunciationText = config["cantonesePronunciationText"] as? String ?? ""
                    subtitleOutput = config["subtitleOutput"] as? String ?? "yue"
                    burnSubtitleMode = config["burnSubtitleMode"] as? String ?? "yue"
                    exportFolder = config["exportFolder"] as? String ?? exportFolder
                }
                reviewUsesGSV = VoiceEngineChoice.requiresReference(reviewBackend)
                reviewAutoFit = (object["config"] as? [String:Any])?["autoFit"] as? Bool ?? false
                burnOutputCaptions = (object["config"] as? [String:Any])?["burnOutputCaptions"] as? Bool ?? false
                reviewVoiceProfiles=[]
                if let profiles = (object["config"] as? [String:Any])?["voiceProfiles"],
                   let data = try? JSONSerialization.data(withJSONObject: profiles),
                   let saved = try? JSONDecoder().decode([VoiceProfile].self, from: data) {
                    reviewVoiceProfiles=saved
                }
                loadTimings()
            } catch { self.error = "讀唔到校稿檔：\(error.localizedDescription)" }
        }
        if event.stage == "等待批准" && !batchRunning { section = .history }
        if event.output != nil { scriptApproved = true }
        // Keep the terminal useful; once-per-second speed samples belong in the
        // live header, while reconnects and validation transitions are logged.
        if let transfer=event.download {
            if transfer.state != previousDownloadState || transfer.state=="retrying" {
                logs.append("[\(event.stage)] \(transfer.file) · \(transfer.stateTitle) · \(transfer.sizeText) · #\(transfer.attempt)")
            }
        } else {logs.append("[\(event.stage)] \(event.message)")}
        if event.stage=="結果摘要" {
            if event.autoRepair==true {autoRepairResultPending=true}
            resultSummary=event.message
            try? resultSummary.write(to:engine.root.appendingPathComponent("latest-result-summary.txt"),atomically:true,encoding:.utf8)
        }

        if logs.count > 250 { logs.removeFirst(logs.count - 250) }
    }
    func task(_ title: String, timingConfiguration:[String:Any]?=nil, operation: @escaping @Sendable () throws -> Void) {
        guard !busy else { return }
        processingClock.start()
        productionJourney=nil;awaitingProductionJourney=false
        // Frozen batch settings, hardware and model variants define comparable runs.
        // Configure every task: only explicit completed passes contribute rates.
        var timing=outputSettings
        timing["model"]=selectedModel;timing["subtitleSource"]=subtitleSource
        timing["separateBackground"]=separateBackground;timing["burnOutputCaptions"]=burnOutputCaptions
        timing["gsvDevice"]=gsvDevice
        if let frozen=timingConfiguration {for (key,value) in frozen {timing[key]=value}}
        let keys=["translationSource","productionMode","model","speechModel","referenceSpeechModel","asrModel","cosyModel","selectedEngines","dubLanguages","subtitleSource","subtitleOutput","separateBackground","burnOutputCaptions","gsvDevice","gsvReferenceMode"]
        var comparable=timing.filter {keys.contains($0.key)}
        comparable["processors"]=ProcessInfo.processInfo.processorCount
        comparable["memory"]=ProcessInfo.processInfo.physicalMemory
        let data=(try? JSONSerialization.data(withJSONObject:comparable,options:.sortedKeys)) ?? Data()
        let profile="phase-v18|"+String(data:data,encoding:.utf8)!
        let seconds=min(limit>0 ? Double(limit):sourceDuration,max(0,sourceDuration-(startSeconds ?? 0)))
        processingClock.configure(profile:profile,seconds:seconds,directory:engine.root.appendingPathComponent("performance"))
        busy = true; error = nil; progress = nil; downloadTransfer=nil; stage = title; detail = "處理中…"
        engine.resetCancellation()
        Task {
            let result = await Task.detached(priority: .userInitiated) { Result { try operation() } }.value
            processingClock.stop()
            processingClock.save(to: engine.root.appendingPathComponent("performance"))
            busy = false
            if let id=activeEditorTask,let i=editorTasks.firstIndex(where:{$0.id==id}) {
                if case .failure(let failure)=result {editorTasks[i].status=pauseRequested ? "queued":"failed";editorTasks[i].message=pauseRequested ? "已暫停，完成進度已保留。":failure.localizedDescription}
                else {
                    let state=URL(fileURLWithPath:editorTasks[i].review).deletingLastPathComponent().appendingPathComponent("versions/"+id+"/version.json")
                    let object=(try? JSONSerialization.jsonObject(with:Data(contentsOf:state))) as? [String:Any]
                    let partial=["partial","script-partial"].contains(object?["status"] as? String ?? "")
                    editorTasks[i].status=partial ? "failed":"complete";editorTasks[i].message=partial ? (object?["status"] as? String=="script-partial" ? "部分字幕未完成；可重試":"部分音軌未完成；可重試"):""
                }
                activeEditorTask=nil;saveEditorQueue();projectEditor.refresh(self)
                let submitted=(try? JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:editorTasks[i].submission)))) as? [String:Any]
                if pauseAfterVoiceRegeneration || (submitted?["settings"] as? [String:Any])?["pauseAfterVoiceRegeneration"] as? Bool==true {pauseAfterVoiceRegeneration=false;queuePaused=true}
            }
            if batchRunning {
                if pauseRequested,let request=currentBatchRequest {
                    if !pendingBatchRequests.contains(request) {pendingBatchRequests.insert(request,at:0)}
                    queuePaused=true;persistBatchRequests()
                } else if case .failure(let failure)=result,let request=currentBatchRequest {
                    // An episode/process failure must not cancel the user's batch.
                    // Keep it retryable, consume this submission and advance once.
                    let cfg=(try? JSONSerialization.jsonObject(with:request)) as? [String:Any]
                    let ids=Set((cfg?["videos"] as? [[String:Any]] ?? []).compactMap {$0["id"] as? String})
                    for i in batchItems.indices where ids.contains(batchItems[i].id) && batchItems[i].output==nil {
                        batchItems[i].status="需要處理";batchItems[i].message=failure.localizedDescription
                    }
                    logs.append("[佇列繼續] 本片未完成，已保留原因；繼續下一條影片。")
                }
                currentBatchRequest=nil
                try? FileManager.default.removeItem(at:engine.root.appendingPathComponent("batch-inflight.json"))
                for i in batchItems.indices where batchItems[i].status == "處理中" { batchItems[i].status = pauseRequested ? "已暫停":"已中斷，可重試" }
                persistBatch()
                if !pauseRequested && pendingBatchRequests.isEmpty {
                    resultSummary=batchItems.map {URL(fileURLWithPath:$0.video).lastPathComponent+"："+L($0.status)+($0.message.isEmpty ? "":" — "+$0.message)}.joined(separator:"\n")
                    try? resultSummary.write(to:engine.root.appendingPathComponent("latest-result-summary.txt"),atomically:true,encoding:.utf8)
                }
            }
            batchRunning = false
            if pauseRequested {
                error=nil;stage="已暫停";detail="已保存工作設定及完成進度；下次開啟可繼續。"
                logs.append("[暫停摘要] 已保留完成嘅字幕、翻譯及配音；未完成步驟會喺繼續時重試。")
                pauseRequested=false
            } else if case .failure(let failure) = result {
                autoRepairResultPending=false
                error = failure.localizedDescription; stage = "需要處理"; detail = String(failure.localizedDescription.prefix(220))
                let line = "[錯誤] \(failure.localizedDescription)"
                if logs.last != line { logs.append(line) }
            }
            refresh()
            loadTimings()
            let engine = self.engine
            let online = await Task.detached { engine.availableModels() }.value
            if !online.isEmpty { models = online }
            try? logs.joined(separator: "\n").write(to: engine.root.appendingPathComponent("latest-session.log"), atomically: true, encoding: .utf8)
            pumpEditorQueue()
            if !busy {pumpBatchRequests()}
            if !busy && !pauseRequested && autoRepairResultPending {
                autoRepairResultPending=false;projectEditor.workspacePage="edit";showAIResultSummary=true
            }
        }
    }
    func chooseVideo() {
        guard !busy else { return }
        let panel = NSOpenPanel(); panel.allowedContentTypes = [.mpeg4Movie, .quickTimeMovie, .movie, UTType(filenameExtension: "mkv") ?? .data]; panel.allowsMultipleSelection = false
        if panel.runModal() == .OK, let url = panel.url { loadVideo(url) }
    }
    func loadVideo(_ url: URL, review: URL? = nil) {
        guard !busy else { return }
        reviewURL = nil; scriptCues = []; scriptVideo = ""; scriptApproved = false
        ocrRegion = OCRRegion(); selectingOCR = false
        startTimeText = "00:00"; sourceDuration = 0; activeOutputOffset = 0
        clearOCRPreview(); selectedCue = nil; cueStopTime = nil; playbackSeconds = 0; playbackDuration = 1
        video = url; output = nil; showingOutput = false; subtitle = nil; ocr = true; subtitleTracks = []; subtitleStream = -1; subtitleSource = "burned"
        backgroundAudio = nil; dialogueAudio = nil; audioPlayer.pause(); audioPreviewLabel = ""
        preparingPreview = true; playbackError = nil; subtitlePreviewMessage = ""
        previewURL = nil; player.pause(); player.replaceCurrentItem(with: nil)
        for ext in ["srt", "ass"] {
            let candidate = url.deletingPathExtension().appendingPathExtension(ext)
            if FileManager.default.fileExists(atPath: candidate.path) { subtitle = candidate; ocr = false; subtitleSource = "external"; break }
        }
        processingClock.start()
        busy = true; stage = "分析"; detail = "讀取影片同字幕軌。"; progress = nil; error = nil
        engine.resetCancellation()
        let e = engine
        Task {
            let result = await Task.detached { Result { try e.inspectVideo(url) } }.value
            processingClock.stop()
            processingClock.save(to: engine.root.appendingPathComponent("performance"))
            busy = false; preparingPreview = false
            switch result {
            case .success(let info):
                subtitleTracks = info.tracks; previewURL = info.preview; playbackDuration = max(1, info.duration); sourceDuration = info.duration; videoAspect = info.aspectRatio
                if let first = info.tracks.first(where: { $0.supported && ["chi", "zh", "yue"].contains(where:$0.language.lowercased().hasPrefix) }) ?? info.tracks.first(where: { $0.supported }) {
                    subtitleStream = first.id
                    if subtitleSource != "external" { subtitleSource = "embedded"; ocr = false }
                }
                if info.burnedCaptions { subtitleSource = "none"; subtitle = nil; ocr = false }
                preview(info.preview, isOutput: false)
                stage = "準備完成"; detail = "片長 \(Int(info.duration / 60)) 分 \(Int(info.duration) % 60) 秒 · \(info.tracks.count) 條內置字幕軌。"
                if let review { receive(WorkerEvent(stage: "等待批准", message: "已載入批量校稿，角色已自動配對。", review: review.path)); section = .script }
            case .failure(let failure): error = failure.localizedDescription; playbackError = failure.localizedDescription; stage = "讀取失敗"; detail = failure.localizedDescription
            }
        }
    }
    func chooseSubtitle() {
        let panel = NSOpenPanel(); panel.allowedContentTypes = [UTType(filenameExtension: "srt")!, UTType(filenameExtension: "ass")!, UTType(filenameExtension: "vtt")!, .plainText]
        if panel.runModal() == .OK { subtitle = panel.url; ocr = false; subtitleSource = "external"; selectPreviewSubtitle() }
    }
    func preview(_ url: URL, isOutput: Bool) {
        let sourceTime = player.currentTime().seconds + (showingOutput ? activeOutputOffset : 0)
        var offset = 0.0
        if isOutput, let data = try? Data(contentsOf: outputReportURL(url,"report.json")), let report = try? JSONSerialization.jsonObject(with: data) as? [String:Any] { offset = report["sourceStart"] as? Double ?? 0 }
        let time = CMTime(seconds: max(0, sourceTime.isFinite ? sourceTime-offset : 0), preferredTimescale: 600)
        activeOutputOffset = offset; player.pause(); audioPlayer.pause()
        let item = AVPlayerItem(url: url)
        playbackError = nil
        player.replaceCurrentItem(with: item); showingOutput = isOutput
        player.seek(to: time)
        if isOutput {
            previewCaptions = []
            let data = try? Data(contentsOf:outputReportURL(url,"report.json"))
            let report = data.flatMap { try? JSONSerialization.jsonObject(with:$0) as? [String:Any] }
            player.subtitles(ordinal:report?["burnOutputCaptions"] as? Bool == true ? nil : 0,external:nil)
        } else { selectPreviewSubtitle() }
    }
    func selectPreviewSubtitle() {
        guard player.currentItem != nil else { return }
        let request = UUID(); subtitleRequest = request
        let source = showingOutput ? (player.currentItem?.asset as? AVURLAsset)?.url : (subtitleSource == "embedded" ? video : subtitleSource == "external" ? subtitle : nil)
        let stream = !showingOutput && subtitleSource == "embedded" ? subtitleStream : nil
        previewCaptions = []; player.subtitles(ordinal:nil,external:nil)
        guard section != .script else { subtitlePreviewMessage = ""; return }
        guard let source else { subtitlePreviewMessage = ""; return }
        subtitlePreviewMessage = "載入 VLC 字幕…"
        let e = engine; let isOutput = showingOutput
        Task {
            do {
                let file = try await Task.detached { try isOutput ? e.vlcOutputSubtitle(source:source) : e.vlcSubtitle(source:source,stream:stream) }.value
                guard subtitleRequest == request, section != .script else { return }
                player.subtitles(ordinal:nil,external:file)
                subtitlePreviewMessage = file == nil ? "字幕已燒入畫面；毋須額外字幕軌。" : "VLC 字幕已載入；使用內置中文字型，保留字幕時間、位置同樣式。"
            } catch {
                guard subtitleRequest == request, section != .script else { return }
                subtitlePreviewMessage = "字幕載入失敗：" + error.localizedDescription
            }
        }
    }

    func jumpToFirstSubtitle() {
        guard let time = subtitleTracks.first(where: { $0.id == subtitleStream })?.firstCue else { return }
        if showingOutput, let previewURL { preview(previewURL, isOutput: false) }
        player.seek(to: CMTime(seconds: time + 0.1, preferredTimescale: 600), toleranceBefore: .zero, toleranceAfter: .zero)
    }
    func convert() {
        guard let video else { return }
        if !validateDubbing() { return }
        guard let start = startSeconds, start < sourceDuration else { error = "請輸入有效開始時間（例如 01:30），必須早過片尾。"; detail = error!; return }
        if subtitleSource == "external" && subtitle == nil { error = "請加入 SRT／ASS／VTT 字幕檔。"; detail = error!; return }
        if subtitleSource == "embedded" && !subtitleTracks.contains(where: { $0.id == subtitleStream && $0.supported }) { error = "請選擇一條可用文字字幕軌。"; detail = error!; return }
        let cfg = conversionConfig(video, start: start)
        let engine = self.engine, useAI = translate || needsEnglishSubtitles, selected = selectedModel
        // JSON serialization before crossing concurrency boundaries.
        let data = try! JSONSerialization.data(withJSONObject: cfg)
        player.pause(); audioPlayer.pause()
        output = nil; reviewURL = nil; scriptCues = []; scriptApproved = false
        task("開始轉換") {
            if !engine.runtimeReady { try engine.installRuntime() }
            if cfg["autoSpeakers"] as? Bool == true { try engine.ensureAutoSpeakers(independent:cfg["roleAnalysisMode"] as? String=="independent") }
            if useAI {
                try engine.ensureSpeechTiming(qualityChecks:cfg["productionMode"] as? String != "fast")
                try engine.startTextModel(selected)
                guard engine.availableModels().contains(selected) else { throw AppFailure(message: "請先下載 \(selected)，或者關閉 AI 翻譯並提供已校對嘅廣東話字幕。") }
            }
            let config = try JSONSerialization.jsonObject(with: data) as! [String:Any]
            try engine.worker("convert", config: config)
        }
    }
    func saveScript() throws {
        guard let url = reviewURL else { throw AppFailure(message: "未有廣東話稿。") }
        var object = try JSONSerialization.jsonObject(with: Data(contentsOf: url)) as! [String:Any]
        let edited = try JSONSerialization.jsonObject(with: JSONEncoder().encode(scriptCues)) as! [[String:Any]]
        guard let original = object["cues"] as? [[String:Any]] else { throw AppFailure(message:"校稿檔案格式無效。") }
        object["cues"] = try DraftStore.mergeEdits(original: original, edited: edited)
        object["status"] = "pending"
        if var config = object["config"] as? [String:Any], reviewUsesGSV {
            config["ffmpeg"] = engine.ffmpeg.path
            config["ffprobe"] = engine.ffprobe.path
            config["executable"] = Bundle.main.executableURL!.path
            ttsBackend = reviewBackend
            config["model"] = selectedModel
            config["port"] = engine.port
            config["ttsBackend"] = reviewBackend
            config.merge(outputSettings) { _, new in new }
            config["autoFit"] = reviewAutoFit
            config["scriptLocked"] = true
            config["burnOutputCaptions"] = burnOutputCaptions
            config["voiceProfiles"] = (try? JSONSerialization.jsonObject(with:JSONEncoder().encode(reviewVoices))) ?? []
            config["defaultSpeaker"] = reviewVoices.count == 1 ? reviewVoices[0].id : ""
            object["config"] = config
        }
        try JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys]).write(to: url, options: .atomic)
        scriptApproved = false
    }
    func saveDraft() {
        do { try saveScript(); stage = "已儲存"; detail = "廣東話稿已保存；未開始配音。"; error = nil }
        catch { self.error = error.localizedDescription }
    }
    func approveScript() {
        guard !busy, let url = reviewURL else { return }
        guard scriptCues.contains(where: { $0.included }) else { error = "請至少保留一句配音台詞。"; return }
        if let index = scriptCues.firstIndex(where: { $0.included && $0.cantonese.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }) {
            error = "第 \(index+1) 句廣東話稿係空白；請填寫或停用呢句。"; return
        }
        if needsEnglishSubtitles && !models.contains(selectedModel) { error = "英文字幕需要先下載所選文字模型。"; return }
        if reviewUsesGSV {
            guard selectedEngines.allSatisfy({ engineReady($0) }) else { error = "請先喺環境頁部署所選配音引擎。"; return }
            let missing = scriptCues.first { cue in cue.included && !reviewVoices.contains(where: { $0.id == (cue.speakerId ?? (reviewVoices.count == 1 ? reviewVoices[0].id : "")) && $0.ready }) }
            if missing != nil { error = "有角色參考未準備好。請按「自動配對全部角色」重新分析，毋須逐句揀人。"; detail = error!; return }
        }
        do { try saveScript() } catch { self.error = error.localizedDescription; return }
        let e = engine
        player.pause(); audioPlayer.pause(); output = nil
        task("已批准，開始配音") { try e.worker("render", config: ["review":url.path, "lockScript":true]) }
    }
    var startSeconds: Double? {
        let parts = startTimeText.trimmingCharacters(in: .whitespacesAndNewlines).split(separator: ":", omittingEmptySubsequences: false)
        guard (1...3).contains(parts.count) else { return nil }
        var total = 0.0
        for (index, part) in parts.enumerated() {
            guard let value = Double(part), value.isFinite, value >= 0,
                  (index == 0 || value < 60), (index == parts.count-1 || value.rounded(.down) == value) else { return nil }
            total = total * 60 + value
        }
        return total
    }
    var rangeDescription: String {
        guard let start = startSeconds, start < sourceDuration else { return "請揀有效嘅開始時間。" }
        let end = limit == 0 ? sourceDuration : min(sourceDuration, start + Double(limit))
        return "原片 \(clockLabel(start)) → \(clockLabel(end))（\(Int((end-start).rounded())) 秒）；輸出由起點開始，唔包括之前嘅 OP。"
    }
    func clockLabel(_ seconds: Double) -> String { String(format: "%02d:%05.2f", Int(seconds) / 60, seconds.truncatingRemainder(dividingBy: 60)) }
    func useCurrentStart() {
        guard !showingOutput, video != nil else { return }
        player.pause(); cueStopTime = nil
        startTimeText = clockLabel(playbackSeconds)
    }
    func previewStart() {
        guard let start = startSeconds, start < sourceDuration else { error = "開始時間超出原片範圍或格式無效。"; return }
        if showingOutput, let previewURL { preview(previewURL, isOutput: false) }
        seekVideo(start)
    }
    var ocrSettings: [String:Any] {
        ["ocrRect":ocrRegion.config, "ocrColor":ocrColor, "ocrStable":ocrStable]
    }
    func beginOCRSelection() {
        guard video != nil, !busy else { return }
        if showingOutput, let previewURL { preview(previewURL, isOutput: false) }
        player.pause(); cueStopTime = nil; selectingOCR = true
        stage = "框選字幕"; detail = "喺影片畫面拖拉方框，包住完整字幕，避開水印。"
    }
    func finishOCRSelection() { selectingOCR = false; previewOCR() }
    func clearOCRPreview() { ocrOriginal = nil; ocrPreview = nil; ocrText = "" }
    func previewOCR() {
        guard let video, !busy else { return }
        player.pause(); cueStopTime = nil
        var cfg = ocrSettings
        cfg.merge(["video":video.path, "storage":engine.root.path, "ffmpeg":engine.ffmpeg.path, "executable":Bundle.main.executableURL!.path, "previewTime":playbackSeconds]) { _, new in new }
        let data = try! JSONSerialization.data(withJSONObject: cfg), e = engine
        task("預覽字幕範圍") {
            if !e.runtimeReady { try e.installRuntime() }
            try e.worker("preview-ocr", config: JSONSerialization.jsonObject(with: data) as! [String:Any])
        }
    }
    func seekVideo(_ seconds: Double) {
        cueStopTime = nil
        player.pause()
        playbackSeconds = seconds
        player.seek(to: CMTime(seconds: seconds, preferredTimescale: 600), toleranceBefore: .zero, toleranceAfter: .zero)
    }
    func seekCue(_ cue: ScriptCue, play: Bool = false) {
        guard let previewURL else { return }
        if showingOutput { preview(previewURL, isOutput: false) }
        selectedCue = scriptCues.firstIndex(where: { $0.id == cue.id })
        cueStopTime = nil; player.pause(); playbackSeconds = cue.sourceStart ?? cue.start
        player.seek(to: CMTime(seconds: cue.sourceStart ?? cue.start, preferredTimescale: 600), toleranceBefore: .zero, toleranceAfter: .zero) { [weak self] finished in
            Task { @MainActor in
                if finished && play { self?.cueStopTime = cue.sourceEnd ?? cue.end; self?.player.play() }
            }
        }
    }

}

func adaptive(_ light: NSColor, _ dark: NSColor) -> Color {
    Color(nsColor: NSColor(name: nil) { appearance in
        appearance.bestMatch(from: [.darkAqua, .aqua]) == .darkAqua ? dark : light
    })
}
let ink = Color.primary
var accent: Color {
    WelcomePalette.color(UserDefaults.standard.string(forKey:"animeTheme") ?? "studio")
}
var paper: Color { AnimeStyle.current.background }
var surface: Color { AnimeStyle.current.panel }

struct SavedDraft: Identifiable { let url: URL; let title: String; let note: String; let date: Date; var id: String { url.path } }

struct ContentView: View {
    @StateObject private var welcomeState:WelcomeSession
    init(welcomeInitiallyVisible:Bool=true) {
        let session=WelcomeSession();session.showWelcome=welcomeInitiallyVisible
        _welcomeState=StateObject(wrappedValue:session)
    }
    @EnvironmentObject var m: AppModel
    @AppStorage("studioInterfaceMode") private var interfaceMode="simple"
    @AppStorage("navigationExpanded") private var navigationExpanded=true
    @StateObject var editorOptions=EditorOptions()
    @StateObject var libraryOptions=ProfessionalVoiceSelection()
    @AppStorage("studioTheme") private var studioTheme = "system"
    @AppStorage("studioLanguage") private var studioLanguage = "system"
    @AppStorage("animeTheme") private var animeTheme = "studio"
    @AppStorage("savedVoiceProfileIDs") var savedVoiceIDs=""
    @AppStorage("voiceLibraryCategory") var voiceLibraryCategory="saved"
    @AppStorage("studioDensity") private var density = "comfortable"
    var body: some View {
        VStack(spacing:0) {
            if welcomeState.showWelcome {WelcomeStudio(model:m,showing:$welcomeState.showWelcome)} else if interfaceMode=="simple" {
                SimpleStudioHeader(model:m);Divider()
                if [.studio,.batch,.history,.script].contains(m.section) {SimpleWorkspace(model:m,editor:m.projectEditor)} else {resourcePage}
            } else {
            professionalHeader
            Divider()
            HStack(spacing:0) {
                if navigationExpanded {StudioNavigation(model:m,editor:m.projectEditor).transition(.move(edge:.leading).combined(with:.opacity));Divider()}
                Group {
                    if [.studio,.batch,.history,.script].contains(m.section) {UnifiedWorkspace(model:m,editor:m.projectEditor)}
                    else {resourcePage}
                }.frame(maxWidth:.infinity,maxHeight:.infinity)
            }

            }
        }.background(StudioPalette.base).font(.system(size:density=="large" ? 17:15)).controlSize(.regular).buttonStyle(StudioButtonStyle())
        .environment(\.locale, studioLocale).foregroundStyle(ink).tint(accent).preferredColorScheme(studioTheme == "dark" ? .dark : studioTheme == "light" ? .light : nil)
        .sheet(item:$m.advancedSettings) { draft in AdvancedSettingsView(model:m,draft:draft).environment(\.locale,studioLocale).preferredColorScheme(studioTheme == "dark" ? .dark : studioTheme == "light" ? .light : nil) }
        .onAppear {if welcomeState.showWelcome && UserDefaults.standard.bool(forKey:"randomAnimeTheme") {animeTheme=WelcomePalette.keys.randomElement() ?? "studio"}}
        .onReceive(NotificationCenter.default.publisher(for:Notification.Name("AniCantoWelcome"))) {_ in welcomeState.showWelcome=true}
        .onChange(of:interfaceMode) {m.switchWorkspaceMode($0)}
        .onChange(of:m.showWorkspaceSettings) {show in if show {m.section = .presets;m.showWorkspaceSettings=false}}
        .onChange(of:m.showProjectManager) {show in if show {m.section = .projects;m.showProjectManager=false}}
        .sheet(isPresented:$m.showAIResultSummary) { AIResultSummaryView(model:m).environment(\.locale,studioLocale) }
        .onChange(of:m.showLogs) {show in if show {if (UserDefaults.standard.string(forKey:"studioInterfaceMode") ?? "simple")=="professional" {m.section = .studio;m.projectEditor.workspacePage="terminal";m.showLogs=false} else {ProfessionalTerminalWindow.show(model:m)}} else {ProfessionalTerminalWindow.close()} }
         .onReceive(NotificationCenter.default.publisher(for:Notification.Name("AniCantoTutorial"))) {_ in welcomeState.showing=true}
        .overlay {
            StudioInformationDrawer(about:$m.showAbout,guide:$welcomeState.showing)
                .environment(\.locale,studioLocale)
        }
        .background(GeometryReader { proxy in
            Color.clear.onAppear { m.availableHeight = proxy.size.height }
                .onChange(of: proxy.size.height) { m.availableHeight = $0 }
        })
    }
    @ViewBuilder var resourcePage:some View {
        if m.section == .environment {professionalModelPage}
        else if m.section == .settings {ProfessionalPreferences(model:m)}
        else if m.section == .presets {ProfessionalSettingsView(model:m,startingCategory:m.setupCategory)}
        else if m.section == .projects {ProjectManagerView(model:m)}
        else {professionalVoicePage}
    }
    private var studioLocale:Locale { Locale(identifier:studioLanguage == "system" ? (Locale.preferredLanguages.first?.hasPrefix("en") == true ? "en" : "zh-HK") : studioLanguage) }
    var sidebar: some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack(spacing: 10) {
                AppEmblem().frame(width:36,height:36)
                VStack(alignment: .leading, spacing: 2) { Text("AniCanto").font(.system(size:18,weight:.black,design:.rounded)).lineLimit(1).minimumScaleFactor(0.8); Text(L("聲演你嘅動畫世界")).font(.system(size: 10, weight: .medium)).tracking(1) }
            }.padding(.bottom, 12).padding(.top, 8)
            ForEach(Array(Section.allCases.filter {![.script,.batch,.history,.voices].contains($0)}.enumerated()),id:\.element) { index,section in
                if index == 0 || index == 2 {
                    Text(LocalizedStringKey(index == 0 ? "製作與編輯" : "資源與設定"))
                        .font(.system(size:9,weight:.bold,design:.rounded)).tracking(1.3).foregroundStyle(.secondary).padding(.top,index == 0 ? 0 : 8).padding(.leading,10)
                }
                Button { m.section = section; if section == .script, m.showingOutput, let url = m.previewURL { m.preview(url, isOutput: false) } } label: {
                    HStack(spacing:10) {
                        Image(systemName:section.icon).frame(width:20)
                        Text(LocalizedStringKey(section.rawValue)).frame(maxWidth:.infinity,alignment:.leading)
                        if m.section == section { Image(systemName:"chevron.right").font(.caption2.bold()) }
                    }.font(.system(size:13,weight:m.section == section ? .bold:.medium)).padding(10)
                        .foregroundStyle(m.section == section ? accent : ink.opacity(0.7))
                        .background(m.section == section ? surface.opacity(0.94) : .clear,in:RoundedRectangle(cornerRadius:12))
                        .overlay(alignment:.leading) { if m.section == section { Capsule().fill(accent).frame(width:3,height:20) } }
                }.buttonStyle(.plain)
            }
            StudioCompanion(model:m).frame(minHeight:130,maxHeight:.infinity).layoutPriority(1)
            HStack {
                Image(systemName:"cpu").foregroundStyle(accent)
                Text("\(ProcessInfo.processInfo.physicalMemory / 1_073_741_824) GB").font(.caption)
                Spacer()
                Text("v\(Bundle.main.object(forInfoDictionaryKey:"CFBundleShortVersionString") as? String ?? "—")").font(.caption2.monospaced())
            }.foregroundStyle(.secondary).padding(8).background(AnimeStyle.current.panel,in:RoundedRectangle(cornerRadius:10)).help("Apple Silicon · 本機模型工作室")

        }.padding(14).frame(width: 180).background(FrameChrome(sidebar:true)).overlay(alignment:.trailing) { Rectangle().fill(AnimeStyle.current.secondary.opacity(0.20)).frame(width:1) }
    }
    var studio: some View {
        VStack(alignment:.leading,spacing:14) {
            ViewThatFits(in:.horizontal) {
                HStack(alignment:.top,spacing:16) {
                    studioMedia.frame(minWidth:440,maxWidth:.infinity)
                    essentialSettings.frame(width:340)
                }
                VStack(spacing:14) { studioMedia; essentialSettings }
            }
            if m.showingOutput { PlayerTrackControls(player:m.player) }
        }
    }
    @ViewBuilder var studioMedia:some View {
        if m.video == nil && m.output == nil {WelcomeScene(model:m)} else {studioVideo}
    }
    var studioVideo: some View {
HStack(alignment: .top, spacing: 16) {
                VStack(alignment: .leading, spacing: 12) {
                    HStack { Text(L("01  影片")).font(.headline); Spacer(); Toggle(L("大預覽"), isOn: $m.largePreview).toggleStyle(.checkbox); Button(L("批量匯入"), action: m.chooseBatch).disabled(m.busy); Button(L("匯入 MP4 / MKV"), action: m.chooseVideo).disabled(m.busy) }
                    AspectPlayerFrame(aspect: m.videoAspect, maxHeight: m.largePreview && m.video != nil ? 440 : 250) {
                    ZStack {
                        RoundedRectangle(cornerRadius: 20).fill(m.video == nil ? surface : Color.black)
                        if m.preparingPreview {
                            VStack(spacing: 14) {
                                ProgressView(value: m.progress).frame(width: 240)
                                Text(L("準備影片預覽")).font(.headline)
            Text(localizedProgressDetail(m.detail)).font(.caption).multilineTextAlignment(.center)
                                Text(L("首次讀取雲端檔案可能需要等候下載。")).font(.caption).foregroundStyle(.white.opacity(0.65))
                            }.foregroundStyle(.white).padding(24)
                        } else if let message = m.playbackError {
                            VStack(spacing: 12) { Image(systemName: "exclamationmark.triangle"); Text(message).multilineTextAlignment(.center) }.foregroundStyle(.white).padding(24)
                        } else if m.video != nil || m.output != nil {
                            if m.subtitleSource == "burned" && !m.showingOutput {
                                OCRSelectionPlayer(player: m.player, selecting: m.selectingOCR, region: $m.ocrRegion).clipShape(RoundedRectangle(cornerRadius: 13))
                            } else { CaptionedPlayer(player: m.player, captions: m.previewCaptions, seconds: m.playbackSeconds).clipShape(RoundedRectangle(cornerRadius: 13)) }
                        }
                        else {
                            HStack(spacing: 12) {
                                VStack(alignment: .leading, spacing: 16) {
                                    Text("YOUR ANIME · YOUR VOICE").font(.system(size: 10, weight: .bold, design: .rounded)).tracking(2).foregroundStyle(accent)
                                    Text(L("下一場，\n輪到你配音。")).font(.system(size: 23, weight: .bold, design: .rounded))
                                    Text(L("拖入動畫，開始你嘅廣東話配音。\nMP4 / MKV / MOV · 全程本機處理")).font(.caption).foregroundStyle(.secondary).lineSpacing(5)
                                    Button(action: m.chooseVideo) { Label(L("選擇影片"), systemImage: "plus").padding(.horizontal, 12).padding(.vertical, 5) }.buttonStyle(.borderedProminent)
                                }
                            }.padding(24).foregroundStyle(ink)
                        }
                    }
                    }
                        .onDrop(of: [.fileURL], isTargeted: nil) { providers in
                            guard !m.busy, let p = providers.first else { return false }
                            _ = p.loadObject(ofClass: URL.self) { url, _ in if let url { Task { @MainActor in m.loadVideo(url) } } }
                            return true
                        }
                    if m.subtitleSource == "burned" && m.video != nil {
                        HStack {
                            Text(LocalizedStringKey(m.selectingOCR ? "拖拉重畫方框，只包住完整字幕，唔好包住水印。" : "先暫停喺有字幕嘅畫面，再框選字幕範圍。")).font(.caption).foregroundStyle(.secondary)
                            Spacer()
                            if m.selectingOCR {
                                Button(L("重設方框")) { m.ocrRegion = OCRRegion() }
                                Button(L("完成並試讀"), action: m.finishOCRSelection).buttonStyle(.borderedProminent)
                            } else { Button(L("框選字幕範圍"), action: m.beginOCRSelection).buttonStyle(.borderedProminent) }
                        }.disabled(m.busy)
                    }
                    HStack {
                        Text((m.showingOutput ? m.output?.lastPathComponent : m.video?.lastPathComponent) ?? "未選擇影片").font(.caption).lineLimit(1)
                        if m.video != nil || m.output != nil { Text(abs(m.videoAspect - 4.0/3.0) < 0.03 ? "4:3" : (abs(m.videoAspect - 16.0/9.0) < 0.03 ? "16:9" : "原片比例")).font(.caption).foregroundStyle(.secondary) }
                        Spacer()
                        Text(L("內置 VLC")).font(.caption).foregroundStyle(.secondary)
                        if let video = m.previewURL { Button(L("原片")) { m.preview(video, isOutput: false) }.disabled(!m.showingOutput) }
                        if let output = m.output { Button(L("配音結果")) { m.preview(output, isOutput: true) }.disabled(m.showingOutput) }
                    }
                }.card()
            }
    }
    var conversionActions: some View {
HStack {
                if m.reviewURL != nil { Button(L("影片編輯／批核")) { m.section = .history } }
                Spacer()
                if let output = m.output {
                    Button(L("開啟輸出位置")) { NSWorkspace.shared.activateFileViewerSelecting([output]) }
                    Button(L("移到垃圾桶"), role: .destructive) { m.trashOutput(output) }.disabled(m.busy)
                }
                Button(action: m.convert) { Label(m.busy ? "處理中" : (m.autoApprove ? "一鍵轉換並輸出" : "翻譯並預覽廣東話稿"), systemImage: "waveform.badge.plus").padding(.horizontal, 16).padding(.vertical, 7) }.buttonStyle(.borderedProminent).disabled(m.busy || m.selectingOCR || m.video == nil)
            }
    }
    var ocrControls: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(L("用影片下方「框選字幕範圍」，直接拖拉方框。只辨識框內畫面，黑邊唔會計入範圍。")).font(.caption).foregroundStyle(.secondary)
            Picker(L("字幕字色"), selection: $m.ocrColor) { Text(L("白色／淺灰")).tag("white"); Text(L("黃色")).tag("yellow"); Text(L("保留原色（預設）")).tag("original") }
            Toggle(L("暫停只出現一個取樣畫面嘅字"), isOn: $m.ocrStable).font(.caption)
            Text(L("預設保留原色，避免細字被過濾。白字／黃字可選；快速字幕可能被暫停，可喺校稿頁恢復。")).font(.caption).foregroundStyle(.secondary)
            Button(L("用目前畫面預覽 OCR"), action: m.previewOCR).disabled(m.video == nil || m.selectingOCR)
        }.disabled(m.busy)
    }
    func ocrImage(_ url: URL, title: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title).font(.caption).foregroundStyle(.secondary)
            if let image = NSImage(contentsOf: url) { Image(nsImage: image).resizable().scaledToFit().frame(maxHeight: 160) }
        }.frame(maxWidth: .infinity)
    }
    func playbackTime(_ value: Double) -> String { String(format: "%02d:%02d", Int(max(0,value)) / 60, Int(max(0,value)) % 60) }
    var reviewPlayback: some View {
        VStack(spacing: 8) {
            AspectPlayerFrame(aspect: m.videoAspect, maxHeight: m.largePreview ? min(460, m.availableHeight * 0.42) : min(260, m.availableHeight * 0.35)) { CaptionedPlayer(player: m.player, captions: editorCaptions, seconds: m.playbackSeconds).clipShape(RoundedRectangle(cornerRadius: 10)) }
            HStack(spacing: 12) {
                Button(L("播放／暫停")) { if m.player.rate == 0 { m.player.play() } else { m.player.pause() } }
                Toggle(L("大預覽"), isOn: $m.largePreview).toggleStyle(.checkbox)
                Text(playbackTime(m.playbackSeconds)).font(.caption.monospacedDigit())
                Slider(value: Binding(get: { min(m.playbackSeconds, m.playbackDuration) }, set: { m.seekVideo($0) }), in: 0...max(1,m.playbackDuration), onEditingChanged: { m.seeking = $0 }).accessibilityLabel("校稿影片時間軸")
                Text(playbackTime(m.playbackDuration)).font(.caption.monospacedDigit())
            }
            SubtitleTimeline(model:m).frame(height:72)
            Text(L("拖動時間軸或點選字幕片段；修改台詞會即時疊加喺影片上，重新配音後先更新成品聲音。")).font(.caption).foregroundStyle(.secondary)
        }
    }
    var script: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                VStack(alignment: .leading, spacing: 6) {
                    Text(L("字幕編輯")).font(.title2.bold())
                    Text(m.scriptVideo.isEmpty ? "先喺工作區匯入影片並開始翻譯。" : "\(m.scriptVideo) · \(m.scriptCues.filter { $0.included }.count) / \(m.scriptCues.count) 句啟用").foregroundStyle(.secondary)
                }
                Spacer()
                if m.reviewURL != nil {
                    Button(L("儲存修改"),action:m.saveDraft).disabled(m.busy)
                    Button(m.scriptApproved ? "用修改稿重新配音" : "批准並開始配音", action: m.approveScript).buttonStyle(.borderedProminent).disabled(m.busy)
                }
            }
            if m.reviewURL != nil {
                Button {m.advancedSettings=WorkflowDraft(model:m,topic:.editor)} label:{Label(L("編輯工具"),systemImage:"slider.horizontal.3")}.disabled(m.busy)
            }
            if m.reviewURL != nil {
                Toggle(L("顯示全部台詞"),isOn:$editorOptions.showAll).toggleStyle(.checkbox)
                LazyVStack(spacing: 12) {
                    ForEach(editorIndices, id: \.self) { index in
                        VStack(alignment: .leading, spacing: 10) {
                            HStack {
                                Text("第 \(index+1) 句").font(.headline)
                                Button(m.scriptCues[index].timing) { m.seekCue(m.scriptCues[index]) }.font(.caption.monospaced())
                                Button(L("播放呢句")) { m.seekCue(m.scriptCues[index], play: true) }
                                Spacer()
                                Toggle(L("配音呢句"), isOn: $m.scriptCues[index].included).toggleStyle(.checkbox).disabled(m.busy)
                            }
                            if let before = m.scriptCues[index].originalCantonese { Text(L("精簡前：") + before).font(.caption).foregroundStyle(.secondary) }
                            if let note = m.scriptCues[index].reviewNote { Text(note).font(.caption).foregroundStyle(.orange) }
                            if let note = m.scriptCues[index].speakerNote, !note.isEmpty { Text(note).font(.caption).foregroundStyle(.secondary) }
                            HStack(alignment: .top, spacing: 20) {
                                VStack(alignment: .leading, spacing: 6) {
                                    Text(m.scriptCues[index].japanese == nil ? "辨識原文" : "日語原聲辨識 · 聲音時間").font(.caption).foregroundStyle(.secondary)
                                    Text(m.scriptCues[index].text).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading)
                                    if let hint = m.scriptCues[index].subtitleHint, !hint.isEmpty {
                                        Text(L("中文字幕參考（唔係配音時段）")).font(.caption).foregroundStyle(.secondary)
                                        Text(hint).font(.callout).foregroundStyle(.secondary).textSelection(.enabled)
                                    }
                                }.frame(maxWidth: .infinity)
                                VStack(alignment: .leading, spacing: 6) {
                                    if m.reviewUsesGSV {
                                        Picker(L("已配對角色（可修正）"), selection: Binding(get: { m.scriptCues[index].speakerId ?? (m.reviewVoices.count == 1 ? m.reviewVoices[0].id : "") }, set: { m.scriptCues[index].speakerId = $0 })) {
                                            Text(L("按上方自動配對")).tag("")
                                            ForEach(m.showSavedVoiceChoices ? m.voiceProfiles : m.currentVoiceProfiles) { profile in Text(profile.name).tag(profile.id) }
                                        }.disabled(m.busy)
                                    }
                                    Text(L("廣東話台詞")).font(.caption).foregroundStyle(.secondary)
                                    TextField(L("輸入廣東話台詞"), text: $m.scriptCues[index].cantonese, axis: .vertical).lineLimit(2...8).textFieldStyle(.roundedBorder).disabled(m.busy || !m.scriptCues[index].included)
                                }.frame(maxWidth: .infinity)
                            }
                            if let timing = m.timingRows.first(where: { $0.start == m.scriptCues[index].start && $0.end == m.scriptCues[index].end }) {
                                HStack {
                                    Text(String(format: "上次試音 %.2f 秒 ／可用 %.2f 秒", timing.seconds, timing.slot)).font(.caption).foregroundStyle(timing.needsReview ? Color.red : .secondary)
                                    if let difference = timing.sourceEndError, abs(difference) > 0.5 {
                                        Text(String(format: difference < 0 ? "較日語提早 %.2f 秒收尾" : "較日語遲 %.2f 秒收尾", abs(difference))).font(.caption).foregroundStyle(.orange)
                                    }
                                    if timing.phraseAligned == true { Text(L("已保留句內停頓")).font(.caption).foregroundStyle(.secondary) }
                                    Button(L("聽上次配音")) { m.audition(URL(fileURLWithPath: timing.audio), label: "第 \(index+1) 句上次配音") }
                                    if timing.needsReview { Button(L("AI 改短建議")) { m.shortenCue(index) }.disabled(m.busy) }
                                }
                            }
                        }.card().overlay(RoundedRectangle(cornerRadius: 16).stroke(m.selectedCue == index ? accent : .clear, lineWidth: 2)).opacity(m.scriptCues[index].included ? 1 : 0.65)
                    }
                }
            }
        }
    }
    var environment: some View {
        VStack(alignment:.leading,spacing:16) {
            if m.environmentCategory=="presets" {DeploymentPresets(model:m)}
            if m.environmentCategory=="voices" {VoiceModelLibrary(model:m)}
            if m.environmentCategory=="text" {modelManager}
            if m.environmentCategory=="speech" {
                Text(L("日語主辨識")).font(.headline)
                ModelLibrary(model:m,category:"speech",role:"speech")
                Divider();Text(L("獨立覆聽 · Qwen ASR")).font(.headline)
                ModelLibrary(model:m,category:"asr",role:"asr")
                DisclosureGroup(L("角色參考／字幕後備辨識")) {ModelLibrary(model:m,category:"speech",role:"referenceSpeech")}

            }
            if m.environmentCategory=="audio" {
                component("背景音樂／音效分離",subtitle:"Mel-Band RoFormer · 約 913 MB",ready:m.separatorReady,icon:"waveform.path",button:"下載／修復") {let e=m.engine;m.task("部署背景分離") {try e.installDubbing("separator")}}
                component("自動角色配對",subtitle:"WeSpeaker 聲紋 · 約 27 MB · 本機 CPU",ready:m.speakersReady,icon:"person.2",button:"下載／修復") {let e=m.engine;m.task("部署自動配對") {try e.ensureAutoSpeakers()}}
            }
            if m.environmentCategory=="runtime" {
                Text(L("程式庫內置於 App；模型下載到專用資料夾。首次部署需要網絡，完成後推理使用本機。"))
                component("Python 3.11",subtitle:"各引擎獨立環境，毋須系統 Python",ready:m.runtimeReady,icon:"shippingbox",button:"檢查／部署") {let e=m.engine;m.task("檢查環境") {try e.installRuntime()}}
                component("本機文字引擎",subtitle:"Ollama · 只監聽本機",ready:m.ollamaReady,icon:"cpu",button:"啟動／修復") {let e=m.engine;m.task("設定文字引擎") {if !e.ollamaReady {try e.installOllama()};try e.startServer()}}
                Button(L("開啟模型資料夾")) {NSWorkspace.shared.open(m.engine.root)}
            }
        }
    }
    func component(_ title: String, subtitle: String, ready: Bool, icon: String, button: String, action: @escaping () -> Void) -> some View {
        HStack(spacing: 16) {
            Image(systemName: icon).font(.title2).foregroundStyle(accent).frame(width: 44, height: 44).background(accent.opacity(0.08), in: RoundedRectangle(cornerRadius: 10))
            VStack(alignment: .leading, spacing: 6) { Text(LocalizedStringKey(title)).font(.headline); Text(LocalizedStringKey(subtitle)).font(.caption).foregroundStyle(.secondary) }
            Spacer()
            Label(LocalizedStringKey(ready ? "已就緒" : "未部署"), systemImage: ready ? "checkmark.circle.fill" : "circle.dashed").font(.caption).foregroundStyle(ready ? .green : .secondary)
            Button(LocalizedStringKey(button), action: action).disabled(m.busy)
        }.card()
    }
    var history: some View {
        VStack(alignment: .leading, spacing: 18) {
            Text(L("完成嘅影片")).font(.title2.bold())
            Text(L("移到垃圾桶只會移走生成嘅 MP4；原片、字幕同校稿會保留。可以喺 Finder 垃圾桶還原。")).font(.caption).foregroundStyle(.secondary)
            Button(L("重新整理"), action: m.refresh).disabled(m.busy)
            if m.history.isEmpty { Text(L("仲未有輸出。匯入影片後，可以先試一段 3 分鐘片段。")).foregroundStyle(.secondary).card() }
            ForEach(m.history, id: \.path) { url in
                VStack(alignment:.leading,spacing:10) {
                HStack { Image(systemName: "film").foregroundStyle(accent); VStack(alignment: .leading) { Text(url.lastPathComponent).font(.headline); Text(url.deletingLastPathComponent().lastPathComponent).font(.caption.monospaced()).foregroundStyle(.secondary) }; Spacer(); Button(L("播放")) { m.output = url; m.preview(url, isOutput: true); m.section = .studio }; Button(L("檔案")) { NSWorkspace.shared.activateFileViewerSelecting([url]) }; Button(L("移到垃圾桶"), role: .destructive) { m.trashOutput(url) }.disabled(m.busy) }
                if let review=m.editableReview(for:url) { Button(L("字幕編輯")) { m.openDraft(review) }.disabled(m.busy) }
                PerformanceSummary(output:url) { seconds in m.output = url; m.preview(url,isOutput:true); m.seekVideo(seconds); m.player.play(); m.section = .studio }
                ValidationSummary(output:url) { seconds in m.output = url; m.preview(url,isOutput:true); m.seekVideo(seconds); m.player.play(); m.section = .studio }
                }.card()
            }
            DisclosureGroup(L("工作資料與手動校對")) {
            HStack {
                Text(L("已保存嘅校稿")).font(.title2.bold())
                Spacer()
                Button(L("清除全部校稿…"), role: .destructive) { m.trashDrafts(m.savedDrafts.map(\.url)) }.disabled(m.busy || m.savedDrafts.isEmpty)
            }
            Text(L("新稿同舊稿分開保存；可繼續校稿，或者用日語原聲重新分句。")).font(.caption).foregroundStyle(.secondary)
            ForEach(m.savedDrafts) { draft in
                HStack {
                    VStack(alignment: .leading) { Text(draft.title).font(.headline); Text(draft.note).font(.caption).foregroundStyle(.secondary) }
                    Spacer()
                    Button(L("繼續校稿")) { m.openDraft(draft.url) }.disabled(m.busy)
                    Button(L("清除…"), role: .destructive) { m.trashDrafts([draft.url]) }.disabled(m.busy)
                }.card()
            }
            }.card()

        }
    }
    private func uiDuration(_ seconds:Double)->String { ProcessingClock.duration(seconds,english:studioLocale.identifier.hasPrefix("en")) }
    var status: some View {
        let displayed = WorkProgress(pass:m.processingClock.passProgress,count:m.processingClock.passLabel,backend:m.progress)
        return
        VStack(alignment: .leading, spacing: 8) {
            if let step=m.processingClock.journeyStep {
                ConversionQuest(step:step,visited:m.processingClock.journeyVisited,running:m.busy,failed:m.error != nil,finished:!m.busy && m.stage == "完成" && m.error == nil)
                if !m.processingClock.voiceTrackLabel.isEmpty {Text(m.processingClock.voiceTrackLabel).font(.caption.bold()).foregroundStyle(accent)}
            }
            HStack {
                Text(LocalizedStringKey(m.stage)).font(.headline)
                if m.busy, let p = displayed.value {
                    Text(LocalizedStringKey(displayed.label)).font(.caption).foregroundStyle(.secondary)
                    Text("\(Int(p * 100))%").font(.caption.monospacedDigit()).foregroundStyle(.secondary)
                }
                Spacer(); if m.busy { Button(L("取消／暫停排程")) { m.queuePaused=true;m.engine.cancel() } }
            }
            if m.busy {
                StudioProgressBar(value:displayed.value)
                    .accessibilityIdentifier("conversion-progress")
                if displayed.value == nil { Text(L("處理中，等待進度回報…")).font(.caption).foregroundStyle(.secondary) }
            }
            if m.processingClock.started != nil {
                TimelineView(.periodic(from: .now, by: 1)) { context in
                    VStack(alignment: .leading, spacing: 3) {
                        Text(L("已用時間：") + uiDuration(m.processingClock.elapsed(at: context.date)))
                        if m.busy {
                            if let seconds = m.processingClock.remaining(at: context.date), seconds>0 {
                                Text(String(format:L("本輪 %@ 預計剩餘：%@ – %@"),L(m.stage),uiDuration(seconds * 0.8),uiDuration(seconds * 1.3)))
                            } else { Text(L(m.processingClock.estimateDelayed(at:context.date) ? m.processingClock.estimateBasis(at:context.date):m.processingClock.waitingReason)) }
                            if let remaining = m.processingClock.overallRemaining(at:context.date) {
                                Text(L("整個工作預計剩餘：") + uiDuration(remaining * 0.7) + " – " + uiDuration(remaining * 1.5))
                                Text(L("按本機相同設定嘅已完成工作估算；對白密度同修正次數會影響時間。"))
                            } else { Text(L("未有相同設定嘅完整時間紀錄，暫時只估本輪；重用快取時唔套用全片估算。")) }
                        }
                        DisclosureGroup(L("各階段已用時間")) {
                            ForEach(m.processingClock.stages(at: context.date), id: \.0) { row in
                                HStack { Text(LocalizedStringKey(row.0)); Spacer(); Text(uiDuration(row.1)) }
                            }
                        }
                    }.font(.caption).foregroundStyle(.secondary).monospacedDigit()
                }
            }
            Text(localizedProgressDetail(m.detail)).font(.caption).foregroundStyle(m.error == nil ? .secondary : Color.red).lineLimit(3).textSelection(.enabled)
            if m.error != nil { Button(L("複製錯誤詳情")) { NSPasteboard.general.clearContents(); NSPasteboard.general.setString(m.logs.suffix(30).joined(separator: "\n"), forType: .string) }.font(.caption) }
        }
    }
}

extension View {
    func card() -> some View { modifier(AnimeCard()) }
}

// Both source and output videos are decoded by bundled libVLC. AVPlayerItem only carries the file URL.
struct NativePlayer: NSViewRepresentable {
    let player: CantoPlayer
    var showsControls=true
    func makeNSView(context: Context) -> VLCVideoView {
        let view = VLCVideoView()
        view.player = player
        return view
    }
    func updateNSView(_ view: VLCVideoView, context: Context) {
        if view.player !== player { view.player = player }
        view.showsControls=showsControls
    }
}

struct CaptionedPlayer: View {
    let player: CantoPlayer
    let captions: [PreviewCaption]
    let seconds: Double
    var bottomFraction: Double? = nil
    var sizeFraction: Double? = nil
    var showsControls=true
    var topAligned=false
    var body: some View {
        GeometryReader { geometry in
            ZStack(alignment:topAligned ? .top:.bottom) {
                NativePlayer(player:player,showsControls:showsControls)
                let caption = PreviewCaption.text(at: seconds, in: captions)
                if !caption.isEmpty {
                    Text(caption).font(.system(size: sizeFraction.map {max(10,geometry.size.height*$0)} ?? max(18, min(30, geometry.size.width / 30)), weight: .semibold))
                        .multilineTextAlignment(.center).foregroundStyle(.white)
                        .padding(.horizontal, 10).padding(.vertical, 5)
                        .background(.black.opacity(0.78), in: RoundedRectangle(cornerRadius: 5))
                        .padding(.horizontal,16).padding(topAligned ? .top:.bottom,bottomFraction.map {geometry.size.height*$0} ?? 44)
                        .allowsHitTesting(false).accessibilityIdentifier("preview-caption")
                }
            }
        }
    }
}
