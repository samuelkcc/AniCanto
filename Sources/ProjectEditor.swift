import SwiftUI
import Combine
import AVKit
import UniformTypeIdentifiers
import CryptoKit

struct EditSegment: Codable, Identifiable, Equatable {
    var id = UUID().uuidString
    var sources: [Int]
    var start: Double
    var end: Double
    var captionStart: Double
    var captionEnd: Double
    var text: String
    var captionText: String = ""
    var original: String
    var speakerId: String
    var enabled = true
    var take = 42
    var rate = 1.0
    var trimStart = 0.0
    var trimEnd = 0.0
    var audioTake: String? = nil
    var audioLength: Double? = nil
    var audioAcceptedHistoryID:String? = nil
    var english: String? = nil
    var manual: Bool? = nil
    var sourceNote: String? = nil
    var preserveOriginalSpeech:Bool? = nil
    var scriptSyncSource:String? = nil
}
struct EditClip: Codable, Identifiable, Equatable {
    var id = UUID().uuidString
    var start: Double
    var end: Double
    var enabled = true
    var ripple = true
}
struct EditDocument: Codable, Equatable {
    var id = UUID().uuidString
    var created = ISO8601DateFormatter().string(from: Date())
    var review: String
    var segments: [EditSegment]
    var clips: [EditClip]
    var playhead = 0.0
    var voiceStyleDefaultRevision:Int? = nil
    var videoOverride: String? = nil
    var backgroundGain = 0.8
    var backgroundDucking:Bool? = nil
    var captionBottom = 0.045
    var captionSize = 0.043
    var pendingChanges: Bool? = nil
    var dubLanguages: [String]? = nil
    var cantonesePronunciationText:String? = nil
    var subtitleOutput:String? = nil
    var voiceStyleMode:String? = nil
    var subtitleModes:[String]? = nil
    var originalSubtitleStreams:[Int]? = nil
    var autoSkipOP:Bool? = nil
    var translationSource:String? = nil
    var translateOPED:Bool? = nil
}
struct EditorialTask: Codable, Identifiable {
    var id: String
    var review: String
    var submission: String
    var status = "queued"
    var message = ""
}
struct ProjectRow: Identifiable {
    var id: String
    var video: String
    var review: URL?
    var status: String
    var previewJob: URL? = nil
    var name: String { URL(fileURLWithPath:video).lastPathComponent }
}
struct EditVersion: Identifiable {
    var id: String
    var status: String
    var output: URL?
    var report: URL?
    var folder: URL
    var created: String
    var processingSeconds:Double=0
}

/// Editor state never aliases AppModel.scriptCues or the active worker's review.json.
@MainActor final class ProjectEditor: ObservableObject {
    var productionSelections:[String:ProductionSelection]=[:]
    var readOnlyPreview=false
    @Published var projects: [ProjectRow] = []
    @Published var document: EditDocument? {didSet {invalidateTakes()}}
    @Published var sourceCaptions:[PreviewCaption]=[]
    @Published var selected: String?
    @Published var auditionVoiceStyle:String? = "clone" {didSet {invalidateTakes()}}
    @Published var selectedSegment: String?
    @Published var versions: [EditVersion] = []
    @Published var tab = "edit"
    var failedTracks:[String:String] {reportSnapshot["failedEngines"] as? [String:String] ?? [:]}
    var segmentIssues:[[String:Any]] {reportSnapshot["segmentIssues"] as? [[String:Any]] ?? []}
    var trackQuality:[[String:Any]] {qualitySnapshot}
    @Published var versionPreviewTakes:[ProcessingVoiceTake]=[]
    @Published var timelineAudioRegions:[String:[TimelineAudioRegion]]=[:]
    @Published var timelineAudioStates:[String:String]=[:]
    @Published var timelineMissingRegions:[String:[TimelineMissingRegion]]=[:]
    @Published var generationSeconds:Double=0
    @Published var generationBreakdown:[String:Double]=[:]
    var evidenceFolders:[String:URL]=[:]
    private var timingRows:[String:[[String:Any]]]=[:]
    private var trackIssueRows:[String:[[String:Any]]]=[:]
    private var fallbackRows:[String:[[String:Any]]]=[:]
    var fallbackEvidence:[String:[[String:Any]]] {fallbackRows}
    var channelGenerationIssues:[[String:Any]] {timingRows.flatMap {key,rows in
        let parts=key.split(separator:":");guard parts.count==2 else{return [[String:Any]]()}
        return VoiceFailureEvidence.rows(timing:rows,issues:trackIssueRows[key] ?? [],engine:String(parts[0]),language:String(parts[1]))
    }}
    private var previewRows:[String:[[String:Any]]]=[:]
    private var recordedModelVersions:[String:String]=[:]
    private var reportSnapshot:[String:Any]=[:]
    private var qualitySnapshot:[[String:Any]]=[]
    func recordedTrackTitle(_ engine:String,language:String)->String {
        if engine=="gpt-sovits-v3" {return "GPT V3 · "+L("舊音軌")}
        if engine=="gpt-sovits-v2",let version=recordedModelVersions[engine+":"+language],version != "v2ProPlus" {return "GPT "+gsvModelTitle(version)+" · "+L("舊音軌")}
        return VoiceEngineChoice.all.first {$0.id==engine}?.shortTitle ?? "Qwen · "+L("舊音軌")
    }
    private var takeCache:[String:(path:String,length:Double)]=[:]
    private var takeMisses=Set<String>()
    var cueVoiceCache:[String:CueVoiceRecording]=[:]
    var cueVoiceMisses=Set<String>()
    private var evidenceFingerprint=""
    private var evidenceProject=""
    private var audioHeaders:[String:(size:UInt64,modified:Date,length:Double)]=[:]
    private(set) var takeLookupCount=0
    var studioIssueCache:[StudioIssue]?
    var warningSegmentCache:[String:Set<String>]=[:]
    func invalidateTakes() {takeCache.removeAll();takeMisses.removeAll();cueVoiceCache.removeAll();cueVoiceMisses.removeAll();studioIssueCache=nil;warningSegmentCache.removeAll()}
    func refreshEvidence() {
        guard let review=selectedRow?.review else{versionPreviewTakes=[];invalidateTakes();evidenceFingerprint="";evidenceProject="";timelineAudioRegions=[:];timelineAudioStates=[:];timelineMissingRegions=[:];reportSnapshot=[:];qualitySnapshot=[];fallbackRows=[:];previewRows=[:];timingRows=[:];trackIssueRows=[:];generationSeconds=0;generationBreakdown=[:];return}
        let root=review.deletingLastPathComponent()
        func json(_ url:URL)->[String:Any] {ProcessingAudioIndex.read(url)}
        if !readOnlyPreview,var draft=document {
            let base=json(root.appendingPathComponent("editor-base.json"))["cues"] as? [[String:Any]] ?? []
            let current=json(review)["cues"] as? [[String:Any]] ?? []
            if EditorScriptSync.merge(&draft,base:base,current:current)>0 {
                if let old=document {undoStack.append(old)}
                document=draft
                try? save()
                invalidateTakes()
            }
        }
        let processing=json(root.appendingPathComponent("processing-time.json"))
        generationSeconds=processing["seconds"] as? Double ?? 0
        generationBreakdown=processing["categorySeconds"] as? [String:Double] ?? [:]
        let versionFolders=(try? FileManager.default.contentsOfDirectory(at:root.appendingPathComponent("versions"),includingPropertiesForKeys:nil)) ?? []
        for folder in versionFolders {
            for (key,value) in json(folder.appendingPathComponent("processing-time.json"))["categorySeconds"] as? [String:Double] ?? [:] {generationBreakdown[key,default:0]+=value}
        }
        generationSeconds += versionFolders.reduce(0) {$0+(json($1.appendingPathComponent("processing-time.json"))["seconds"] as? Double ?? 0)}
        let renderedVersions=versionFolders.filter {folder in let status=json(folder.appendingPathComponent("version.json"))["status"] as? String ?? "";return ["running","complete","partial"].contains(status) || (status=="failed" && FileManager.default.fileExists(atPath:folder.appendingPathComponent("dialogue-delivery-audit.json").path))}.sorted {(json($0.appendingPathComponent("version.json"))["created"] as? String ?? "") > (json($1.appendingPathComponent("version.json"))["created"] as? String ?? "")}
        if !dirty,!readOnlyPreview,var draft=document {
            let old=draft
            for version in renderedVersions {
                for row in json(version.appendingPathComponent("filled-script-gaps.json"))["rows"] as? [[String:Any]] ?? [] {
                    guard let index=draft.segments.firstIndex(where:{$0.id==row["id"] as? String}),draft.segments[index].text.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty,draft.segments[index].speakerId==row["speakerId"] as? String,abs(draft.segments[index].start-(row["start"] as? Double ?? -1))<0.001,abs(draft.segments[index].end-(row["end"] as? Double ?? -1))<0.001,let text=row["text"] as? String,!text.isEmpty else{continue}
                    draft.segments[index].text=text
                }
            }
            if draft != old {undoStack.append(old);document=draft;try? save()}
        }
        let evidenceRoots=renderedVersions+[root]
        let childFolders=evidenceRoots.flatMap {(try? FileManager.default.contentsOfDirectory(at:$0.appendingPathComponent("tracks"),includingPropertiesForKeys:nil)) ?? []}
        let auditionFolders=versionFolders.filter {json($0.appendingPathComponent("version.json"))["status"] as? String=="preview"}
        let evidenceFiles=(evidenceRoots+auditionFolders).flatMap {folder in [folder]+["version.json","report.json","review.json","track-progress.json","dialogue-delivery-audit.json","audio-preview.json","timing.json"].map {folder.appendingPathComponent($0)}}+childFolders.flatMap {folder in [folder]+["report.json","review.json","timing.json","segment-issues.json","validation.json","audio-preview.json","fallbacks.json"].map {folder.appendingPathComponent($0)}}
        let fingerprint=evidenceFiles.map {url -> String in let a=(try? FileManager.default.attributesOfItem(atPath:url.path)) ?? [:];return url.path+String((a[.modificationDate] as? Date)?.timeIntervalSince1970 ?? 0)+String(describing:a[.size])}.joined(separator:"|")
        if evidenceProject==root.path,evidenceFingerprint==fingerprint {return}
        evidenceProject=root.path;evidenceFingerprint=fingerprint
        if let video=config["video"] as? String {
            ProcessingAudioIndex.request(root,video:video) {[weak self] result in
                guard let self,self.selectedRow?.review?.deletingLastPathComponent()==root else{return}
                if self.versionPreviewTakes != result {self.versionPreviewTakes=result;self.evidenceFingerprint="";self.invalidateTakes()}
            }
        } else {versionPreviewTakes=[]}
        invalidateTakes();reportSnapshot=[:];qualitySnapshot=[];timelineAudioRegions=[:];timelineAudioStates=[:];timelineMissingRegions=[:];evidenceFolders=[:];previewRows=[:];timingRows=[:];trackIssueRows=[:];fallbackRows=[:]
        let report=json(root.appendingPathComponent("report.json"));reportSnapshot=renderedVersions.map {json($0.appendingPathComponent("report.json"))}.first {!$0.isEmpty} ?? report
        recordedModelVersions=[:]
        var tracks:[[String:Any]]=[]
        for version in renderedVersions {
            let progress=json(version.appendingPathComponent("track-progress.json"))["tracks"] as? [[String:Any]] ?? []
            let reports=json(version.appendingPathComponent("report.json"))["tracks"] as? [[String:Any]] ?? []
            for track in progress.compactMap({row -> [String:Any]? in guard let engine=row["engine"] as? String,let folder=row["folder"] as? String else{return nil};return ["engine":engine,"language":row["language"] as? String ?? "yue","report":URL(fileURLWithPath:folder).appendingPathComponent("report.json").path]})+reports {
                if !tracks.contains(where:{$0["engine"] as? String==track["engine"] as? String && $0["language"] as? String==track["language"] as? String}) {tracks.append(track)}
            }
        }
        let progress=json(root.appendingPathComponent("track-progress.json"))["tracks"] as? [[String:Any]] ?? []
        for track in progress.compactMap({row -> [String:Any]? in guard let engine=row["engine"] as? String,let folder=row["folder"] as? String else{return nil};return ["engine":engine,"language":row["language"] as? String ?? "yue","report":URL(fileURLWithPath:folder).appendingPathComponent("report.json").path]}) where !tracks.contains(where:{$0["engine"] as? String==track["engine"] as? String && $0["language"] as? String==track["language"] as? String}) {tracks.append(track)}
        for track in report["tracks"] as? [[String:Any]] ?? [] where !tracks.contains(where:{$0["engine"] as? String==track["engine"] as? String && $0["language"] as? String==track["language"] as? String}) {tracks.append(track)}
        let children=(try? FileManager.default.contentsOfDirectory(at:root.appendingPathComponent("tracks"),includingPropertiesForKeys:[.contentModificationDateKey])) ?? []
        for folder in children.sorted(by:{ ((try? $0.resourceValues(forKeys:[.contentModificationDateKey]).contentModificationDate) ?? .distantPast) > ((try? $1.resourceValues(forKeys:[.contentModificationDateKey]).contentModificationDate) ?? .distantPast) }) {
            let settings=json(folder.appendingPathComponent("review.json"))["config"] as? [String:Any] ?? [:]
            guard let engine=settings["ttsBackend"] as? String else{continue}
            let language=settings["targetLanguage"] as? String ?? "yue"
            if !tracks.contains(where:{$0["engine"] as? String==engine && ($0["language"] as? String ?? "yue")==language}) {tracks.append(["engine":engine,"language":language,"report":folder.appendingPathComponent("report.json").path])}
        }
        let rootPreview=json(root.appendingPathComponent("audio-preview.json"))
        if let engine=rootPreview["engine"] as? String,let language=rootPreview["language"] as? String,!tracks.contains(where:{$0["engine"] as? String==engine && $0["language"] as? String==language}) {
            tracks.append(["engine":engine,"language":language,"report":root.appendingPathComponent("report.json").path])
        }
        func timelineSegmentID(_ row:[String:Any])->String? {
            if let id=row["editorID"] as? String {return id}
            return document?.segments.first {abs($0.start-(row["start"] as? Double ?? -1))<0.001 && abs($0.end-(row["end"] as? Double ?? -1))<0.001}?.id
        }
        for track in tracks {
            guard let engine=track["engine"] as? String,let path=track["report"] as? String else{continue}
            let folder=URL(fileURLWithPath:path).deletingLastPathComponent(),key=engine+":"+(track["language"] as? String ?? "yue")
            evidenceFolders[key]=folder
            recordedModelVersions[key]=(json(folder.appendingPathComponent("review.json"))["config"] as? [String:Any])?["gsvVersion"] as? String ?? "v2"
            if track["language"] as? String=="en",!dirty,document != nil {
                let cues=json(folder.appendingPathComponent("review.json"))["cues"] as? [[String:Any]] ?? []
                for i in document!.segments.indices where (document!.segments[i].english ?? "").isEmpty {
                    let segment=document!.segments[i]
                    if let cue=cues.first(where:{abs(($0["start"] as? Double ?? -1)-segment.start)<0.001 && abs(($0["end"] as? Double ?? -1)-segment.end)<0.001}),let text=cue["english"] as? String {document!.segments[i].english=text}
                }
            }
            let rows=(try? Data(contentsOf:folder.appendingPathComponent("timing.json"))).flatMap {try? JSONSerialization.jsonObject(with:$0) as? [[String:Any]]} ?? []
            timingRows[key]=rows;fallbackRows[key]=json(folder.appendingPathComponent("report.json"))["audioFallbacks"] as? [[String:Any]] ?? []
            trackIssueRows[key]=(try? Data(contentsOf:folder.appendingPathComponent("segment-issues.json"))).flatMap {try? JSONSerialization.jsonObject(with:$0) as? [[String:Any]]} ?? []
            previewRows[key]=json(folder.appendingPathComponent("audio-preview.json"))["rows"] as? [[String:Any]] ?? []
            if rows.isEmpty,engine.hasPrefix("gpt-sovits") {
                let snapshot=json(folder.appendingPathComponent("review.json"))
                let savedCues=snapshot["cues"] as? [[String:Any]] ?? []
                previewRows[key,default:[]]+=AudioTakeIndex.recovered(folder:folder,engine:engine,cues:savedCues,profiles:profiles)
            }
            timelineAudioRegions[key]=rows.compactMap {row in
                guard row["skipped"] as? Bool != true,let path=row["renderedAudio"] as? String ?? row["audio"] as? String,ProcessingAudioIndex.length(path) != nil,let start=row["renderedStart"] as? Double ?? row["start"] as? Double,let end=row["renderedEnd"] as? Double ?? row["end"] as? Double,end>start else{return nil}
                return TimelineAudioRegion(start:start,end:end,warning:row["needsReview"] as? Bool ?? false,speakerId:row["speakerId"] as? String,segmentID:timelineSegmentID(row))
            }
            if rows.isEmpty {timelineAudioRegions[key]=(previewRows[key] ?? []).compactMap {row in
                guard let path=row["audio"] as? String,ProcessingAudioIndex.length(path) != nil,let start=row["start"] as? Double,let end=row["end"] as? Double else{return nil}
                return TimelineAudioRegion(start:start,end:end,warning:true,speakerId:row["speakerId"] as? String,segmentID:timelineSegmentID(row))
            }}
            for row in fallbackRows[key] ?? [] {
                if let start=row["renderedStart"] as? Double,let end=row["renderedEnd"] as? Double {timelineAudioRegions[key,default:[]].append(TimelineAudioRegion(start:start,end:end,warning:true,speakerId:row["speakerId"] as? String,segmentID:timelineSegmentID(row)))}
            }
            let state=progress.first(where:{$0["folder"] as? String==folder.path})?["state"] as? String
            timelineAudioStates[key]=state ?? (FileManager.default.fileExists(atPath:path) ? "complete":"preparing")
            var quality=json(folder.appendingPathComponent("validation.json"));if !quality.isEmpty {quality["engine"]=engine;quality["language"]=track["language"];qualitySnapshot.append(quality)}
        }
        for root in evidenceRoots {
            for track in json(root.appendingPathComponent("dialogue-delivery-audit.json"))["tracks"] as? [[String:Any]] ?? [] {
                guard let engine=track["engine"] as? String,let language=track["language"] as? String else{continue}
                let key=engine+":"+language
                for proof in track["rows"] as? [[String:Any]] ?? [] where proof["available"] as? Bool==false {
                    guard let logs=proof["logs"] as? [String:String],let path=logs["timing"],URL(fileURLWithPath:path).deletingLastPathComponent()==evidenceFolders[key] else{continue}
                    var issue=proof
                    issue["status"]="skipped";issue["kind"]="delivery-missing"
                    let messages=proof["messages"] as? [String] ?? []
                    issue["message"]=messages.isEmpty ? L("錄音缺失或無有效聲音；請查看生成紀錄。"):messages.joined(separator:" · ")
                    trackIssueRows[key,default:[]].append(issue)
                }
            }
        }
        mergePreviewTimelineRegions()
        for issue in channelGenerationIssues {
            guard let engine=issue["engine"] as? String,let language=issue["language"] as? String,let start=issue["start"] as? Double,let end=issue["end"] as? Double else{continue}
            let key=engine+":"+language,id=timelineSegmentID(issue)
            if (timelineAudioRegions[key] ?? []).contains(where: {($0.segmentID != nil && $0.segmentID==id) || (abs($0.start-start)<0.001 && abs($0.end-end)<0.001)}) {continue}
            timelineMissingRegions[key,default:[]].append(TimelineMissingRegion(start:start,end:end,segmentID:id,reason:issue["message"] as? String ?? ""))
        }
    }
    static func audioLength(_ path:String)->Double? {
        guard let file=try? AVAudioFile(forReading:URL(fileURLWithPath:path)),file.length>0,file.fileFormat.sampleRate>0 else{return nil}
        return Double(file.length)/file.fileFormat.sampleRate
    }
    private func cachedAudioLength(_ path:String)->Double? {
        guard let attributes=try? FileManager.default.attributesOfItem(atPath:path),let size=attributes[.size] as? UInt64,let modified=attributes[.modificationDate] as? Date else{return nil}
        if let cached=audioHeaders[path],cached.size==size,cached.modified==modified {return cached.length}
        guard let length=Self.audioLength(path) else{return nil}
        if audioHeaders.count>4000 {audioHeaders.removeAll()}
        audioHeaders[path]=(size,modified,length);return length
    }
    func audioStatus(_ key:String)->String {
        let count=timelineAudioRegions[key]?.count ?? 0
        let state=timelineAudioStates[key]
        return L(["running":"生成中","preparing":"準備／生成中","complete":count>0 ? "已生成":"未有可用錄音","failed":"生成失敗","skipped":"已跳過餘下生成"][state ?? ""] ?? (count>0 ? "已生成":"等待生成"))+(count>0 ? " · \(count) "+L("段錄音"):"")
    }
    var availableDubLanguages:[String] {
        let saved=document?.dubLanguages ?? config["dubLanguages"] as? [String] ?? ["yue"]
        return ["yue","en"].filter {language in saved.contains(language) || timelineAudioStates.keys.contains {$0.hasSuffix(":"+language)} || timelineAudioRegions.contains {key,rows in key.hasSuffix(":"+language) && !rows.isEmpty}}
    }
    var availableVoiceEngines:[String] {
        let saved=Array(productionSelections[document?.review ?? ""]?.engines ?? Set(config["selectedEngines"] as? [String] ?? [config["ttsBackend"] as? String ?? "gpt-sovits"]))
        return ["gpt-sovits-v2","gpt-sovits-v3","gpt-sovits","cosyvoice3","voxcpm2","wsyue","drama3","qwen-tts"].filter {engine in
            if ["gpt-sovits-v3","qwen-tts"].contains(engine) {return timelineAudioRegions.contains {key,rows in key.hasPrefix(engine+":") && !rows.isEmpty}}
            return saved.contains(engine) || timelineAudioStates.keys.contains {$0.hasPrefix(engine+":")} || timelineAudioRegions.contains {key,rows in key.hasPrefix(engine+":") && !rows.isEmpty}
        }
    }

    @Published var previewLanguage="yue"
    @Published var cueSearch=""
    @Published var cueFilter="all"
    @Published var timelineZoom=1.0
    @Published var followPlaybackText=true
    @Published var previewVolume=1.0 {didSet {player.volume=Float(previewVolume);audio.volume=Float(previewVolume)}}
    @Published var auditionLabel=""
    @Published var manualNavigation=0
    private var isolatedStopAt:Double?
    private var isolatedStart=0.0
    private var audioObserver:Any?
    @Published var workspacePage="edit"
    @Published var rolePageEditor:ProjectEditor?
    var rolePageStates:[String:RoleManagerState]=[:]
    var rolePageState:RoleManagerState {
        let key=(rolePageEditor ?? self).document?.review ?? selectedRow?.video ?? "preview"
        if let state=rolePageStates[key] {return state}
        let state=RoleManagerState()
        if let review=(rolePageEditor ?? self).document?.review,!(rolePageEditor ?? self).readOnlyPreview {state.configureDraft(URL(fileURLWithPath:review).deletingLastPathComponent().appendingPathComponent("pending-role-changes.json"))}
        rolePageStates[key]=state;return state
    }
    var pendingEnglishScript:(version:String,review:String,segment:String)?
    var pendingVoiceComparison:(version:String,review:String,segment:String)?
    var pendingAudition:(version:String,review:String,segment:String,engine:String,language:String)?
    @Published var previewEngine="cosyvoice3"
    @Published var filter = "全部"
    @Published var error: String?
    @Published var dirty = false
    @Published var seconds = 0.0
    @Published var playingVersion: String?
    @Published var splitText = ""
    @Published var splitAt = 0
    @Published var splitCaptionAt = 1
    @Published var looping = false
    @Published var outputDuration = 1.0
    @Published var aspect = 16.0/9.0
    @Published var clipSelection: String?
    @Published var profiles: [VoiceProfile] = [] {didSet {invalidateTakes()}}
    @Published var selectedSegments: Set<String> = []
    @Published var suggestion: String?
    @Published var waveforms: [String:[Float]] = [:]
    @Published var sourceGaps: [[String:Double]] = []
    var suggestionTarget: (review:String,segment:String,text:String,language:String)?
    @Published var undoStack: [EditDocument] = []
    @Published var redoStack: [EditDocument] = []
    let player = CantoPlayer()
    let audio = AVPlayer()
    var config: [String:Any] = [:]
    var duration = 1.0
    var offset = 0.0
    var stopAt: Double?
    var loopStart: Double?
    private var observer: Any?
    private var saving: DispatchWorkItem?
    private var root: URL?
    private var applying = false
    var segmentIndex: Int? { document?.segments.firstIndex { $0.id == selectedSegment } }
    var selectedRow: ProjectRow? { projects.first { $0.id == selected } }
    var draftURL: URL? { document.map { URL(fileURLWithPath:$0.review).deletingLastPathComponent().appendingPathComponent("editor-draft.json") } }
    var captions: [PreviewCaption] {
        guard playingVersion == nil else { return [] }
        return (document?.segments ?? []).filter(\.enabled).map { PreviewCaption(start:$0.captionStart+offset,end:$0.captionEnd+offset,text:$0.captionText.isEmpty ? $0.text : $0.captionText) }
    }
    func configure(root: URL) {
        self.root = root
        guard observer == nil else { return }
        audioObserver=audio.addPeriodicTimeObserver(forInterval:CMTime(seconds:0.05,preferredTimescale:600),queue:.main) {[weak self] time in Task {@MainActor in
            guard let self,let end=self.isolatedStopAt,time.seconds>=end else{return}
            if self.looping {self.audio.seek(to:CMTime(seconds:self.isolatedStart,preferredTimescale:600));self.audio.play()}
            else {self.audio.pause();self.isolatedStopAt=nil}
        }}
        observer = player.addPeriodicTimeObserver(forInterval:CMTime(seconds:0.1,preferredTimescale:600),queue:.main) { [weak self] time in
            Task { @MainActor in
                guard let self else { return }
                self.seconds = max(0,time.seconds - (self.playingVersion == nil ? self.offset : 0))
                if let end=self.stopAt, self.seconds>=end {
                    if self.looping, let start=self.loopStart { self.seek(start); self.player.play() }
                    else { self.player.pause(); self.stopAt=nil }
                }
            }
        }
    }
    func refresh(_ model: AppModel) {
        configure(root:model.engine.root)
        model.reconcileBatchProjects()
        var rows = model.savedDrafts.map { draft -> ProjectRow in
            let obj=(try? JSONSerialization.jsonObject(with:Data(contentsOf:draft.url))) as? [String:Any] ?? [:]
            let cfg=obj["config"] as? [String:Any] ?? [:]
            let queued=model.editorTasks.last { $0.review==draft.url.path && ["queued","running","failed"].contains($0.status) }
            let versionFolders=(try? FileManager.default.contentsOfDirectory(at:draft.url.deletingLastPathComponent().appendingPathComponent("versions"),includingPropertiesForKeys:nil)) ?? []
            let hasCompleted=versionFolders.contains {p in
                guard let data=try? Data(contentsOf:p.appendingPathComponent("version.json")),let v=try? JSONSerialization.jsonObject(with:data) as? [String:Any] else{return false}
                return v["status"] as? String=="complete"
            }
            let exportReport=(try? JSONSerialization.jsonObject(with:Data(contentsOf:draft.url.deletingLastPathComponent().appendingPathComponent("report.json")))) as? [String:Any] ?? [:]
            let exported=(exportReport["exportedOutput"] as? String ?? exportReport["output"] as? String).map {FileManager.default.fileExists(atPath:$0)} ?? false
            let status=queued.map { ["queued":"排隊生成","running":"生成中","failed":"需修正"][$0.status] ?? $0.status } ?? ((obj["status"] as? String)=="partial" ? (exported ? "已輸出，待覆核":"需修正") : ((obj["status"] as? String)=="complete" || hasCompleted ? "已完成" : "待批核"))
            return ProjectRow(id:model.batchItems.first(where:{$0.review==draft.url.path})?.id ?? draft.url.path,video:cfg["video"] as? String ?? "",review:draft.url,status:status)
        }
        for item in model.batchItems where !rows.contains(where: { item.review != nil && $0.review?.path==item.review }) {
            rows.append(ProjectRow(id:item.id,video:item.video,review:item.review.map {URL(fileURLWithPath:$0)},status:item.status,previewJob:SavedWorkspace.folder(root:model.engine.root,video:item.video,preferred:item.previewJob)))
        }
        projects=rows
        if let selected, let row=rows.first(where:{$0.id==selected}), row.review != nil, document == nil { open(row) }
        loadVersions();importAuditionEnglish()
        if let pending=pendingAudition,document?.review==pending.review,selectedSegment==pending.segment,versions.contains(where:{$0.id==pending.version && $0.status=="preview"}) {
            previewEngine=pending.engine;previewLanguage=pending.language
            if pending.language=="en",let i=segmentIndex,(document?.segments[i].english ?? "").isEmpty,
               let version=versions.first(where:{$0.id==pending.version}),let data=try? Data(contentsOf:version.folder.appendingPathComponent("review.json")),let obj=try? JSONSerialization.jsonObject(with:data) as? [String:Any],let cue=(obj["cues"] as? [[String:Any]])?.first,let text=cue["english"] as? String,!text.isEmpty {updateSegment {$0.english=text}}
            pendingAudition=nil;playEngine(pending.engine,native:true)
        }
        if let pending=pendingEnglishScript,let version=versions.first(where:{$0.id==pending.version && $0.status=="preview-script"}) {
            if document?.review==pending.review,let i=document?.segments.firstIndex(where:{$0.id==pending.segment}),(document?.segments[i].english ?? "").trimmingCharacters(in:.whitespacesAndNewlines).isEmpty,let data=try? Data(contentsOf:version.folder.appendingPathComponent("review.json")),let object=try? JSONSerialization.jsonObject(with:data) as? [String:Any],let text=(object["cues"] as? [[String:Any]])?.first?["english"] as? String,!text.isEmpty {update {$0.segments[i].english=text};try? save()}
            pendingEnglishScript=nil
        }
        if let pending=pendingVoiceComparison,document?.review==pending.review,let version=versions.first(where:{$0.id==pending.version && $0.status=="voice-samples"}) {model.workspaceOptions.voiceSampleVersion=version;pendingVoiceComparison=nil}
        for i in projects.indices where projects[i].id==selected && versions.contains(where:{$0.status=="complete"}) && !["生成中","排隊生成","需修正"].contains(projects[i].status) {projects[i].status="已完成"}
    }
    func open(_ row: ProjectRow) {
        do { try save() } catch { self.error=error.localizedDescription;return }
        player.pause();audio.pause();selected=row.id;selectedSegment=nil;selectedSegments=[];suggestion=nil;undoStack=[];redoStack=[];playingVersion=nil;stopAt=nil
        guard let review=row.review else {
            document=nil;versions=[];config=[:];waveforms=[:];sourceGaps=[]
            sourceCaptions=[];profiles=[]
            dirty=false;duration=1;outputDuration=1;offset=0;seconds=0;error=nil;refreshEvidence();return
        }
        do {
            guard let obj=try JSONSerialization.jsonObject(with:Data(contentsOf:review)) as? [String:Any],obj["config"] is [String:Any],obj["cues"] is [[String:Any]] else {throw AppFailure(message:"校稿檔案格式無效。") }
            let base=review.deletingLastPathComponent().appendingPathComponent("editor-base.json")
            if !FileManager.default.fileExists(atPath:base.path) {try JSONSerialization.data(withJSONObject:obj,options:.prettyPrinted).write(to:base,options:.atomic)}
            config=obj["config"] as? [String:Any] ?? [:]
            if let selection=WorkspaceVoiceSelection(config) {previewEngine=selection.primary;previewLanguage=selection.languages.first ?? "yue"}
            sourceCaptions=SavedWorkspace.captions(folder:review.deletingLastPathComponent())
            sourceGaps=[]
            if let data=try? Data(contentsOf:review.deletingLastPathComponent().appendingPathComponent("source-coverage.json")),let coverage=try? JSONSerialization.jsonObject(with:data) as? [String:Any] {sourceGaps=coverage["uncovered"] as? [[String:Double]] ?? []}
            if let meta=obj["meta"] as? [String:Any],let streams=meta["streams"] as? [[String:Any]],let video=streams.first(where:{$0["codec_type"] as? String=="video"}),let w=video["width"] as? Double,let h=video["height"] as? Double,h>0 {aspect=w/h}
            duration=config["duration"] as? Double ?? 1;offset=config["startOffset"] as? Double ?? 0
            guard duration.isFinite,duration>0,offset.isFinite,offset>=0 else {throw AppFailure(message:"工作時間無效。") }
            if let p=config["voiceProfiles"] { profiles=(try? JSONDecoder().decode([VoiceProfile].self,from:JSONSerialization.data(withJSONObject:p))) ?? [] }
            let draft=review.deletingLastPathComponent().appendingPathComponent("editor-draft.json")
            let database=root.flatMap {try? ProjectDatabase(root:$0)}
            if let data=try database?.data(draft) ?? (try? Data(contentsOf:draft)) {
                document=try JSONDecoder().decode(EditDocument.self,from:data)
            } else {
                let cues=obj["cues"] as? [[String:Any]] ?? []
                let segments=cues.enumerated().map { i,c in EditSegment(sources:[i],start:c["start"] as? Double ?? 0,end:c["end"] as? Double ?? 1,captionStart:c["subtitleStart"] as? Double ?? c["start"] as? Double ?? 0,captionEnd:c["subtitleEnd"] as? Double ?? c["end"] as? Double ?? 1,text:c["cantonese"] as? String ?? "",original:c["text"] as? String ?? "",speakerId:c["speakerId"] as? String ?? config["defaultSpeaker"] as? String ?? "",enabled:c["enabled"] as? Bool ?? true,english:c["english"] as? String,sourceNote:c["reviewNote"] as? String,preserveOriginalSpeech:c["preserveOriginalSpeech"] as? Bool) }
                document=EditDocument(review:review.path,segments:segments,clips:[EditClip(start:0,end:duration)],backgroundGain:config["backgroundGain"] as? Double ?? 0.8,dubLanguages:config["dubLanguages"] as? [String] ?? ["yue"],cantonesePronunciationText:config["cantonesePronunciationText"] as? String)
            }
            if let data=try? Data(contentsOf:review.deletingLastPathComponent().appendingPathComponent("editor-voices.json")),let saved=try? JSONDecoder().decode([VoiceProfile].self,from:data) {profiles=saved}
            dirty=document?.pendingChanges ?? true;selectedSegment=document?.segments.first?.id;loadVersions();loadWaveforms();playSource();seek(document?.playhead ?? 0);error=nil
            if !readOnlyPreview,document?.voiceStyleDefaultRevision != 3 {update {$0.voiceStyleMode="clone";$0.voiceStyleDefaultRevision=3};try save()}
        } catch { document=nil;self.error="載入編輯資料失敗：\(error.localizedDescription)" }
    }
    /// Inspector choices belong to the loaded project; production defaults are
    /// for newly imported videos. Never overwrite a draft simply by opening it.
    var outputDubMode:String? {
        guard let document else {return nil}
        let languages=document.dubLanguages ?? config["dubLanguages"] as? [String] ?? ["yue"]
        return languages.contains("yue") && languages.contains("en") ? "both":languages.first ?? "yue"
    }
    var outputSubtitleModes:Set<String> {
        if let modes=document?.subtitleModes ?? config["subtitleModes"] as? [String] {return Set(modes)}
        switch document?.subtitleOutput ?? config["subtitleOutput"] as? String ?? "yue" {
        case "none":return []
        case "separate","all","dual":return ["yue","english"]
        case "complete":return ["yue","english","original"]
        case "english":return ["english"]
        case "original":return ["original"]
        default:return ["yue"]
        }
    }
    func setOutputSubtitle(_ key:String,_ value:Bool) {
        var modes=outputSubtitleModes
        if value {modes.insert(key)} else {modes.remove(key)}
        update {$0.subtitleModes=["original","yue","english"].filter {modes.contains($0)}}
    }
    func setOutputDubMode(_ mode:String) {
        guard ["yue","en","both"].contains(mode) else {return}
        update {$0.dubLanguages=mode=="both" ? ["yue","en"]:[mode]}
    }
    func update(recordUndo:Bool=true,_ mutate: (inout EditDocument)->Void) {
        guard !readOnlyPreview else{return}
        guard var next=document else { return }
        let previous=next;mutate(&next)
        for i in next.segments.indices where next.segments[i].audioTake==nil {next.segments[i].audioAcceptedHistoryID=nil}
        guard previous != next else { return }
        if recordUndo {undoStack.append(previous);if undoStack.count>100 {undoStack.removeFirst()}};redoStack=[]
        document=next;dirty=true;scheduleSave()
    }
    func updateSegment(recordUndo:Bool=true,_ mutate: (inout EditSegment)->Void) { guard let i=segmentIndex else{return}; update(recordUndo:recordUndo) { mutate(&$0.segments[i]) } }
    func assignRole(_ target:String,from source:String,segment:String?=nil) {
        guard profiles.contains(where:{$0.id==target}),target != source else{return}
        update {document in
            for i in document.segments.indices where document.segments[i].speakerId==source && (segment==nil || document.segments[i].id==segment) {
                document.segments[i].speakerId=target;document.segments[i].audioTake=nil
                document.segments[i].preserveOriginalSpeech=false
            }
        }
    }
    func undo() {guard let d=undoStack.popLast(),let current=document else{return};redoStack.append(current);document=d;dirty=true;scheduleSave()}
    func redo() {guard let d=redoStack.popLast(),let current=document else{return};undoStack.append(current);document=d;dirty=true;scheduleSave()}
    func scheduleSave() {
        guard !readOnlyPreview else{return}
        saving?.cancel()
        let work=DispatchWorkItem { [weak self] in Task { @MainActor in do {try self?.save()} catch {self?.error=error.localizedDescription} } }
        saving=work;DispatchQueue.main.asyncAfter(deadline:.now()+0.6,execute:work)
    }
    func save() throws {
        guard !readOnlyPreview else{return}
        saving?.cancel()
        guard var document,let url=draftURL else{return}
        if playingVersion==nil {document.playhead=seconds}
        document.pendingChanges=dirty
        let bytes=try JSONEncoder().encode(document)
        if let root {try ProjectDatabase(root:root).put(url,project:document.review,kind:"editor-draft.json",data:bytes)}
        try bytes.write(to:url,options:.atomic)
        self.document=document
        try JSONEncoder().encode(profiles).write(to:url.deletingLastPathComponent().appendingPathComponent("editor-voices.json"),options:.atomic)
    }
    func followPlaybackCue(at time:Double) {
        guard followPlaybackText,playingVersion==nil,let document else{return}
        let active=document.segments.first {$0.enabled && $0.captionStart<=time && time<$0.captionEnd} ?? document.segments.first {$0.enabled && $0.start<=time && time<$0.end}
        if selectedSegment != active?.id {selectedSegment=active?.id}
    }
    func selectSegment(_ id:String,reveal:Bool=true) {
        guard let segment=document?.segments.first(where:{$0.id==id}) else{return}
        player.pause();audio.pause();isolatedStopAt=nil;stopAt=nil;selectedSegment=id
        if playingVersion != nil {playSource()}
        seek(segment.start);if reveal {manualNavigation += 1}
    }
    var dialoguePath:String? {
        guard let path=config["dialoguePath"] as? String,FileManager.default.fileExists(atPath:path) else{return nil}
        return path
    }
    func playDialogue(context:Bool=false) {
        guard let i=segmentIndex,let s=document?.segments[i],let path=dialoguePath else{error=L("分離對白未準備好，請先完成背景分離。");return}
        selectSegment(s.id);player.isMuted=true;player.pause();stopAt=nil
        audio.replaceCurrentItem(with:AVPlayerItem(url:URL(fileURLWithPath:path)))
        isolatedStart=context ? max(0,s.start-0.5):s.start;isolatedStopAt=nil
        let end=context ? min(duration,s.end+0.75):s.end
        audio.seek(to:CMTime(seconds:isolatedStart,preferredTimescale:600),toleranceBefore:.zero,toleranceAfter:.zero) { [weak self] finished in Task { @MainActor in
            guard finished,let self,self.selectedSegment==s.id else{return}
            self.isolatedStopAt=end;self.audio.play()
        }}
        auditionLabel=L("分離對白")
    }
    func playSource() {
        isolatedStopAt=nil
        guard let document else{return}
        let path=document.videoOverride ?? config["video"] as? String ?? ""
        guard FileManager.default.fileExists(atPath:path) else{error="原片遺失，請重新連結原片。";return}
        audio.pause();player.isMuted=false;playingVersion=nil;outputDuration=duration;player.replaceCurrentItem(with:AVPlayerItem(url:URL(fileURLWithPath:path)));player.subtitles(ordinal:nil,external:nil);seek(document.playhead)
    }
    func seek(_ local:Double) {player.seek(to:CMTime(seconds:max(0,local)+(playingVersion==nil ? offset:0),preferredTimescale:600));seconds=local}
    func playSegment(context:Bool=false) {
        guard let i=segmentIndex,let s=document?.segments[i] else{return}
        selectSegment(s.id);audio.pause();auditionLabel=L("原片音軌");player.isMuted=false
        if playingVersion != nil {playSource()}
        let start=context ? max(0,s.start-0.5):s.start
        loopStart=start;stopAt=context ? min(duration,s.end+0.75):s.end;seek(start);player.play()
    }
    func relink() {
        let panel=NSOpenPanel();panel.allowedContentTypes=[.movie,UTType(filenameExtension:"mkv")!]
        if panel.runModal() == .OK,let url=panel.url {update {$0.videoOverride=url.path};playSource()}
    }
    func splitSegment(reuseAudio: Bool = false) {
        guard playingVersion==nil else {error="請先切返原片，再揀分割位置。";return}
        guard let i=segmentIndex,let s=document?.segments[i] else{return}
        let characters=Array(s.text)
        guard seconds>s.start && seconds<s.end && splitAt>0 && splitAt<characters.count else {error="請將播放頭放喺句子內，並選擇文字分割位置。";return}
        let boundary=seconds
        let captionCharacters=Array(s.captionText)
        if !captionCharacters.isEmpty && !(splitCaptionAt>0 && splitCaptionAt<captionCharacters.count) {error="請選擇顯示字幕嘅文字分界。";return}
        if reuseAudio,let length=s.audioLength {
            let cut=s.trimStart+(boundary-s.start)*s.rate
            guard cut>s.trimStart && cut<length-s.trimEnd else {error="聲音分割位置超出已選 take。";return}
        }
        if reuseAudio && s.audioTake == nil {error="請先從試音版本選擇一個 take，再分割音訊。";return}
        update { d in
            var left=s,right=s;right.id=UUID().uuidString
            left.end=boundary;left.captionEnd=boundary;right.start=boundary;right.captionStart=boundary
            left.text=String(characters[..<splitAt]);right.text=String(characters[splitAt...]);left.captionText=captionCharacters.isEmpty ? "":String(captionCharacters[..<splitCaptionAt]);right.captionText=captionCharacters.isEmpty ? "":String(captionCharacters[splitCaptionAt...])
            if reuseAudio,let length=s.audioLength {
                let cut=s.trimStart+(boundary-s.start)*s.rate
                left.trimEnd=max(0,length-cut);right.trimStart=cut
            } else {
                left.audioTake=nil;right.audioTake=nil
                left.trimStart=0;left.trimEnd=0;right.trimStart=0;right.trimEnd=0
            }
            left.english=nil;right.english=nil
            d.segments.replaceSubrange(i...i,with:[left,right])
        }
    }
    func mergeNext() {
        guard let i=segmentIndex,let d=document,i+1<d.segments.count else{return}
        update { d in
            let next=d.segments[i+1]
            d.segments[i].end=next.end;d.segments[i].captionEnd=next.captionEnd
            d.segments[i].sources=Array(Set(d.segments[i].sources+next.sources)).sorted()
            if !d.segments[i].captionText.isEmpty || !next.captionText.isEmpty {d.segments[i].captionText=(d.segments[i].captionText.isEmpty ? d.segments[i].text:d.segments[i].captionText)+(next.captionText.isEmpty ? next.text:next.captionText)}
            d.segments[i].english=[d.segments[i].english,next.english].compactMap{$0}.joined(separator:" ")
            d.segments[i].text+=next.text;if d.segments[i].original != next.original {d.segments[i].original+=" / "+next.original}
            d.segments[i].audioTake=nil;d.segments[i].trimStart=0;d.segments[i].trimEnd=0;d.segments.remove(at:i+1)
        }
    }
    func bladeClip() {
        guard playingVersion==nil else {error="請先切返原片，再揀分割位置。";return}
        guard let i=document?.clips.firstIndex(where:{$0.enabled && $0.start<seconds && seconds<$0.end}) else {error="播放頭必須喺影片片段內。";return}
        update {d in var next=d.clips[i];next.id=UUID().uuidString;next.start=seconds;d.clips[i].end=seconds;d.clips.insert(next,at:i+1)}
    }
    func loadVersions() {
        cueVoiceCache.removeAll();cueVoiceMisses.removeAll()
        refreshEvidence()
        guard let document else {versions=[];return}
        let folder=URL(fileURLWithPath:document.review).deletingLastPathComponent()
        let paths=(try? FileManager.default.contentsOfDirectory(at:folder.appendingPathComponent("versions"),includingPropertiesForKeys:nil)) ?? []
        versions=paths.compactMap { p in
            guard let data=try? Data(contentsOf:p.appendingPathComponent("version.json")),let o=try? JSONSerialization.jsonObject(with:data) as? [String:Any] else{return nil}
            return EditVersion(id:o["id"] as? String ?? p.lastPathComponent,status:o["status"] as? String ?? "unknown",output:(o["output"] as? String).map {URL(fileURLWithPath:$0)},report:(o["report"] as? String).map {URL(fileURLWithPath:$0)},folder:p,created:o["created"] as? String ?? "")
        }.sorted {$0.created>$1.created}
        for i in versions.indices {
            if let bytes=try? Data(contentsOf:versions[i].folder.appendingPathComponent("processing-time.json")),let time=try? JSONSerialization.jsonObject(with:bytes) as? [String:Any] {versions[i].processingSeconds=time["seconds"] as? Double ?? 0}
        }
        if let root,let db=try? ProjectDatabase(root:root) {versions=versions.filter {v in guard let output=v.output else{return true};return FileManager.default.fileExists(atPath:output.path) && ((try? db.isRemoved(output)) != true)}}
        if let data=try? Data(contentsOf:folder.appendingPathComponent("report.json")),let obj=try? JSONSerialization.jsonObject(with:data) as? [String:Any],let output=obj["exportedOutput"] as? String ?? obj["output"] as? String {
            versions.append(EditVersion(id:"original",status:(obj["failedEngines"] as? [String:String] ?? [:]).isEmpty && (obj["segmentIssues"] as? [Any] ?? []).isEmpty ? "complete":"partial",output:URL(fileURLWithPath:output),report:folder.appendingPathComponent("report.json"),folder:folder,created:"原始成品"))
            if let root,let db=try? ProjectDatabase(root:root),((try? db.isRemoved(URL(fileURLWithPath:output)))==true || !FileManager.default.fileExists(atPath:output)) {versions.removeAll {$0.id=="original"}}
        }
    }
    /// Repair the latest rendered snapshot, rather than the original import
    /// whose roles, engine selection and AI settings can predate that result.
    var repairReview:URL? {
        guard let base=selectedRow?.review else{return nil}
        for version in versions where ["partial","complete","failed"].contains(version.status) {
            let review=version.folder.appendingPathComponent("review.json")
            guard (FileManager.default.fileExists(atPath:version.folder.appendingPathComponent("report.json").path) || (version.status=="failed" && FileManager.default.fileExists(atPath:version.folder.appendingPathComponent("dialogue-delivery-audit.json").path))),
                  let data=try? Data(contentsOf:review),let row=try? JSONSerialization.jsonObject(with:data) as? [String:Any],
                  let settings=row["config"] as? [String:Any],settings["video"] as? String==config["video"] as? String else{continue}
            return review
        }
        return base
    }
    func play(_ version:EditVersion) {
        guard let url=version.output,FileManager.default.fileExists(atPath:url.path) else {error="成品已移走。";return}
        audio.pause();playingVersion=version.id;stopAt=nil;
        if let report=version.report,let data=try? Data(contentsOf:report),let obj=try? JSONSerialization.jsonObject(with:data) as? [String:Any] {outputDuration=obj["duration"] as? Double ?? duration}
        player.replaceCurrentItem(with:AVPlayerItem(url:url));player.subtitles(ordinal:0,external:nil);player.play()
    }
    func audition(_ version:EditVersion, use:Bool=false) {
        guard let i=segmentIndex,let document else{return}
        let timings=version.folder.appendingPathComponent("timing.json")
        guard let data=try? Data(contentsOf:timings),let rows=try? JSONSerialization.jsonObject(with:data) as? [[String:Any]] else{error="呢個版本未有逐句試音。";return}
        let s=document.segments[i]
        guard let row=rows.first(where:{abs(($0["start"] as? Double ?? -1)-s.start)<0.001 && abs(($0["end"] as? Double ?? -1)-s.end)<0.001}),let path=row["renderedAudio"] as? String ?? row["audio"] as? String else {error="呢段時間已修改，請生成新試音。";return}
        if use {updateSegment {$0.audioTake=path;$0.audioLength=row["renderedSeconds"] as? Double ?? row["seconds"] as? Double;$0.rate=1;$0.trimStart=0;$0.trimEnd=0}}
        if version.output != nil {
            play(version)
            var start=s.start,end=s.end
            if version.status=="preview" {start=0;end=outputDuration}
            else if let report=version.report,let data=try? Data(contentsOf:report),let obj=try? JSONSerialization.jsonObject(with:data) as? [String:Any],let spans=obj["editSpans"] as? [[String:Any]] {
                guard let span=spans.first(where:{($0["blank"] as? Bool != true) && ($0["start"] as? Double ?? 0)<=s.start && ($0["end"] as? Double ?? 0)>s.start}) else {error="呢段已喺該成品剪走。";player.pause();return}
                let sourceStart=span["start"] as? Double ?? 0,outputStart=span["outputStart"] as? Double ?? 0
                start=outputStart+s.start-sourceStart;end=outputStart+min(s.end,span["end"] as? Double ?? s.end)-sourceStart
            }
            loopStart=start;stopAt=end;seek(start);player.play()
        } else {player.pause();audio.replaceCurrentItem(with:AVPlayerItem(url:URL(fileURLWithPath:path)));audio.play()}
    }
    func trashVersion(_ version:EditVersion) {
        guard let output=version.output else{return}
        do {if playingVersion==version.id{player.pause()};try FileManager.default.trashItem(at:output,resultingItemURL:nil);if let root {try ProjectDatabase(root:root).removeOutput(output)};loadVersions()} catch {self.error=error.localizedDescription}
    }
}

extension AppModel {
    func saveEditorQueue() {do {try JSONEncoder().encode(editorTasks).write(to:engine.root.appendingPathComponent("editor-queue.json"),options:.atomic)} catch {self.error=error.localizedDescription}}
    func loadEditorQueue() {
        if let data=try? Data(contentsOf:engine.root.appendingPathComponent("editor-queue.json")),let tasks=try? JSONDecoder().decode([EditorialTask].self,from:data) {
            editorTasks=tasks.map {var t=$0;if t.status=="running"{t.status="queued";t.message="工作已暫停；可繼續同一版本。"};return t}
        }
    }
    func repairMissingTracks(currentTrackOnly:Bool=false) {
        guard !busy,let review=projectEditor.repairReview,(!projectEditor.failedTracks.isEmpty || !projectEditor.segmentIssues.isEmpty || !projectEditor.studioIssues.isEmpty) else{return}
        let e=engine
        projectEditor.player.pause()
        var request:[String:Any]=["review":review.path,"lockScript":true]
        if review != projectEditor.selectedRow?.review {request["repairVersion"]=true}
        if currentTrackOnly {request["repairOnly"]=true;request["repairGenerate"]=true;request["repairTrack"]=["engine":projectEditor.previewEngine,"language":projectEditor.previewLanguage]}
        let frozen=request
        task(currentTrackOnly ? "智能補聲此音軌":"自動修復缺少音軌") {try e.worker("render",config:frozen)}
    }
    func submitEditor(previewOnly:Bool=false,preserveProjectEngines:Bool=false,audioSettings:[String:Any]?=nil,startImmediately:Bool=true) {
        let editor=projectEditor
        editor.error=nil
        do {
            try editor.save()
            guard var document=editor.document else{return}
            document.id=UUID().uuidString;document.created=ISO8601DateFormatter().string(from:Date())
            var object=try JSONSerialization.jsonObject(with:JSONEncoder().encode(document)) as! [String:Any]
            let usedRoles=Set(document.segments.filter {$0.enabled && (!previewOnly || $0.id==editor.selectedSegment)}.map(\.speakerId))
            var frozenProfiles=(audioSettings?["subtitlesOnly"] as? Bool == true || audioSettings?["previewScriptOnly"] as? Bool == true) ? []:editor.profiles.filter {usedRoles.contains($0.id)}
            let references=URL(fileURLWithPath:document.review).deletingLastPathComponent().appendingPathComponent("editor-references")
            try FileManager.default.createDirectory(at:references,withIntermediateDirectories:true)
            for i in frozenProfiles.indices {
                if frozenProfiles[i].reference.isEmpty || !FileManager.default.fileExists(atPath:frozenProfiles[i].reference) {
                    if continueOnError {continue}
                    throw AppFailure(message:L("未設定參考聲音"))
                }
                let bytes=try Data(contentsOf:URL(fileURLWithPath:frozenProfiles[i].reference))
                let hash=SHA256.hash(data:bytes).map{String(format:"%02x",$0)}.joined()
                let target=references.appendingPathComponent(hash+".wav")
                if !FileManager.default.fileExists(atPath:target.path) {try bytes.write(to:target,options:.atomic)}
                frozenProfiles[i].reference=target.path
                for (key,own) in frozenProfiles[i].engineReferences ?? [:] where own.enabled {
                    let data=try Data(contentsOf:URL(fileURLWithPath:own.reference));let digest=SHA256.hash(data:data).map{String(format:"%02x",$0)}.joined()
                    let file=references.appendingPathComponent(digest+".wav")
                    if !FileManager.default.fileExists(atPath:file.path) {try data.write(to:file,options:.atomic)}
                    frozenProfiles[i].engineReferences?[key]?.reference=file.path
                }
            }
            var settings:[String:Any]=["voxcpmModel":voxcpmModel,"wsyueModel":wsyueModel,"drama3Model":drama3Model,"voxcpmDevice":voxcpmDevice,"voiceStyleMode":editor.voiceStyleMode,"gsvSampleSteps":voiceRenderMode=="balanced" ? 16:32,"maxNaturalCandidates":0,"allowCrossEngineRepair":allowCrossEngineRepair,"continueOnError":continueOnError,"independentReferences":true,"asrModel":engine.selectedVariant("asr",default:"asr-1.7b-bf16"),"speechModel":engine.selectedVariant("speech",default:"whisper-large-v3"),"referenceSpeechModel":engine.selectedVariant("referenceSpeech",default:"whisper-small"),"dubLanguages":document.dubLanguages ?? editor.config["dubLanguages"] as? [String] ?? ["yue"],"qwenModel":qwenModel,"qwenReferenceMode":qwenReferenceMode,"gsvReferenceMode":gsvReferenceMode,"cosyModel":cosyModel,"selectedEngines":selectedEngines,"defaultAudioEngine":ttsBackend,"backgroundGain":document.backgroundGain,"backgroundDucking":document.backgroundDucking ?? editor.config["backgroundDucking"] as? Bool ?? false,"captionBottom":document.captionBottom,"captionSize":document.captionSize,"voiceProfiles":try JSONSerialization.jsonObject(with:JSONEncoder().encode(frozenProfiles))]
            if preserveProjectEngines,let engines=editor.config["selectedEngines"] as? [String],!engines.isEmpty {
                settings["selectedEngines"]=engines
                settings["defaultAudioEngine"]=editor.config["defaultAudioEngine"] as? String ?? engines[0]
            }
            settings["fallbackToRoleVoice"]=true
            settings["roleAnalysisMode"]=effectiveRoleAnalysisMode
            settings["visualRoleAnalysisEnabled"]=effectiveRoleAnalysisMode=="audiovisual"
            settings["model"]=selectedModel
            settings["aiRepairModel"]=selectedModel
            settings["requireCompleteDubbing"]=true
            settings["cantoneseLocale"]="yue-HK"
            settings["autoSkipOP"]=document.autoSkipOP ?? editor.config["autoSkipOP"] as? Bool ?? autoSkipOP
            settings["translationSource"]=document.translationSource ?? editor.config["translationSource"] as? String ?? translationSource
            settings["translateOPED"]=document.translateOPED ?? editor.config["translateOPED"] as? Bool ?? false
            if let modes=document.subtitleModes {settings["subtitleModes"]=modes;settings["burnOutputCaptions"]=false}
            if let streams=document.originalSubtitleStreams {settings["originalSubtitleStreams"]=streams}
            settings["pronunciationText"]=editor.config["pronunciationText"] as? String ?? pronunciationText
            settings["subtitleOutput"]=document.subtitleOutput ?? editor.config["subtitleOutput"] as? String ?? subtitleOutput
            settings["cantonesePronunciationText"]=document.cantonesePronunciationText ?? editor.config["cantonesePronunciationText"] as? String ?? cantonesePronunciationText
            if let audioSettings {for (key,value) in audioSettings {settings[key]=value}}
            if let path=document.videoOverride {settings["video"]=path}
            object["settings"]=settings
            if previewOnly {object["previewLanguage"]=editor.previewLanguage;object["previewEngine"]=editor.previewEngine}
            if previewOnly,let i=editor.segmentIndex {object["previewSegment"]=document.segments[i].id}
            let folder=URL(fileURLWithPath:document.review).deletingLastPathComponent().appendingPathComponent("submissions")
            try FileManager.default.createDirectory(at:folder,withIntermediateDirectories:true)
            let submission=folder.appendingPathComponent(document.id+".json")
            try JSONSerialization.data(withJSONObject:object,options:[.prettyPrinted,.sortedKeys]).write(to:submission,options:.atomic)
            if !previewOnly && audioSettings==nil {
                for i in editorTasks.indices where editorTasks[i].review==document.review && ["queued","failed"].contains(editorTasks[i].status) {editorTasks[i].status="superseded"}
            }
            if !previewOnly && audioSettings?["reanalyzeRoles"] as? Bool==true {
                // A new whole-film character analysis replaces pending whole-film
                // voice exports for this project, retaining their immutable snapshots.
                for i in editorTasks.indices where editorTasks[i].review==document.review && ["queued","failed"].contains(editorTasks[i].status) {
                    guard let data=try? Data(contentsOf:URL(fileURLWithPath:editorTasks[i].submission)),let old=try? JSONSerialization.jsonObject(with:data) as? [String:Any],old["previewSegment"]==nil,old["previewOnly"] as? Bool != true,let settings=old["settings"] as? [String:Any],settings["audioOnlyRerun"] as? Bool==true,settings["repairTrack"]==nil,settings["voiceSamplesOnly"] as? Bool != true else{continue}
                    editorTasks[i].status="superseded";editorTasks[i].message=L("已由新人物分析匯出取代；舊提交及已生成檔案保留。")
                }
            }
            editorTasks.append(EditorialTask(id:document.id,review:document.review,submission:submission.path))
            saveEditorQueue();if !previewOnly {editor.dirty=false;try editor.save()};editor.refresh(self);if startImmediately {pumpEditorQueue()}
        } catch {editor.error=error.localizedDescription}
    }
    func pumpEditorQueue() {
        guard !busy,!queuePaused,let i=editorTasks.firstIndex(where:{$0.status=="queued"}) else{return}
        let item=editorTasks[i];editorTasks[i].status="running";activeEditorTask=item.id;saveEditorQueue()
        let cfg:[String:Any]=["submission":item.submission,"review":item.review,"ffmpeg":engine.ffmpeg.path,"ffprobe":engine.ffprobe.path,"executable":Bundle.main.executableURL!.path,"port":engine.port]
        let data=try! JSONSerialization.data(withJSONObject:cfg),e=engine
        task("生成已批准版本") {try e.worker("render-project",config:try JSONSerialization.jsonObject(with:data) as! [String:Any])}
    }
}

final class ProjectWorkspaceOptions: ObservableObject {
    @Published var gptTemperature=1.0
    @Published var gptTopP=1.0
    @Published var gptTopK=15
    @Published var gptRepetitionPenalty=1.35
    @Published var cosyTemperature=0.7
    @Published var cosyExpression="neutral"
    var inferenceSettings:[String:Any] {["gptTemperature":gptTemperature,"gptTopP":gptTopP,"gptTopK":gptTopK,"gptRepetitionPenalty":gptRepetitionPenalty,"cosyTemperature":cosyTemperature,"cosyExpression":cosyExpression]}
    @Published var showABComparison=false
    @Published var comparisonEngineA="gpt-sovits"
    @Published var comparisonEngineB="cosyvoice3"
    @Published var comparisonParametersA:[String:Any]?
    @Published var comparisonParametersB:[String:Any]?
    @Published var showProcessingStatus=false
    @Published var subtitleProposal:EditVersion?
    @Published var voiceSampleVersion:EditVersion?
    @Published var inspector="convert"
    @Published var dialogueTab="listen"
    @Published var sourceTranscript="original"
    @Published var browser="projects"
    @Published var showBrowser=true
    @Published var showInspector=true
    @Published var allTracks=true
    @Published var layoutRevision=0
    @Published var browserWidth=240.0
    @Published var inspectorWidth=350.0
    @Published var timelineHeight=0.0
    @Published var transcriptHeight=240.0
    @Published var focusPreview=false
    @Published var showQueue=false
    @Published var exportPanel="versions"
    @Published var speakerTarget=""
    @Published var allRole=false
    @Published var showSplit=false
    @Published var showAdvancedCue=false
    @Published var referenceEngine="qwen-tts"
    @Published var referenceLanguage="yue"
}
struct ProjectWorkspace: View {
    @AppStorage("studioLanguage") private var interfaceLanguage="system"
    @ObservedObject var model: AppModel
    @ObservedObject var editor: ProjectEditor
    var processing=false
    @ObservedObject var options:ProjectWorkspaceOptions
    init(model:AppModel,editor:ProjectEditor,processing:Bool=false) {
        self.model=model;self.editor=editor;self.processing=processing;self.options=model.workspaceOptions;self.livePreview=model.workspacePreview
    }
    @ObservedObject var livePreview:LiveVideoPreview
    @StateObject var transcriptOriginals=MonitorSubtitles()
    @StateObject private var refreshClock=StudioRefreshClock()
    var body: some View {
        professionalWorkspace
        .onAppear {model.refresh();editor.refresh(model);if editor.selected==nil,let url=model.reviewURL,let row=editor.projects.first(where:{$0.review==url}) {editor.open(row)}}
        .onReceive(refreshClock.projects) {_ in if model.busy {editor.refreshEvidence()}}
        .onReceive(refreshClock.projects) {_ in if model.busy {model.refresh();editor.refresh(model)}}
        .onChange(of:model.busy) {_ in model.refresh();editor.refresh(model);livePreview.refresh(model,video:editor.selectedRow?.video)}
        .onChange(of:editor.manualNavigation) {_ in
            livePreview.follow=false;livePreview.player.pause();livePreview.refresh(model,video:editor.selectedRow?.video)
            if let i=editor.segmentIndex,let segment=editor.document?.segments[i] {livePreview.seek(segment.start)}
        }
        .onChange(of:editor.profiles) {_ in editor.dirty=true;editor.scheduleSave()}
        .onDisappear {do {try editor.save()} catch {editor.error=error.localizedDescription};editor.player.pause();editor.audio.pause()}
        .sheet(isPresented:$options.showQueue) {ConversionQueueSheet(model:model,close:{options.showQueue=false})}
        .sheet(isPresented:$options.showAdvancedCue) {
            DetailedDialoguePanel(model:model,editor:editor,close:{options.showAdvancedCue=false})
        }.accessibilityIdentifier("expert-workspace-"+interfaceLanguage)
    }
    var projectList:some View {
        VStack(alignment:.leading,spacing:8) {
            HStack {Text(L("專案")).font(.headline);Spacer();Button {model.showProjectManager=true} label:{Image(systemName:"folder.badge.gearshape")}.help(L("管理專案及成品"))}
            Picker(L("篩選"),selection:$editor.filter) {ForEach(["全部","待處理","待批核","處理中","生成中","已完成","需修正"],id:\.self) {Text(L($0))}}
            ScrollView {LazyVStack(spacing:6) {
                ForEach(editor.projects.filter {editor.filter=="全部" || $0.status==editor.filter}) {row in
                    Button {editor.open(row)} label:{VStack(alignment:.leading,spacing:4) {
                        Text(row.name).lineLimit(2).font(.callout.bold());Text(L(row.status)).font(.caption).foregroundStyle(.secondary)
                    }.frame(maxWidth:.infinity,alignment:.leading).padding(8).background(editor.selected==row.id ? accent.opacity(0.18):Color.secondary.opacity(0.06),in:RoundedRectangle(cornerRadius:8))}.buttonStyle(.plain)
                     .contextMenu {
                        if let review=row.review {Button(L("刪除專案，保留成品"),role:.destructive) {model.manageCleanup(mode:.projects,review:review)}}
                        else {Button(L("移出佇列")) {model.removeBatchItem(id:row.id);editor.refresh(model)}}
                    }
                }
            }}
            Text(L("專案包含字幕、配音及編輯草稿；MP4 喺成品管理。")).font(.caption2).foregroundStyle(.secondary)
        }
    }
    func workspace(_ document:EditDocument,height:Double,width:Double)->some View {
        let mediaHeight=max(150,min(max(175,min(390,height*0.38)),max(150,(width-250-12)/max(0.1,editor.aspect))))
        return VStack(alignment:.leading,spacing:8) {
            HStack {
                Text(editor.selectedRow?.name ?? L("影片編輯")).font(.headline).lineLimit(1)
                if editor.dirty {Text(L("草稿已修改")).font(.caption).foregroundStyle(.orange)}
                Spacer();Button(L("撤銷"),action:editor.undo).disabled(editor.undoStack.isEmpty);Button(L("重做"),action:editor.redo).disabled(editor.redoStack.isEmpty)
                Button(L("儲存")) {do {try editor.save()} catch {editor.error=error.localizedDescription}}
                Button(L(model.busy ? "批准並排隊":"批准並生成")) {model.submitEditor()}.buttonStyle(.borderedProminent)
            }
            HStack(alignment:.top,spacing:12) {
                AspectPlayerFrame(aspect:editor.aspect,maxHeight:mediaHeight,leftAligned:true) {
                    CaptionedPlayer(player:editor.player,captions:editor.captions,seconds:editor.seconds+(editor.playingVersion==nil ? editor.offset:0),bottomFraction:document.captionBottom,sizeFraction:document.captionSize,showsControls:false)
                }.frame(width:mediaHeight*editor.aspect)
                WorkspaceControlPanel(model:model,editor:editor).frame(maxWidth:.infinity)
            }.frame(height:mediaHeight)
            timeline
            Picker(L("工作內容"),selection:$editor.tab) {Text(L("字幕／配音")).tag("edit");Text(L("影片剪接")).tag("cuts");Text(L("角色／混音")).tag("voices");Text(L("成品／版本")).tag("versions");Text(L("處理步驟")).tag("steps")}.pickerStyle(.segmented)
            if editor.tab=="edit" {
                HStack(alignment:.top,spacing:12) {VStack(alignment:.leading,spacing:5) {cueList(document)}.frame(width:250);compactCue(document).frame(maxWidth:.infinity,maxHeight:.infinity,alignment:.topLeading)}.frame(maxHeight:.infinity)
            } else {ScrollView {VStack(alignment:.leading,spacing:10) {if editor.tab=="cuts" {cuts(document)} else if editor.tab=="voices" {voices(document)} else if editor.tab=="versions" {versionList} else {steps}}}}
            if let error=editor.error {Text(error).font(.caption).foregroundStyle(.red)}
        }
    }
    var timeline:some View {
        VStack(spacing:2) {
            HStack {Text(L("時間軸")).font(.caption);Slider(value:$editor.timelineZoom,in:1...12).frame(width:100);Text(String(format:"%.0f×",editor.timelineZoom)).font(.caption);Spacer();Button(L("新增漏配對白")) {editor.addDialogue()}}
            GeometryReader {g in ScrollView(.horizontal) {EditorialTimeline(editor:editor,compact:true).frame(width:max(400,g.size.width)*editor.timelineZoom,height:100)}}.frame(height:102)
        }
    }
    @ViewBuilder func compactCue(_ document:EditDocument)->some View {
        if let i=editor.segmentIndex {
            let segment=document.segments[i]
            VStack(alignment:.leading,spacing:8) {
                HStack {
                    Text(L("對白")+" \(i+1) · "+String(format:"%.2f–%.2f",segment.start,segment.end)).font(.headline)
                    Button {editor.selectSegment(document.segments[i-1].id)} label:{Image(systemName:"chevron.left")}.disabled(i==0)
                    Button {editor.selectSegment(document.segments[i+1].id)} label:{Image(systemName:"chevron.right")}.disabled(i+1>=document.segments.count)
                    Spacer();Toggle(L("啟用"),isOn:Binding(get:{segment.enabled},set:{v in editor.updateSegment {$0.enabled=v}})).toggleStyle(.checkbox)
                    Button(L("進階…")) {options.showAdvancedCue=true}
                }
                HStack(alignment:.top,spacing:10) {
                    VStack(alignment:.leading,spacing:4) {Text(L("日文辨識文字")).font(.caption);TextEditor(text:segmentText(\.original)).font(.callout).frame(maxHeight:.infinity).border(Color.secondary.opacity(0.2))}
                    VStack(alignment:.leading,spacing:4) {
                        Picker(L("配音台詞"),selection:$editor.previewLanguage) {Text(L("廣東話")).tag("yue");Text(L("英文")).tag("en")}.pickerStyle(.segmented)
                        TextEditor(text:editor.previewLanguage=="en" ? Binding(get:{segment.english ?? ""},set:{v in editor.updateSegment {$0.english=v;$0.audioTake=nil}}):segmentText(\.text)).font(.callout).frame(maxHeight:.infinity).border(Color.secondary.opacity(0.2))
                    }
                }.frame(minHeight:65,maxHeight:.infinity)
                HStack {Picker(L("角色"),selection:segmentText(\.speakerId)) {Text(L("未指定")).tag("");ForEach(editor.profiles) {Text(localizedRoleName($0.name)).tag($0.id)}};TextField(L("顯示字幕（留空跟配音台詞）"),text:segmentText(\.captionText)).textFieldStyle(.roundedBorder)}
                if editor.flaggedSegments.contains(segment.id) {Text(L("呢段有覆核警告；可以試聽或打開處理步驟。")).font(.caption2).foregroundStyle(.orange)}
            }.padding(8).background(Color.secondary.opacity(0.04),in:RoundedRectangle(cornerRadius:8))
        } else {Text(L("揀一段對白開始編輯")).foregroundStyle(.secondary)}
    }
    func segmentText(_ key:WritableKeyPath<EditSegment,String>) -> Binding<String> {
        Binding(get:{guard let i=editor.segmentIndex else{return ""};return editor.document?.segments[i][keyPath:key] ?? ""},set:{v in editor.updateSegment {$0[keyPath:key]=v;if key == \EditSegment.text || key == \EditSegment.speakerId {$0.audioTake=nil}}})
    }
    func segmentNumber(_ key:WritableKeyPath<EditSegment,Double>) -> Binding<Double> {
        Binding(get:{guard let i=editor.segmentIndex else{return 0};return editor.document?.segments[i][keyPath:key] ?? 0},set:{v in editor.updateSegment {$0[keyPath:key]=v}})
    }
    func number(_ title:String,_ binding:Binding<Double>) -> some View {
        HStack {Text(title).font(.caption);TextField(title,value:binding,format:.number.precision(.fractionLength(2))).textFieldStyle(.roundedBorder).frame(width:78)}
    }
    @ViewBuilder func editing(_ document:EditDocument) -> some View {
        HStack(alignment:.top,spacing:14) {
            VStack(alignment:.leading,spacing:8) {cueList(document)}.frame(width:290)
            VStack(alignment:.leading,spacing:10) {selectedCue(document)}.frame(maxWidth:.infinity,alignment:.topLeading)
        }
        DisclosureGroup(L("時間軸／字幕位置與配音時段")) {
        HStack {Text(L("時間軸")).font(.caption);Slider(value:$editor.timelineZoom,in:1...12).frame(width:160);Text(String(format:"%.0f×",editor.timelineZoom)).font(.caption);Spacer();Button(L("新增漏配對白")) {editor.addDialogue()}}
        GeometryReader {g in ScrollView(.horizontal) {EditorialTimeline(editor:editor).frame(width:max(600,g.size.width)*editor.timelineZoom,height:225)}}.frame(height:235)
        }
        HStack {
            Picker(L("輸出配音"),selection:Binding(get:{editor.outputDubMode ?? "yue"},set:editor.setOutputDubMode)) {Text(L("廣東話")).tag("yue");Text(L("英文")).tag("en");Text(L("廣東話＋英文")).tag("both")}.frame(width:240)
            Button(L("新增漏配對白")) {editor.addDialogue()}
        }
    }
    @ViewBuilder func cueList(_ document:EditDocument) -> some View {
        Text(editor.activeTrackTitle+" · "+L("只顯示所選音軌提示")).font(.caption).foregroundStyle(.secondary)
        HStack {
            TextField(L("搜尋對白／原文"),text:$editor.cueSearch).textFieldStyle(.roundedBorder)
            Picker(L("對白篩選"),selection:$editor.cueFilter) {Text(L("全部")).tag("all");Text(L("需覆核")).tag("issues");Text(L("已停用")).tag("disabled")}.labelsHidden().frame(width:85)
        }
        ScrollViewReader {proxy in
            ScrollView {LazyVStack(spacing:4) {
                ForEach(Array(document.segments.enumerated()).filter {_,segment in
                    (editor.cueSearch.isEmpty || [segment.text,segment.original,segment.english ?? ""].contains {$0.localizedCaseInsensitiveContains(editor.cueSearch)}) && (editor.cueFilter=="all" || (editor.cueFilter=="disabled" && !segment.enabled) || (editor.cueFilter=="issues" && editor.flaggedSegments.contains(segment.id)))
                },id:\.element.id) {index,segment in
                    Button {editor.selectSegment(segment.id)} label:{
                        HStack(alignment:.top,spacing:10) {
                            Text("\(index+1)").font(.caption.monospaced()).frame(width:20)
                            Text(String(format:"%.2f–%.2f",segment.start,segment.end)).font(.caption.monospaced()).frame(width:78,alignment:.leading)
                            Text(editor.previewLanguage=="en" ? segment.english ?? segment.text:segment.text).lineLimit(2).frame(maxWidth:.infinity,alignment:.leading)
                            if !segment.enabled {Text(L("停用")).font(.caption).foregroundStyle(.secondary)}
                            if editor.flaggedSegments.contains(segment.id) {Image(systemName:"exclamationmark.triangle.fill").foregroundStyle(.orange).help(L("所選音軌需要覆核"))}
                            else if editor.repairedSegments.contains(segment.id) {Image(systemName:"arrow.triangle.2.circlepath").foregroundStyle(.blue).help(L("此音軌已替代補聲"))}
                        }.padding(8).background(editor.selectedSegment==segment.id ? accent.opacity(0.16):Color.secondary.opacity(0.04),in:RoundedRectangle(cornerRadius:7))
                    }.buttonStyle(.plain).id(segment.id)
                }
            }}.frame(maxHeight:.infinity)
            .onChange(of:editor.selectedSegment) {id in if let id {proxy.scrollTo(id,anchor:.center)}}
        }
    }
    @ViewBuilder func selectedCue(_ document:EditDocument) -> some View {
        if let i=editor.segmentIndex {
            let segment=document.segments[i]
            VStack(alignment:.leading,spacing:12) {
                HStack {
                    Text(String(format:L("第 %d 段 · %.2f–%.2f 秒"),i+1,segment.start,segment.end)).font(.headline)
                    Button(L("上一段")) {editor.selectSegment(document.segments[i-1].id)}.disabled(i==0)
                    Button(L("下一段")) {editor.selectSegment(document.segments[i+1].id)}.disabled(i+1>=document.segments.count)
                    if editor.flaggedSegments.contains(segment.id) {Label(L("時間／重疊需覆核"),systemImage:"exclamationmark.triangle").font(.caption).foregroundStyle(.orange)}
                    Spacer()
                    Toggle(L("啟用"),isOn:Binding(get:{segment.enabled},set:{v in editor.updateSegment {$0.enabled=v}})).toggleStyle(.checkbox)
                }
                HStack {
                    Picker(L("試聽語言"),selection:$editor.previewLanguage) {Text(L("廣東話")).tag("yue");Text(L("英文")).tag("en")}.frame(width:180)
                    Button(L("▶ 原聲")) {editor.playSegment()}
                    ForEach(VoiceEngineChoice.all) {engine in
                        Button((editor.deliveredTake(engine.id)==nil ? "生成＋播放 ":"▶ ")+engine.title) {editor.previewEngine=engine.id;if editor.deliveredTake(engine.id) != nil {editor.playEngine(engine.id)} else {model.generateAndPlayEditor(engine.id)}}.disabled(model.busy && editor.deliveredTake(engine.id)==nil)
                    }
                    Button(L("停止")) {editor.audio.pause();editor.player.pause();editor.auditionLabel=""}
                }
                if !editor.auditionLabel.isEmpty {Text(editor.auditionLabel).font(.caption).foregroundStyle(accent)}
                HStack {Text(L("採用呢段聲音：")).font(.caption);Picker(L("引擎"),selection:$editor.previewEngine) {ForEach(VoiceEngineChoice.all) {Text($0.title).tag($0.id)}}.frame(width:180);Button(L("採用所選 take")) {editor.playEngine(editor.previewEngine,use:true)}.disabled(editor.deliveredTake(editor.previewEngine)==nil)}
                if let note=segment.sourceNote,!note.isEmpty {Text(note).font(.caption).foregroundStyle(.orange)}
                if editor.previewLanguage=="en" {
                    TextField(L("English dubbing script"),text:Binding(get:{segment.english ?? ""},set:{v in editor.updateSegment {$0.english=v;$0.audioTake=nil}}),axis:.vertical).lineLimit(3...6).textFieldStyle(.roundedBorder)
                } else {TextField(L("廣東話配音台詞"),text:segmentText(\.text),axis:.vertical).lineLimit(3...6).textFieldStyle(.roundedBorder)}
                DisclosureGroup(L("原文校正／顯示字幕")) {
                    TextField(L("原文"),text:segmentText(\.original),axis:.vertical).lineLimit(2...4).textFieldStyle(.roundedBorder)
                    TextField(L("顯示字幕（留空跟配音台詞）"),text:segmentText(\.captionText),axis:.vertical).lineLimit(2...4).textFieldStyle(.roundedBorder)
                }
                HStack {
                    Toggle(L("加入多選"),isOn:Binding(get:{editor.selectedSegments.contains(segment.id)},set:{v in if v{editor.selectedSegments.insert(segment.id)}else{editor.selectedSegments.remove(segment.id)}})).toggleStyle(.checkbox)
                    Button(String(format:L("將此聲線套用到所選 %d 段"),editor.selectedSegments.count)) {editor.update {d in for j in d.segments.indices where editor.selectedSegments.contains(d.segments[j].id) {d.segments[j].speakerId=segment.speakerId;d.segments[j].audioTake=nil}}}.disabled(editor.selectedSegments.isEmpty)
                }
                HStack {
                    Picker(L("角色"),selection:segmentText(\.speakerId)) {Text(L("未指定")).tag("");ForEach(editor.profiles) {Text(localizedRoleName($0.name)).tag($0.id)}}
                    Toggle(L("套用到本片同角色"),isOn:$options.allRole).toggleStyle(.checkbox)
                    Button(L("套用聲線")) {
                        let oldID=(editor.config["defaultSpeaker"] as? String) ?? ""
                        // Explicit old-role selection is shown below; never alter another project.
                        let from=options.speakerTarget.isEmpty ? oldID : options.speakerTarget
                        if options.allRole {editor.update {d in for j in d.segments.indices where d.segments[j].speakerId==from {d.segments[j].speakerId=segment.speakerId;d.segments[j].audioTake=nil}}}
                    }.disabled(!options.allRole)
                }
                if options.allRole {Picker(L("將呢個角色全部改成上方聲線"),selection:$options.speakerTarget) {Text(L("揀原角色")).tag("");ForEach(editor.profiles) {Text(localizedRoleName($0.name)).tag($0.id)}}}
                DisclosureGroup(L("進階：時間、語速、裁切及其他 take")) {
                HStack {number("配音開始",segmentNumber(\.start));number("結束",segmentNumber(\.end));number("字幕開始",segmentNumber(\.captionStart));number("結束",segmentNumber(\.captionEnd))}
                HStack {number("語速 0.5–2×",segmentNumber(\.rate));number("裁頭（秒）",segmentNumber(\.trimStart));number("裁尾（秒）",segmentNumber(\.trimEnd))}
                Text(L("拖字幕軌左右邊界做 trim；拖配音軌邊界調整目標時段。語速 1× 使用自動時長配合；手動語速及裁切會覆寫自動配合。")).font(.caption).foregroundStyle(.secondary)
                HStack {
                    Picker(L("試音引擎"),selection:$editor.previewEngine) {ForEach(VoiceEngineChoice.all) {Text($0.title).tag($0.id)}}.frame(width:200)
                    Picker(L("試音／改稿語言"),selection:$editor.previewLanguage) {Text(L("廣東話")).tag("yue");Text(L("英文")).tag("en")}.frame(width:180)
                    Button(L("生成呢段試音")) {model.submitEditor(previewOnly:true)}
                    Button(L("重譯原文建議")) {model.suggestEditorShortening(translate:true)}.disabled(model.busy)
                    Button(L("AI 改短建議")) {model.suggestEditorShortening()}.disabled(model.busy)
                    Button(L("另一個 take")) {editor.updateSegment {$0.take+=1;$0.audioTake=nil};model.submitEditor(previewOnly:true)}
                    Stepper("Take \(segment.take)",value:Binding(get:{segment.take},set:{v in editor.updateSegment {$0.take=v}}),in:0...100000)
                    Button(L("分割台詞")) {options.showSplit.toggle();editor.splitAt=max(1,segment.text.count/2)}
                    Button(L("合併下一段"),action:editor.mergeNext).disabled(i+1>=document.segments.count)
                }
                }
                if let suggestion=editor.suggestion {
                    Text(L("待批核建議：")+suggestion)
                    HStack {Button(L("採用建議")) {editor.acceptSuggestion()};Button(L("保留原文")) {editor.suggestion=nil;editor.suggestionTarget=nil}}
                }
                if options.showSplit {
                    Text(L("將播放頭移到分割時間，再揀文字分界；左右兩段會重新配音，唔會按比例切斷字音。")).font(.caption)
                    Stepper("文字分界：第 \(editor.splitAt) 字之後",value:$editor.splitAt,in:1...max(1,segment.text.count-1))
                    if !segment.captionText.isEmpty {Stepper("顯示字幕分界：第 \(editor.splitCaptionAt) 字之後",value:$editor.splitCaptionAt,in:1...max(1,segment.captionText.count-1))}
                    Text(String(segment.text.prefix(editor.splitAt))+" ｜ "+String(segment.text.dropFirst(editor.splitAt)))
                    Button(L("分割並重新配音")) {editor.splitSegment()}
                    Button(L("Blade：切開已選聲音 take")) {editor.splitSegment(reuseAudio:true)}.disabled(segment.audioTake == nil)
                }
            }.padding(12).background(Color.secondary.opacity(0.05),in:RoundedRectangle(cornerRadius:10))
        }
    }
    @ViewBuilder func cuts(_ document:EditDocument) -> some View {
        Text(L("剪接以原片工作範圍嘅秒數記錄；輸出按下列次序串接，影片、全部聲音及字幕一齊連動。原片保留。")).font(.caption)
        Button(L("Blade：喺播放頭分割影片"),action:editor.bladeClip)
        ForEach(Array(document.clips.enumerated()),id:\.element.id) {i,clip in
            VStack(alignment:.leading,spacing:10) {
                HStack {
                    Text(String(format:L("片段 %d"),i+1)).fixedSize()
                    Spacer()
                    Button(L("預覽")) {editor.playSource();editor.seek(clip.start);editor.stopAt=clip.end;editor.loopStart=clip.start;editor.player.play()}
                    Button("↑") {editor.update {$0.clips.swapAt(i,i-1)}}.disabled(i==0)
                    Button("↓") {editor.update {$0.clips.swapAt(i,i+1)}}.disabled(i+1==document.clips.count)
                }
                HStack {
                    number("入點",Binding(get:{clip.start},set:{v in editor.update {$0.clips[i].start=v}}))
                    number("出點",Binding(get:{clip.end},set:{v in editor.update {$0.clips[i].end=v}}))
                }
                Toggle(L("保留"),isOn:Binding(get:{clip.enabled},set:{v in editor.update {$0.clips[i].enabled=v}})).toggleStyle(.checkbox)
                if !clip.enabled {Toggle(L("後面前移"),isOn:Binding(get:{clip.ripple},set:{v in editor.update {$0.clips[i].ripple=v}})).toggleStyle(.checkbox)}
            }.padding(10).background(Color.primary.opacity(0.035),in:RoundedRectangle(cornerRadius:8))
        }
        Text(L("取消保留並關閉「後面前移」會輸出同長度黑畫面及靜音。成品頁籤可以檢查剪輯後結果。")).font(.caption).foregroundStyle(.secondary)
        GroupBox(L("成品字幕排版")) {
            VStack(alignment:.leading,spacing:10) {
                number(L("字幕底部位置"),Binding(get:{document.captionBottom},set:{v in editor.update {$0.captionBottom=v}}))
                number(L("字幕字體大小"),Binding(get:{document.captionSize},set:{v in editor.update {$0.captionSize=v}}))
                Text(L("只調整生成字幕的排版；原裝中文字幕的時間保持不變。")).font(.caption).foregroundStyle(.secondary)
            }.padding(8)
        }
        Button(L("重新連結原片"),action:editor.relink)
    }
    @ViewBuilder func voices(_ document:EditDocument) -> some View {
        Button {RoleManagerWindow.present(model:model,editor:editor,live:livePreview)} label:{Label(L("開啟角色相簿"),systemImage:"person.3.sequence.fill")}.buttonStyle(StudioButtonStyle(prominent:true))
        Text(String(format:L("%d 個角色"),editor.profiles.count)).foregroundStyle(.secondary)

    }
    var versionList: some View {
        VStack(alignment:.leading,spacing:12) {
            Text(L("新版本完成前保留舊成品；刪除成品只移走嗰個 MP4，草稿同配音仍保留。")).font(.caption)
            ForEach(editor.versions) {v in
                HStack {
                    VStack(alignment:.leading) {Text(v.created);ProductionDurationLabel(folder:v.folder,output:v.output,fallbackSeconds:v.processingSeconds);Text(editorStatus(v.status)).font(.caption).foregroundStyle(.secondary)}
                    Spacer()
                    if let url=v.output,FileManager.default.fileExists(atPath:url.path) {
                        Button(L("播放")) {editor.play(v)}
                        Button(L("檔案")) {NSWorkspace.shared.activateFileViewerSelecting([url])}
                        Button(L("移到垃圾桶"),role:.destructive) {editor.trashVersion(v)}.disabled(model.busy)
                    }
                    if ["script-ready","script-partial","script-applied"].contains(v.status) {Button(L("比較字幕")) {options.subtitleProposal=v}}
                    if v.status=="voice-samples" {Button(L("試音")) {options.voiceSampleVersion=v}}
                    if FileManager.default.fileExists(atPath:v.folder.appendingPathComponent("role-reanalysis.json").path) {Button(L("新版人物卡")) {editor.showAnalyzedRoles(v,model:model)}}
                }
                if let url=v.output {ValidationSummary(output:url) {t in editor.play(v);editor.seek(t)}}
            }
        }
    }
    var steps: some View {
        VStack(alignment:.leading,spacing:10) {
            Text(L("待修正片段及處理紀錄")).font(.headline)
            if !editor.failedTracks.isEmpty || !editor.segmentIssues.isEmpty || !editor.studioIssues.isEmpty {
                Button(L("重試並修復所有音軌")) {model.repairMissingTracks()}.disabled(model.busy)
                Text(L("重新檢查已選模型並有限次重試缺聲片段；保留成功錄音，按已授權補聲設定繼續。")).font(.caption).foregroundStyle(.secondary)
            }
            Text(L("自動覆聽只提供核對線索；語言、名稱同短句可能有辨識誤差。請逐段比較原聲及所選配音。")).font(.caption).foregroundStyle(.secondary)
            StudioIssueList(model:model,editor:editor) {options.inspector="dialogue"}
            if !editor.sourceGaps.isEmpty {
                Text(L("原聲有人聲活動，但未對應台詞：需要試聽分辨對白、歌聲或音效。")).foregroundStyle(.orange)
                ForEach(Array(editor.sourceGaps.enumerated()),id:\.offset) {_,gap in
                    Button(String(format:"聽原聲 %.2f–%.2f 秒",gap["start"] ?? 0,gap["end"] ?? 0)) {editor.playSource();editor.seek(gap["start"] ?? 0);editor.player.play()}
                }
            }
            ForEach([("原聲對白覆蓋／漏段","source-coverage.json"),("原始辨識","cues.json"),("翻譯／角色配對","review.json"),("配音時間檢查","timing.json"),("輸出品質檢查","validation.json")],id:\.1) {name,file in
                if let document=editor.document {
                    let url=URL(fileURLWithPath:document.review).deletingLastPathComponent().appendingPathComponent(file)
                    HStack {Text(L(name));Spacer();Text(L(FileManager.default.fileExists(atPath:url.path) ? "已保存":"未完成")).foregroundStyle(.secondary);Button(L("檢視資料")) {NSWorkspace.shared.open(url)}.disabled(!FileManager.default.fileExists(atPath:url.path))}
                }
            }
            Text(L("台詞／角色修改會更新相關配音，再混音合片；影片剪輯會同步重排全部軌道。原始辨識保留作追溯。")).font(.caption)
        }
    }
    var queue: some View {StudioQueueView(model:model)}

}

final class EditorialDrag: ObservableObject { var recorded=false; var value: (id:String,track:Int,edge:Int)? }
struct EditorialTimeline: View {
    @ObservedObject var editor: ProjectEditor
    @StateObject private var dragState=EditorialDrag()
    var compact=false
    var body: some View {
        GeometryReader {g in
            let duration=max(1,editor.duration)
            let rowHeight:Double=compact ? 17:40
            ZStack(alignment:.topLeading) {
                Color.secondary.opacity(0.06)
                Canvas {context,size in
                    for track in 0...4 {
                        context.draw(Text(["影片","原聲","背景","字幕","配音"][track]).font(.caption),at:CGPoint(x:22,y:Double(track)*rowHeight+rowHeight/2))
                    }
                    let width=max(1,size.width-55)
                    for (track,rows) in [(0,(editor.document?.clips ?? []).map {($0.id,$0.start,$0.end,$0.enabled)}),(3,(editor.document?.segments ?? []).map {($0.id,$0.captionStart,$0.captionEnd,$0.enabled)}),(4,(editor.document?.segments ?? []).map {($0.id,$0.start,$0.end,$0.enabled)})] {
                        for (id,a,b,enabled) in rows {
                            let rect=CGRect(x:55+a/duration*width,y:Double(track)*rowHeight+5,width:max(2,(b-a)/duration*width),height:rowHeight-8)
                            context.fill(Path(roundedRect:rect,cornerRadius:3),with:.color(enabled ? (id==editor.selectedSegment ? .orange:accent).opacity(0.7):.gray.opacity(0.3)))
                            if editor.flaggedSegments.contains(id) {context.stroke(Path(roundedRect:rect,cornerRadius:3),with:.color(.red),lineWidth:2)}
                        }
                    }
                    for (track,key) in [(1,"dialoguePath"),(2,"backgroundPath")] {
                        let values=editor.waveforms[key] ?? []
                        var wave=Path()
                        for (i,value) in values.enumerated() {
                            let x=55+Double(i)/Double(max(1,values.count-1))*width
                            let mid=Double(track)*rowHeight+rowHeight/2,amplitude=Double(value)*(compact ? 7:13)
                            wave.move(to:CGPoint(x:x,y:mid-amplitude));wave.addLine(to:CGPoint(x:x,y:mid+amplitude))
                        }
                        context.stroke(wave,with:.color(.secondary),lineWidth:1)
                        if values.isEmpty {context.draw(Text(L("未有分離音軌")).font(.caption2).foregroundColor(.secondary),at:CGPoint(x:130,y:Double(track)*rowHeight+rowHeight/2))}
                    }
                    for tick in 0...8 {
                        let t=duration*Double(tick)/8
                        context.draw(Text(String(format:"%.1fs",t)).font(.system(size:9,design:.monospaced)),at:CGPoint(x:min(size.width-18,55+t/duration*width),y:rowHeight*5+10))
                    }
                    let x=55+editor.seconds/duration*width
                    var line=Path();line.move(to:CGPoint(x:x,y:0));line.addLine(to:CGPoint(x:x,y:size.height));context.stroke(line,with:.color(.red),lineWidth:2)
                }
            }.gesture(DragGesture(minimumDistance:0).onChanged {value in
                if editor.playingVersion != nil {editor.playSource()}
                let width=max(1,g.size.width-55);let t=max(0,min(duration,(value.location.x-55)/width*duration));let track=min(4,max(0,Int(value.startLocation.y/rowHeight)))
                if dragState.value==nil,track>=3,let s=editor.document?.segments.first(where:{s in let a=track==3 ? s.captionStart:s.start;let b=track==3 ? s.captionEnd:s.end;let start=(value.startLocation.x-55)/width*duration;return start>=a && start<=b}) {
                    editor.selectedSegment=s.id
                    let a=track==3 ? s.captionStart:s.start;let b=track==3 ? s.captionEnd:s.end;let x=(value.startLocation.x-55)/width*duration
                    dragState.value=(s.id,track,abs(x-a)*width/duration<8 ? -1:abs(x-b)*width/duration<8 ? 1:0)
                }
                if let drag=dragState.value,drag.edge != 0 {
                    editor.updateSegment(recordUndo:!dragState.recorded) {s in
                        if drag.track==3 {if drag.edge<0{s.captionStart=min(t,s.captionEnd-0.05)}else{s.captionEnd=max(t,s.captionStart+0.05)}}
                        else {if drag.edge<0{s.start=min(t,s.end-0.05)}else{s.end=max(t,s.start+0.05)}}
                    }
                    dragState.recorded=true
                } else {editor.seek(t)}
            }.onEnded {_ in dragState.value=nil;dragState.recorded=false})
        }
    }
}

extension AppModel {
    func suggestEditorShortening(translate:Bool=false) {
        let editor=projectEditor
        guard !busy,let document=editor.document,let i=editor.segmentIndex else{return}
        let s=document.segments[i]
        let speech=editor.previewLanguage=="en" ? s.english ?? "":s.text
        editor.suggestionTarget=(document.review,s.id,speech,editor.previewLanguage)
        let cfg:[String:Any]=["targetLanguage":editor.previewLanguage,"port":engine.port,"model":editor.config["model"] as? String ?? selectedModel,"index":i,"cue":["start":s.start,"end":s.end,"text":s.original,"cantonese":speech],"measuredSeconds":s.end-s.start]
        let e=engine,data=try! JSONSerialization.data(withJSONObject:cfg)
        task("建立改短建議") {try e.worker(translate ? "translate-cue" : "shorten-cue",config:try JSONSerialization.jsonObject(with:data) as! [String:Any])}
    }
}
extension ProjectEditor {
    func acceptSuggestion() {
        guard let target=suggestionTarget,let text=suggestion,document?.review==target.review,
              let i=document?.segments.firstIndex(where:{$0.id==target.segment}),(target.language=="en" ? document?.segments[i].english ?? "":document?.segments[i].text)==target.text else {error="原稿已修改，請重新要求建議。";suggestion=nil;return}
        update {if target.language=="en" {$0.segments[i].english=text}else{$0.segments[i].text=text};$0.segments[i].audioTake=nil};suggestion=nil;suggestionTarget=nil
    }
}

private func editorialWaveform(_ path: String) -> [Float] {
    guard let file=try? AVAudioFile(forReading:URL(fileURLWithPath:path)),file.length>0 else{return []}
    let format=file.processingFormat
    guard let buffer=AVAudioPCMBuffer(pcmFormat:format,frameCapacity:1024) else{return []}
    var peaks:[Float]=[]
    for i in 0..<200 {
        file.framePosition=AVAudioFramePosition(Double(file.length-1)*Double(i)/200)
        do {try file.read(into:buffer,frameCount:min(1024,AVAudioFrameCount(file.length-file.framePosition)))} catch{return []}
        guard let data=buffer.floatChannelData else{return []}
        var peak:Float=0
        for j in 0..<Int(buffer.frameLength) {peak=max(peak,abs(data[0][j]))}
        peaks.append(peak)
    }
    let scale=max(0.01,peaks.max() ?? 1)
    return peaks.map{min(1,$0/scale)}
}
extension ProjectEditor {
    func loadWaveforms() {
        waveforms=[:]
        let review=document?.review
        let paths=["dialoguePath","backgroundPath"].compactMap {key -> (String,String)? in guard let path=config[key] as? String else{return nil};return (key,path)}
        Task {
            let values=await Task.detached {Dictionary(uniqueKeysWithValues:paths.map{($0.0,editorialWaveform($0.1))})}.value
            if document?.review==review {waveforms=values}
        }
    }
}

func editorStatus(_ status:String) -> String {
    ["prosody-experiment":"日文表演實驗已保存","preview-script":"英文稿已生成","queued":"等待生成","running":"生成中","failed":"需要修正","complete":"已完成","preview":"片段試音","partial":"部分音軌未完成","superseded":"已由新版取代","script-ready":"字幕草稿待核對","script-partial":"字幕草稿未完成","script-applied":"字幕草稿已套用","audition-review":"試音已保存，待覆核","voice-samples":"試音組"][status] ?? status
}

extension ProjectEditor {
    func addDialogue() {
        let a=min(max(0,seconds),max(0,duration-0.2)),b=min(duration,a+2)
        let segment=EditSegment(sources:[],start:a,end:b,captionStart:a,captionEnd:b,text:"",original:"",speakerId:profiles.first?.id ?? "",manual:true,sourceNote:"手動補回嘅對白；請聽原聲、填原文及台詞，再試音。")
        update {$0.segments.append(segment);$0.segments.sort{$0.start<$1.start}};selectedSegment=segment.id
    }
}

extension ProjectEditor {
    /// Match approved text, role and time before offering an existing engine take.
    func engineTake(_ engine:String,language:String?=nil,segmentID:String?=nil) -> (path:String,length:Double)? {
        let language=language ?? previewLanguage
        let key=engine+":"+language+":"+(segmentID ?? selectedSegment ?? "")
        if let take=takeCache[key],FileManager.default.fileExists(atPath:take.path) {return take}
        if takeMisses.contains(key) {return nil}
        takeLookupCount+=1
        let take=lookupEngineTake(engine,language:language,segmentID:segmentID)
        if let take {takeCache[key]=take} else {takeMisses.insert(key)}
        return take
    }
    private func lookupEngineTake(_ engine:String,language:String,segmentID:String?=nil) -> (path:String,length:Double)? {
        guard let document,let i=document.segments.firstIndex(where:{$0.id==(segmentID ?? selectedSegment)}) else{return nil}
        if let saved=cueVoiceRecording(engine,language:language,segmentID:segmentID) {return saved.canAdopt ? (saved.path,saved.length):nil}
        let segment=document.segments[i],root=URL(fileURLWithPath:document.review).deletingLastPathComponent()
        var folders:[URL]=[]
        for version in versions where version.status=="preview" {
            guard let data=try? Data(contentsOf:version.folder.appendingPathComponent("version.json")),let meta=try? JSONSerialization.jsonObject(with:data) as? [String:Any],meta["engine"] as? String==engine,meta["language"] as? String==language,meta["segment"] as? String==segment.id else {continue}
            if let wanted=auditionVoiceStyle,let reviewData=try? Data(contentsOf:version.folder.appendingPathComponent("review.json")),let review=try? JSONSerialization.jsonObject(with:reviewData) as? [String:Any],(review["config"] as? [String:Any])?["voiceStyleMode"] as? String != wanted {continue}
            folders.append(version.folder)
        }
        let reportFolders=versions.filter {$0.status=="complete" || $0.status=="partial"}.map(\.folder)+[root]
        for folder in reportFolders {
            guard let data=try? Data(contentsOf:folder.appendingPathComponent("report.json")),let report=try? JSONSerialization.jsonObject(with:data) as? [String:Any] else{continue}
            for track in report["tracks"] as? [[String:Any]] ?? [] where track["engine"] as? String==engine && (track["language"] as? String ?? "yue")==language {
                if let path=track["report"] as? String {folders.append(URL(fileURLWithPath:path).deletingLastPathComponent())}
            }
        }
        let key=engine+":"+language
        if let folder=evidenceFolders[key],!folders.contains(folder) {folders.append(folder)}
        for folder in folders {
            guard let data=try? Data(contentsOf:folder.appendingPathComponent("review.json")),let obj=try? JSONSerialization.jsonObject(with:data) as? [String:Any],let cues=obj["cues"] as? [[String:Any]],let cue=cues.first(where:{abs(($0["start"] as? Double ?? -1)-segment.start)<0.001 && abs(($0["end"] as? Double ?? -1)-segment.end)<0.001}),cue["speakerId"] as? String==segment.speakerId else{continue}
            guard engine != "gpt-sovits-v2" || (obj["config"] as? [String:Any])?["gsvVersion"] as? String=="v2ProPlus" else{continue}
            guard (cue["_seed"] as? Int ?? 42)==segment.take,
                  (cue["editorRate"] as? Double ?? 1)==segment.rate,
                  (cue["editorTrimStart"] as? Double ?? 0)==segment.trimStart,
                  (cue["editorTrimEnd"] as? Double ?? 0)==segment.trimEnd else {continue}
            let expected=language=="en" ? segment.english ?? "":segment.text
            let actual=language=="en" ? cue["english"] as? String ?? cue["cantonese"] as? String:cue["cantonese"] as? String
            guard actual==expected,let timing=try? Data(contentsOf:folder.appendingPathComponent("timing.json")),let rows=try? JSONSerialization.jsonObject(with:timing) as? [[String:Any]],let row=rows.first(where:{abs(($0["start"] as? Double ?? -1)-segment.start)<0.001 && abs(($0["end"] as? Double ?? -1)-segment.end)<0.001}) else {continue}
            // The newest matching failure must not silently expose an older take.
            guard row["skipped"] as? Bool != true,let path=row["renderedAudio"] as? String ?? row["audio"] as? String,!URL(fileURLWithPath:path).lastPathComponent.hasPrefix("skipped-"),let measuredLength=Self.audioLength(path),measuredLength>0 else {return nil}
            if let seconds=row["renderedSeconds"] as? Double ?? row["seconds"] as? Double,seconds<=0 {return nil}
            if !URL(fileURLWithPath:path).lastPathComponent.hasPrefix("original-vocalization-"),let manifestData=try? Data(contentsOf:folder.appendingPathComponent("voice-reference-manifest.json")),let manifest=try? JSONSerialization.jsonObject(with:manifestData) as? [String:String],let hash=manifest[segment.speakerId],let profile=profiles.first(where:{$0.id==segment.speakerId}) {
                let style=(obj["config"] as? [String:Any])?["voiceStyleMode"] as? String
                guard let reference=(style=="natural" ? naturalReference(profile,engine:engine,language:language,castingFolder:folder):profile.referenceFor(engine,language)),let bytes=try? Data(contentsOf:URL(fileURLWithPath:reference)),SHA256.hash(data:bytes).map({String(format:"%02x",$0)}).joined()==hash else{continue}
            }
            return (path,row["renderedSeconds"] as? Double ?? row["seconds"] as? Double ?? segment.end-segment.start)
        }
        let expected=language=="en" ? segment.english ?? "":segment.text
        if engine=="gpt-sovits-v2",recordedModelVersions[key] != "v2ProPlus" {return nil}
        for row in previewRows[key] ?? [] where abs((row["start"] as? Double ?? -1)-segment.start)<0.001 && abs((row["end"] as? Double ?? -1)-segment.end)<0.001 {
            guard row["speakerId"] as? String==segment.speakerId,(row["_seed"] as? Int ?? 42)==segment.take,segment.rate==1,segment.trimStart==0,segment.trimEnd==0,row["cantonese"] as? String==expected,let path=row["audio"] as? String,!URL(fileURLWithPath:path).lastPathComponent.hasPrefix("skipped-"),let length=Self.audioLength(path) else{continue}
            if !URL(fileURLWithPath:path).lastPathComponent.hasPrefix("original-vocalization-"),let folder=evidenceFolders[key],let bytes=try? Data(contentsOf:folder.appendingPathComponent("voice-reference-manifest.json")),let manifest=try? JSONSerialization.jsonObject(with:bytes) as? [String:String],let hash=manifest[segment.speakerId],let profile=profiles.first(where:{$0.id==segment.speakerId}),let reference=try? Data(contentsOf:URL(fileURLWithPath:(row["voiceStyleMode"] as? String=="natural" ? naturalReference(profile,engine:engine,language:language):nil) ?? profile.referenceFor(engine,language))) {
                guard SHA256.hash(data:reference).map({String(format:"%02x",$0)}).joined()==hash else{continue}
            }
            return (path,length)
        }
        return nil
    }
    func cueAudioStatus(_ engine:String,segmentID:String?=nil)->String {
        if let take=fallbackTake(engine,segmentID:segmentID) {return L("補聲來源")+": "+take.source}
        if let take=engineTake(engine,segmentID:segmentID) {return URL(fileURLWithPath:take.path).lastPathComponent.hasPrefix("original-vocalization-") ? L("保留原聲（未經聲線模仿）"):L("可試聽")+(engine.hasPrefix("gpt-sovits") ? " · "+gsvModelTitle(recordedModelVersions[engine+":"+previewLanguage] ?? "v2"):"")}
        guard let s=document?.segments.first(where:{$0.id==(segmentID ?? selectedSegment)}) else{return L("等待生成")}
        let key=engine+":"+previewLanguage
        if (timingRows[key] ?? []).contains(where:{abs(($0["start"] as? Double ?? -1)-s.start)<0.001 && $0["skipped"] as? Bool==true}) {return L("生成失敗")}
        if (previewRows[key] ?? []).contains(where:{abs(($0["start"] as? Double ?? -1)-s.start)<1.5}) {return L("台詞或時間已改，需重新配音")}
        return L(timelineAudioStates[key]=="running" ? "生成中":"等待生成")
    }
    func fallbackTake(_ engine:String,language:String?=nil,segmentID:String?=nil)->(path:String,source:String)? {
        let language=language ?? previewLanguage
        guard let s=document?.segments.first(where:{$0.id==(segmentID ?? selectedSegment)}) else{return nil}
        if engine=="gpt-sovits-v2",recordedModelVersions[engine+":"+language] != "v2ProPlus" {return nil}
        for row in fallbackRows[engine+":"+language] ?? [] where abs((row["start"] as? Double ?? -1)-s.start)<0.001 && abs((row["end"] as? Double ?? -1)-s.end)<0.001 {
            let expected=language=="en" ? s.english ?? "":s.text
            guard row["text"] as? String==expected,row["speakerId"] as? String==s.speakerId,(row["seed"] as? Int ?? 42)==s.take,s.rate==1,s.trimStart==0,s.trimEnd==0,let path=row["audio"] as? String,Self.audioLength(path) != nil else{continue}
            return (path,row["sourceEngine"] as? String=="original" ? L("日語原聲"):VoiceEngineChoice.all.first {$0.id==row["sourceEngine"] as? String}?.title ?? row["sourceEngine"] as? String ?? "")
        }
        return nil
    }
    func playFallback() {
        guard let take=fallbackTake(previewEngine) else{return}
        isolatedStopAt=nil;player.pause();audio.pause();audio.replaceCurrentItem(with:AVPlayerItem(url:URL(fileURLWithPath:take.path)));audio.play();auditionLabel=L("補聲來源")+": "+take.source
    }
    func deliveredTake(_ engine:String,language:String?=nil,segmentID:String?=nil)->(path:String,length:Double)? {
        if let take=fallbackTake(engine,language:language,segmentID:segmentID),let length=Self.audioLength(take.path) {return (take.path,length)}
        return engineTake(engine,language:language,segmentID:segmentID)
    }
    private func recordingVersion(_ path:String)->String {
        var folder=URL(fileURLWithPath:path).deletingLastPathComponent()
        for _ in 0..<8 {
            if let bytes=try? Data(contentsOf:folder.appendingPathComponent("review.json")),let row=try? JSONSerialization.jsonObject(with:bytes) as? [String:Any],let cfg=row["config"] as? [String:Any] {return gsvModelTitle(cfg["gsvVersion"] as? String ?? "v2")}
            folder=folder.deletingLastPathComponent()
        }
        return ""
    }
    func clearAuditionStop() {isolatedStopAt=nil;stopAt=nil}
    func playEngine(_ engine:String,use:Bool=false,native:Bool=false) {
        previewEngine=engine
        if !native,let fallback=fallbackTake(engine),let length=Self.audioLength(fallback.path) {
            if use {updateSegment {$0.audioTake=fallback.path;$0.audioLength=length;$0.audioAcceptedHistoryID=nil;$0.rate=1;$0.trimStart=0;$0.trimEnd=0}}
            previewEngine=engine;playFallback();return
        }
        guard let take=engineTake(engine) else {
            if !use,let preview=versionPreviewTake(engine,language:previewLanguage) {playVersionPreview(preview);return}
            error="呢段未有符合目前台詞嘅試音，請生成新 take。";return
        }
        isolatedStopAt=nil;player.pause();audio.pause()
        if use {updateSegment {$0.audioTake=take.path;$0.audioLength=take.length;$0.audioAcceptedHistoryID=nil;$0.rate=1;$0.trimStart=0;$0.trimEnd=0}}
        audio.replaceCurrentItem(with:AVPlayerItem(url:URL(fileURLWithPath:take.path)));audio.play()
        let original=URL(fileURLWithPath:take.path).lastPathComponent.hasPrefix("original-vocalization-")
        auditionLabel=L(use ? "已採用並播放：":"正在播放：")+(original ? L("保留原聲"):(engine.hasPrefix("gpt-sovits") ? "GPT-SoVITS "+recordingVersion(take.path):VoiceEngineChoice.all.first {$0.id==engine}?.title ?? engine))+(original ? "":(" · "+L(previewLanguage=="en" ? "英文":"廣東話")))
    }
}
extension AppModel {
    func generateAndPlayEditor(_ engine:String) {generateCueVoice(engine,language:projectEditor.previewLanguage)}

}

struct EngineReferenceControls:View {
    @ObservedObject var editor:ProjectEditor
    var index:Int
    @ObservedObject var options:ProjectWorkspaceOptions
    var key:String {options.referenceEngine+":"+options.referenceLanguage}
    var own:EngineVoiceReference {editor.profiles[index].engineReferences?[key] ?? EngineVoiceReference()}
    func update(_ mutate:(inout EngineVoiceReference)->Void) {
        var value=own;mutate(&value)
        if editor.profiles[index].engineReferences==nil {editor.profiles[index].engineReferences=[:]}
        editor.profiles[index].engineReferences?[key]=value;editor.dirty=true;editor.scheduleSave()
    }
    var body:some View {
        DisclosureGroup(L("每個引擎獨立語言參考（可選）")) {
            HStack {
                Picker(L("引擎"),selection:$options.referenceEngine) {ForEach(VoiceEngineChoice.all) {Text($0.title).tag($0.id)}}.frame(width:220)
                Picker(L("語言"),selection:$options.referenceLanguage) {Text(L("廣東話")).tag("yue");Text(L("英文")).tag("en")}.frame(width:150)
                Button(L("匯入 3–10 秒 WAV")) {importAudio()}
                if !own.reference.isEmpty {Button(L("聽參考")) {editor.player.pause();editor.audio.replaceCurrentItem(with:AVPlayerItem(url:URL(fileURLWithPath:own.reference)));editor.audio.play()}}
            }
            Text(own.reference.isEmpty ? "未設定；使用原裝角色錄音":URL(fileURLWithPath:own.reference).lastPathComponent).font(.caption).foregroundStyle(.secondary)
            TextField(L("錄音逐字原文（按錄音實際語言）"),text:Binding(get:{own.promptText},set:{text in update {$0.promptText=text}}),axis:.vertical).textFieldStyle(.roundedBorder)
            Toggle(L("使用呢個引擎嘅獨立語言參考"),isOn:Binding(get:{own.enabled},set:{enabled in update {$0.enabled=enabled}})).disabled(!own.ready && !own.enabled)
            Text(L("可用自己準備嘅乾淨廣東話／英文錄音改善跨語言效果。唔會自動由其他 TTS 引擎生成；聲線身份同口音仍需試聽。")).font(.caption).foregroundStyle(.secondary)
        }
    }
    func importAudio() {
        let panel=NSOpenPanel();panel.allowedContentTypes=[.wav]
        guard panel.runModal() == .OK,let source=panel.url,let document=editor.document else{return}
        do {
            let audio=try AVAudioFile(forReading:source);let seconds=Double(audio.length)/audio.processingFormat.sampleRate
            guard seconds.isFinite,seconds>=3,seconds<=10.1 else {throw AppFailure(message:"參考錄音需要 3–10 秒。")}
            let data=try Data(contentsOf:source);let hash=SHA256.hash(data:data).map{String(format:"%02x",$0)}.joined()
            let folder=URL(fileURLWithPath:document.review).deletingLastPathComponent().appendingPathComponent("independent-user-references")
            try FileManager.default.createDirectory(at:folder,withIntermediateDirectories:true)
            let target=folder.appendingPathComponent(hash+".wav")
            if !FileManager.default.fileExists(atPath:target.path) {try data.write(to:target,options:.atomic)}
            update {$0.reference=target.path;$0.enabled=false;$0.language=options.referenceLanguage;$0.promptText=""}
        } catch {editor.error=error.localizedDescription}
    }
}

extension AppModel {
    func prepareEnglishForAudition() {
        guard !busy,let doc=projectEditor.document,let segment=projectEditor.selectedSegment,let i=projectEditor.segmentIndex,(doc.segments[i].english ?? "").trimmingCharacters(in:.whitespacesAndNewlines).isEmpty else{return}
        let count=editorTasks.count
        submitEditor(previewOnly:true,audioSettings:["previewScriptOnly":true,"pauseAfterVoiceRegeneration":true],startImmediately:false)
        guard editorTasks.count>count,let task=editorTasks.last else{return}
        projectEditor.pendingEnglishScript=(task.id,doc.review,segment)
        editorTasks.removeLast();editorTasks.insert(task,at:0);saveEditorQueue();queuePaused=false;pumpEditorQueue()
    }
    func compareCantoneseAuditions() {
        guard !busy,let doc=projectEditor.document,let segment=projectEditor.selectedSegment else{return}
        var settings=workspaceOptions.inferenceSettings
        let candidates:[[String:Any]]=[
            ["label":"A","engine":workspaceOptions.comparisonEngineA,"parameters":workspaceOptions.comparisonParametersA ?? workspaceOptions.inferenceSettings],
            ["label":"B","engine":workspaceOptions.comparisonEngineB,"parameters":workspaceOptions.comparisonParametersB ?? workspaceOptions.inferenceSettings]]
        guard candidates.allSatisfy({engineReady($0["engine"] as? String ?? "")}) else{error="請先部署 A／B 所選模型。";return}
        settings.merge(["comparisonCandidates":candidates,"targetLanguage":projectEditor.previewLanguage,"voiceSamplesOnly":true,"singleCueComparison":true,"pauseAfterVoiceRegeneration":true,"audioRerunToken":UUID().uuidString]) {_,new in new}
        let count=editorTasks.count;submitEditor(previewOnly:true,audioSettings:settings,startImmediately:false)
        guard editorTasks.count>count,let task=editorTasks.last else{return}
        projectEditor.pendingVoiceComparison=(task.id,doc.review,segment)
        editorTasks.removeLast();editorTasks.insert(task,at:0);saveEditorQueue();queuePaused=false;pumpEditorQueue()
    }
}
