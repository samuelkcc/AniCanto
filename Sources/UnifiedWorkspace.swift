import SwiftUI
import AVKit

final class WorkspaceOptions: ObservableObject {
    @Published var showQueue=false
    @Published var viewMode="edit"
}
struct UnifiedWorkspace: View {
    @ObservedObject var model:AppModel
    @ObservedObject var editor:ProjectEditor
    @StateObject private var options=WorkspaceOptions()
    var body:some View {
        ProjectWorkspace(model:model,editor:editor)
            .onDrop(of:[.fileURL],isTargeted:nil) {providers in
                guard !model.busy else{return false}
                for provider in providers {_ = provider.loadObject(ofClass:URL.self) {url,_ in if let url {Task {@MainActor in model.addBatch([url])}}}}
                return true
            }
    }
}

struct LiveSubtitleCue:Equatable,Identifiable {
    let id:Int,start:Double,end:Double,original:String,cantonese:String,english:String
    var speakerID:String=""
    func text(_ language:String)->String {language=="en" ? english:cantonese}
}
@MainActor func usesProcessingPreview(_ model:AppModel,_ editor:ProjectEditor,_ live:LiveVideoPreview)->Bool {
    editor.document==nil || (model.activeEditorTask==nil && (model.hasBatchRequest(video:editor.selectedRow?.video) || (model.busy && live.processingVideo != nil && live.processingVideo==editor.selectedRow?.video)))
}
@MainActor final class LiveVideoPreview:ObservableObject {
    private let readSnapshot:(WorkspacePreviewInput)->WorkspacePreviewSnapshot
    init(snapshotReader:@escaping (WorkspacePreviewInput)->WorkspacePreviewSnapshot = WorkspacePreviewSnapshot.read) {readSnapshot=snapshotReader}
    let player=CantoPlayer()
    let audition=CantoPlayer()
    @Published var takes:[ProcessingVoiceTake]=[]
    @Published var auditionTake:ProcessingVoiceTake?
    @Published var captions:[PreviewCaption]=[]
    @Published var cues:[LiveSubtitleCue]=[]
    @Published var sourceCaptions:[PreviewCaption]=[]
    @Published var profiles:[VoiceProfile]=[]
    @Published var requestedLanguages:[String]?
    @Published var requestedEngines:[String]?
    @Published private(set) var processingVideo:String?
    @Published var seconds=0.0
    @Published var duration=1.0
    @Published var follow=true {didSet {if follow != oldValue {syncAudio();persistSession()}}}
    @Published private(set) var muted=true
    @Published private(set) var inspectionMuted=false
    private var audioSnapshotKey:String?
    private var processing=false
    @Published var readyCount=0
    @Published var error:String?
    private var current:String?
    private var sessionURL:URL?
    private(set) var savedSession:WorkspacePreviewSession?
    private var observer:Any?
    private var lastCueEnd = -1.0
    private var clipLength=0.0
    private var inspectionEnd:Double?
    private var deferredSeek:(video:String?,seconds:Double)?
    var offset=0.0
    private func syncAudio() {
        let quiet=(processing && follow) || inspectionMuted || auditionTake != nil
        if muted != quiet {muted=quiet}
        player.isMuted=quiet
    }
    func toggleAudio() {
        if processing && follow {follow=false;inspectionMuted=false}
        else {inspectionMuted.toggle()}
        syncAudio()

    }
    func resetForRemoval() {
        previewIO.invalidate();refreshGeneration += 1;refreshLoading=false;refreshInput=nil;audioSnapshotKey=nil;deferredSeek=nil
        stopInspection();player.pause();player.replaceCurrentItem(with:nil);current=nil;processingVideo=nil
        takes=[];cues=[];captions=[];sourceCaptions=[];profiles=[];requestedLanguages=nil;requestedEngines=nil
        seconds=0;duration=1;offset=0;lastCueEnd = -1
        savedSession=nil
        if let sessionURL {try? FileManager.default.removeItem(at:sessionURL)}
    }
    private let previewIO=PreviewCommandQueue(label:"AniCanto.preview-metadata",qos:.utility)
    private var refreshInput:WorkspacePreviewInput?
    private var refreshLoading=false
    private var refreshGeneration=0
    func refresh(_ model:AppModel,video:String?,preferredJob:String?=nil) {
        processing=model.busy;syncAudio()
        if refreshInput?.video != video {
            // Slow loading must never expose the previous episode's auditions
            // or captions under the newly selected video's name.
            audioSnapshotKey=nil;deferredSeek=nil;stopInspection();player.replaceCurrentItem(with:nil);current=nil
            takes=[];cues=[];captions=[];sourceCaptions=[];profiles=[];readyCount=0;processingVideo=nil
            seconds=savedSession?.video==video ? savedSession?.seconds ?? 0:0
        }
        // Frozen selections are cheap, immediately available and shared by
        // Basic/Expert. Disk-backed captions and profiles arrive asynchronously.
        if let submitted=model.submittedVoiceSelection(video:video) {
            if requestedLanguages != submitted.languages {requestedLanguages=submitted.languages}
            if requestedEngines != submitted.engines {requestedEngines=submitted.engines}
        }
        let selectedJob=model.projectEditor.selectedRow.flatMap {row in row.video==video ? (row.review?.deletingLastPathComponent().path ?? row.previewJob?.path):nil}
        let input=WorkspacePreviewInput(root:model.engine.root,video:video,preferredJob:preferredJob,selectedJob:selectedJob,
            activeJob:model.busy ? model.activePreviewJob:nil,restoredJob:savedSession?.video==video ? savedSession?.job:nil,
            sourceDuration:model.video?.path==video ? model.sourceDuration:0)
        if refreshLoading,refreshInput==input {return}
        refreshInput=input;refreshGeneration += 1
        let generation=refreshGeneration;refreshLoading=true
        let reader=readSnapshot
        previewIO.submit(key:"metadata") { [weak self,weak model] _ in
            let snapshot=reader(input)
            DispatchQueue.main.async {
                guard let self,let model,self.refreshGeneration==generation else{return}
                self.refreshLoading=false
                self.apply(snapshot,model:model,video:video)
            }
        }
    }
    private func apply(_ snapshot:WorkspacePreviewSnapshot,model:AppModel,video:String?) {
        processing=model.busy;processingVideo=nil
        let path=snapshot.path,jobPath=snapshot.job,activeVideo=snapshot.activeVideo,start=snapshot.start,length=snapshot.length
        var rows=snapshot.rows
        let nextSourceCaptions=snapshot.captions,nextProfiles=snapshot.profiles
        let submitted=model.submittedVoiceSelection(video:video)
        let nextLanguages=submitted?.languages ?? snapshot.config["dubLanguages"] as? [String]
        let nextEngines=submitted?.engines ?? snapshot.config["selectedEngines"] as? [String] ?? (snapshot.config["ttsBackend"] as? String).map {[$0]}
        if snapshot.matches {processingVideo=path}
        if let job=jobPath,let path {
            audioSnapshotKey=job+"\n"+path
            let key=audioSnapshotKey
            ProcessingAudioIndex.request(URL(fileURLWithPath:job),video:path) {[weak self] result in
                guard let self,self.audioSnapshotKey==key else{return}
                if self.takes != result {self.takes=result}
            }
        } else {audioSnapshotKey=nil;if !takes.isEmpty {takes=[]}}
        if sourceCaptions != nextSourceCaptions {sourceCaptions=nextSourceCaptions}
        if profiles != nextProfiles {profiles=nextProfiles}
        if requestedLanguages != nextLanguages {requestedLanguages=nextLanguages}
        if requestedEngines != nextEngines {requestedEngines=nextEngines}
        if let path,path != current,snapshot.sourceExists {
            player.pause();player.replaceCurrentItem(with:AVPlayerItem(url:URL(fileURLWithPath:path)));player.subtitles(ordinal:nil,external:nil)
            let pending=deferredSeek.flatMap {$0.video==video || $0.video==path ? $0.seconds:nil}
            let restored=pending ?? (savedSession?.video==path ? savedSession?.seconds ?? 0:0)
            deferredSeek=nil
            current=path;lastCueEnd = -1;offset=start;seconds=max(0,length>0 ? min(length,restored):restored);player.seek(to:CMTime(seconds:seconds+start,preferredTimescale:600));error=nil
            inspectionEnd=nil
            if observer==nil {observer=player.addPeriodicTimeObserver(forInterval:CMTime(seconds:0.1,preferredTimescale:600),queue:.main) {[weak self] time in Task {@MainActor in
                guard let self else{return}
                if !(self.processing && self.follow) {self.seconds=max(0,time.seconds-self.offset)}
                if let end=self.inspectionEnd,self.seconds>=end {self.player.pause();self.inspectionEnd=nil}
                let length=max(1,self.clipLength>0 ? self.clipLength:self.player.duration-self.offset)
                if self.duration != length {self.duration=length}
            }}}
        }
        clipLength=length;duration=max(1,length>0 ? length:player.duration-start);offset=start
        syncAudio()
        if !model.busy,let document=model.projectEditor.document,let job=jobPath,
           URL(fileURLWithPath:document.review).deletingLastPathComponent().path==job {
            requestedLanguages=model.workspaceVoiceSelection.languages
            requestedEngines=model.workspaceVoiceSelection.engines
            rows=document.segments.map {segment in
                var row:[String:Any]=["start":segment.start,"end":segment.end,"japanese":segment.original,
                    "cantonese":segment.text,"speakerId":segment.speakerId,"enabled":segment.enabled]
                if let english=segment.english {row["english"]=english}
                return row
            }
        }
        let next=rows.enumerated().compactMap {i,row -> LiveSubtitleCue? in
            guard let a=row["subtitleStart"] as? Double ?? row["start"] as? Double,let b=row["subtitleEnd"] as? Double ?? row["end"] as? Double,a.isFinite,b.isFinite,b>a else{return nil}
            return LiveSubtitleCue(id:i,start:a,end:b,original:row["japanese"] as? String ?? row["text"] as? String ?? "",cantonese:row["cantonese"] as? String ?? "",english:row["english"] as? String ?? "",speakerID:row["speakerId"] as? String ?? "")
        }
        if cues != next {cues=next}
        let nextCaptions=rows.compactMap {row -> PreviewCaption? in
            let translated=row["cantonese"] as? String ?? ""
            let text=translated
            guard row["enabled"] as? Bool != false else{return nil}
            guard !text.isEmpty,let a=row["start"] as? Double,let b=row["end"] as? Double else{return nil}
            return PreviewCaption(start:a+start,end:b+start,text:text)
        }
        if captions != nextCaptions {captions=nextCaptions}
        let nextReadyCount=rows.filter {!(($0["cantonese"] as? String ?? "").isEmpty)}.count
        if readyCount != nextReadyCount {readyCount=nextReadyCount}
        let activeCue=model.previewCueIndex.flatMap {i in
            if rows.contains(where:{$0["reviewIndex"] != nil}) {return rows.first(where:{$0["reviewIndex"] as? Int==i})}
            return rows.indices.contains(i) ? rows[i]:nil
        }
        if follow,model.busy,activeVideo==video,let cue=activeCue ?? (model.activeAudioTrack==nil && model.previewCueIndex==nil ? rows.last(where:{!(($0["cantonese"] as? String ?? "").isEmpty)}):nil),let a=cue["start"] as? Double,a != lastCueEnd {
            lastCueEnd=a;player.pause();seek(a)
        }
        persistSession(job:jobPath)
        if let failure=player.failure {error=failure}
    }
    func configurePersistence(root:URL) {
        sessionURL=root.appendingPathComponent("workspace-session.json")
        guard let data=try? Data(contentsOf:sessionURL!),let saved=try? JSONDecoder().decode(WorkspacePreviewSession.self,from:data),saved.seconds.isFinite,saved.seconds>=0 else{return}
        savedSession=saved;follow=saved.follow;seconds=saved.seconds
    }
    func persistSession(job:String?=nil) {
        guard let sessionURL,let target=deferredSeek?.video ?? current else{return}
        let previous=savedSession?.video==target ? savedSession:nil
        let pendingJob=refreshInput?.video==target ? refreshInput?.preferredJob ?? refreshInput?.selectedJob ?? refreshInput?.activeJob:nil
        let snapshot=WorkspacePreviewSession(video:target,job:job ?? pendingJob ?? previous?.job,seconds:deferredSeek?.seconds ?? seconds,follow:follow)
        guard seconds.isFinite,seconds>=0,snapshot != savedSession,let data=try? JSONEncoder().encode(snapshot) else{return}
        do {try data.write(to:sessionURL,options:.atomic);savedSession=snapshot}
        catch {self.error="無法保存預覽位置：\(error.localizedDescription)"}
    }
    func resumeFollowing(_ model:AppModel,video:String?) {stopAudition();inspectionEnd=nil;lastCueEnd = -1;if !follow {follow=true};refresh(model,video:video)}
    func seek(_ local:Double) {
        guard local.isFinite else{return}
        stopAudition();inspectionEnd=nil
        if refreshLoading,refreshInput?.video != current {deferredSeek=(refreshInput?.video,max(0,local));seconds=max(0,local);persistSession();return}
        player.seek(to:CMTime(seconds:local+offset,preferredTimescale:600));seconds=local;persistSession()
    }
    func playInterval(_ start:Double,_ end:Double) {
        guard start.isFinite,end.isFinite,end>start else{return}
        follow=false;inspectionMuted=false;syncAudio();seek(start);inspectionEnd=end;player.play()
    }
    func stopInspection() {stopAudition();inspectionEnd=nil;player.pause()}
    func stopAudition() {audition.pause();if auditionTake != nil {auditionTake=nil};syncAudio()}
    func take(_ engine:String,language:String)->ProcessingVoiceTake? {
        takes.first {$0.engine==engine && $0.language==language && $0.start<=seconds && seconds<$0.end}
    }
    func playTake(_ take:ProcessingVoiceTake) {
        guard ProcessingAudioIndex.length(take.path) != nil else{return}
        follow=false;seek(take.start);auditionTake=take;syncAudio();inspectionEnd=take.start+take.length;player.play()
        audition.replaceCurrentItem(with:AVPlayerItem(url:URL(fileURLWithPath:take.path)));audition.play()
    }
}
struct ProcessingVideoPreview:View {
    @ObservedObject var model:AppModel
    var video:String?
    var maximumHeight:Double?=nil
    var showsTimeline=false
    @StateObject private var preview=LiveVideoPreview()
    private let timer=Timer.publish(every:1,on:.main,in:.common).autoconnect()
    var body:some View {
        VStack(alignment:.leading,spacing:12) {
            HStack {Text(video.map {URL(fileURLWithPath:$0).lastPathComponent} ?? "加入影片開始製作").font(.title2.bold());Spacer();Button(action:preview.toggleAudio) {Label(L(preview.muted ? "開啟原聲":"靜音預覽"),systemImage:preview.muted ? "speaker.slash.fill":"speaker.wave.2.fill")}}
            AspectPlayerFrame(aspect:model.videoAspect,maxHeight:maximumHeight ?? max(400,min(650,model.availableHeight*0.62)),leftAligned:true) {
                if !model.busy,model.subtitleSource=="burned" {
                    OCRSelectionPlayer(player:preview.player,selecting:model.selectingOCR,region:$model.ocrRegion)
                } else {CaptionedPlayer(player:preview.player,captions:preview.captions,seconds:preview.seconds+preview.offset,bottomFraction:0.045,sizeFraction:0.043)}
            }
            HStack {
                Button(L("播放／暫停")) {preview.follow=false;if preview.player.rate==0 {preview.player.play()} else {preview.player.pause()}}
                Slider(value:Binding(get:{min(preview.duration,preview.seconds)},set:{preview.follow=false;preview.seek($0)}),in:0...preview.duration)
                Toggle(L("跟隨處理位置"),isOn:$preview.follow).toggleStyle(.checkbox)
            }
            if showsTimeline {
                Canvas {context,size in
                    let width=max(1,size.width-48)
                    context.draw(Text(L("原片")).font(.caption),at:CGPoint(x:20,y:14))
                    context.fill(Path(CGRect(x:48,y:6,width:width,height:16)),with:.color(accent.opacity(0.35)))
                    context.draw(Text(L("字幕")).font(.caption),at:CGPoint(x:20,y:43))
                    for cue in preview.captions {
                        let x=max(0,cue.start-preview.offset)/preview.duration*width
                        let length=max(2,(cue.end-cue.start)/preview.duration*width)
                        context.fill(Path(CGRect(x:48+x,y:34,width:length,height:16)),with:.color(accent))
                    }
                    let x=48+min(1,preview.seconds/preview.duration)*width
                    context.stroke(Path(CGRect(x:x,y:0,width:1,height:60)),with:.color(.red),lineWidth:1)
                }.frame(height:65)
            }
            if !model.busy,model.subtitleSource=="burned",let video {
                HStack {
                    if model.selectingOCR {
                        Button(L("重設方框")) {model.ocrRegion=OCRRegion()}
                        Button(L("完成並試讀")) {model.selectingOCR=false;model.video=URL(fileURLWithPath:video);model.playbackSeconds=preview.seconds+preview.offset;model.previewOCR()}
                    } else {Button(L("框選字幕範圍")) {preview.player.pause();model.selectingOCR=true}}
                    Text(model.selectingOCR ? "拖拉方框包住完整字幕，避開水印":"大型原片預覽；框選後可套用到全局或個別影片").font(.caption).foregroundStyle(.secondary)
                }
            }
            Text(model.busy ? "\(model.stage) · 已準備 \(preview.readyCount) 段字幕":"原片大型預覽 · 可先喺全局設定選擇處理範圍").font(.headline)
            if model.busy {Text(model.detail).font(.caption).foregroundStyle(.secondary)}
            if let error=preview.error {Text(error).foregroundStyle(.orange)}
            Spacer(minLength:0)
        }.onAppear {preview.refresh(model,video:video)}.onReceive(timer) {_ in preview.refresh(model,video:video)}.onDisappear {preview.player.pause()}
    }
}
