import SwiftUI
import AVKit
import CryptoKit

struct CueVoiceRecording {
    let path:String,length:Double,canAdopt:Bool,requiresReview:Bool,seed:Int
}
extension ProjectEditor {
    /// Auditions are owned by cue × engine × language, independent of another
    /// engine's random seed. Versions on disk remain the source of truth.
    func cueVoiceRecording(_ engine:String,language:String,segmentID:String?=nil)->CueVoiceRecording? {
        guard let document,let segment=document.segments.first(where:{$0.id==(segmentID ?? selectedSegment)}),let profile=profiles.first(where:{$0.id==segment.speakerId}) else{return nil}
        let key=engine+":"+language+":"+segment.id
        if let row=cueVoiceCache[key],FileManager.default.fileExists(atPath:row.path) {return row}
        if cueVoiceMisses.contains(key) {return nil}
        func json(_ url:URL)->[String:Any] {guard let bytes=try? Data(contentsOf:url) else{return [:]};return (try? JSONSerialization.jsonObject(with:bytes) as? [String:Any]) ?? [:]}
        let expected=language=="en" ? segment.english ?? "":segment.text
        guard !expected.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty else{return nil}
        let root=URL(fileURLWithPath:document.review).deletingLastPathComponent().resolvingSymlinksInPath()
        func recording(_ folder:URL,_ path:String,_ rejected:Bool)->CueVoiceRecording? {
            let review=json(folder.appendingPathComponent("review.json")),cfg=review["config"] as? [String:Any] ?? [:]
            guard engine != "gpt-sovits-v2" || cfg["gsvVersion"] as? String=="v2ProPlus" else{return nil}
            guard let cue=(review["cues"] as? [[String:Any]])?.first(where:{$0["editorID"] as? String==segment.id || (abs(($0["start"] as? Double ?? -1)-segment.start)<0.001 && abs(($0["end"] as? Double ?? -1)-segment.end)<0.001)}),cue["speakerId"] as? String==segment.speakerId else{return nil}
            let actual=language=="en" ? cue["english"] as? String ?? cue["cantonese"] as? String:cue["cantonese"] as? String
            guard actual==expected,abs((cue["start"] as? Double ?? -1)-segment.start)<0.001,abs((cue["end"] as? Double ?? -1)-segment.end)<0.001 else{return nil}
            let url=URL(fileURLWithPath:path).resolvingSymlinksInPath()
            guard url.path.hasPrefix(root.path+"/"),!url.lastPathComponent.hasPrefix("skipped-"),let length=Self.audioLength(path),length>0 else{return nil}
            let frozen=(cfg["voiceProfiles"] as? [[String:Any]])?.first {$0["id"] as? String==segment.speakerId}
            let owns=(frozen?["engineReferences"] as? [String:[String:Any]])?[engine+":"+language]
            let oldReference=owns?["enabled"] as? Bool==true ? owns?["reference"] as? String:frozen?["reference"] as? String
            let manifest=json(folder.appendingPathComponent("voice-reference-manifest.json"))
            let current=profile.referenceFor(engine,language)
            guard let bytes=try? Data(contentsOf:URL(fileURLWithPath:current)) else{return nil}
            let currentHash=SHA256.hash(data:bytes).map {String(format:"%02x",$0)}.joined()
            let oldHash=(manifest[profile.id] as? String) ?? oldReference.flatMap {try? Data(contentsOf:URL(fileURLWithPath:$0))}.map {SHA256.hash(data:$0).map {String(format:"%02x",$0)}.joined()}
            guard oldHash==currentHash else{return nil}
            let report=json(folder.appendingPathComponent("report.json")),check=report["speechCheck"] as? [String:Any] ?? [:]
            let blocked=CueVoiceReviewPolicy.blocked(check,language:language,rejected:rejected)
            return CueVoiceRecording(path:path,length:length,canAdopt:!blocked,requiresReview:blocked || check["requiresReview"] as? Bool==true,seed:cue["_seed"] as? Int ?? 42)
        }
        for version in versions {
            let meta=json(version.folder.appendingPathComponent("version.json"))
            if version.status=="voice-samples" {
                for row in json(version.folder.appendingPathComponent("voice-samples.json"))["rows"] as? [[String:Any]] ?? [] where row["engine"] as? String==engine && (row["language"] as? String ?? "yue")==language && row["editorID"] as? String==segment.id {
                    guard let path=row["audio"] as? String ?? row["diagnosticAudio"] as? String else{continue}
                    let folder=row["candidate"].flatMap {$0 as? String}.map {version.folder.appendingPathComponent("candidate-"+$0)} ?? version.folder
                    if let found=recording(folder,path,row["audio"]==nil) {cueVoiceCache[key]=found;return found}
                }
            } else if ["preview","audition-review"].contains(version.status),meta["engine"] as? String==engine,meta["language"] as? String==language,meta["segment"] as? String==segment.id,let path=meta["output"] as? String,
                      let found=recording(version.folder,path,version.status=="audition-review") {cueVoiceCache[key]=found;return found}
        }
        cueVoiceMisses.insert(key);return nil
    }
    /// Reanalysis owns new role IDs; diagnostic playback must not require
    /// adopting those roles into the editor. Bind by submitted cue ID and exact
    /// words/times/settings, while adoption continues to use engineTake.
    func versionPreviewTake(_ engine:String,language:String,segmentID:String?=nil)->ProcessingVoiceTake? {
        guard let segment=document?.segments.first(where:{$0.id==(segmentID ?? selectedSegment)}) else{return nil}
        let expected=language=="en" ? segment.english ?? "":segment.text
        guard !expected.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty else{return nil}
        return versionPreviewTakes.first {take in
            take.engine==engine && take.language==language && matchesVersionPreview(take,segment:segment)
        }
    }
    func playVersionPreview(_ take:ProcessingVoiceTake) {
        guard ProcessingAudioIndex.length(take.path) != nil else{return}
        previewEngine=take.engine;previewLanguage=take.language
        player.pause();audio.pause();clearAuditionStop()
        audio.replaceCurrentItem(with:AVPlayerItem(url:URL(fileURLWithPath:take.path)));audio.play()
        let changed=document?.segments.first(where:{$0.id==selectedSegment})?.speakerId != take.speakerID
        let engineTitle=take.engine.hasPrefix("gpt-sovits") ? "GPT-SoVITS "+gsvModelTitle(take.modelVersion ?? "v2"):(VoiceEngineChoice.all.first {$0.id==take.engine}?.title ?? take.engine)
        auditionLabel=L(changed ? "試聽新版人物配音（未採用）：":"正在播放：")+engineTitle+" · "+L(take.language=="en" ? "英文":"廣東話")
    }
    func cueVoiceAvailable(_ engine:String,language:String)->Bool {cueVoiceRecording(engine,language:language) != nil || deliveredTake(engine,language:language) != nil || versionPreviewTake(engine,language:language) != nil}
    func cuePlaybackPath(_ engine:String,language:String)->String? {
        cueVoiceRecording(engine,language:language)?.path ?? versionPreviewTake(engine,language:language)?.path ?? deliveredTake(engine,language:language)?.path
    }
    func playCueVoice(_ engine:String,language:String) {
        previewEngine=engine;previewLanguage=language
        if let saved=cueVoiceRecording(engine,language:language) {
            player.pause();audio.pause();clearAuditionStop()
            audio.replaceCurrentItem(with:AVPlayerItem(url:URL(fileURLWithPath:saved.path)));audio.play()
            auditionLabel=(saved.requiresReview ? L("試音待覆核："):L("正在播放："))+(VoiceEngineChoice.all.first {$0.id==engine}?.title ?? engine)+" · "+L(language=="en" ? "英文":"廣東話")
        } else if let preview=versionPreviewTake(engine,language:language) {
            playVersionPreview(preview)
        } else {previewLanguage=language;playEngine(engine)}
    }
    func prosodyExperiment()->[String:Any]? {
        guard let doc=document,let i=segmentIndex else{return nil}
        let s=doc.segments[i]
        for version in versions where version.status=="prosody-experiment" {
            guard let data=try? Data(contentsOf:version.folder.appendingPathComponent("prosody-experiment.json")),let row=try? JSONSerialization.jsonObject(with:data) as? [String:Any],row["segment"] as? String==s.id,row["speakerId"] as? String==s.speakerId,row["text"] as? String==s.text,abs((row["start"] as? Double ?? -1)-s.start)<0.001,abs((row["end"] as? Double ?? -1)-s.end)<0.001,let profile=profiles.first(where:{$0.id==s.speakerId}),let reference=try? Data(contentsOf:URL(fileURLWithPath:profile.reference)),row["roleReferenceSHA256"] as? String==SHA256.hash(data:reference).map({String(format:"%02x",$0)}).joined() else{continue}
            if let source=row["source"] as? String,let attributes=try? FileManager.default.attributesOfItem(atPath:source),let size=attributes[.size] as? NSNumber,size.int64Value==((row["sourceSize"] as? NSNumber)?.int64Value ?? -1),let date=attributes[.modificationDate] as? Date,abs(date.timeIntervalSince1970-Double((row["sourceMTime"] as? NSNumber)?.int64Value ?? 0)/1e9)<0.001 {return row}
        }
        return nil
    }
    func experimentPath(_ key:String)->String? {
        guard let doc=document,let path=prosodyExperiment()?[key] as? String else{return nil}
        let root=URL(fileURLWithPath:doc.review).deletingLastPathComponent().resolvingSymlinksInPath().path
        let url=URL(fileURLWithPath:path).resolvingSymlinksInPath()
        return url.path.hasPrefix(root+"/") && (Self.audioLength(path) ?? 0)>0 ? path:nil
    }
    func playProsodyExperiment(_ key:String) {
        guard let path=experimentPath(key) else{return}
        player.pause();audio.pause();clearAuditionStop()
        audio.replaceCurrentItem(with:AVPlayerItem(url:URL(fileURLWithPath:path)));audio.play()
        auditionLabel=L(key=="baseline" ? "正在播放：粵語基準":"正在播放：日文表演（實驗）")
    }
    func importAuditionEnglish() {
        guard !readOnlyPreview,var doc=document else{return}
        var changed=false
        for version in versions where ["preview","audition-review","voice-samples"].contains(version.status) {
            guard let data=try? Data(contentsOf:version.folder.appendingPathComponent("voice-samples.json")),let samples=try? JSONSerialization.jsonObject(with:data) as? [String:Any] else {
                guard let data=try? Data(contentsOf:version.folder.appendingPathComponent("review.json")),let review=try? JSONSerialization.jsonObject(with:data) as? [String:Any] else{continue}
                for cue in review["cues"] as? [[String:Any]] ?? [] {
                    guard let text=cue["english"] as? String,!text.isEmpty,let i=doc.segments.firstIndex(where:{$0.id==cue["editorID"] as? String && $0.speakerId==cue["speakerId"] as? String && abs($0.start-(cue["start"] as? Double ?? -1))<0.001 && abs($0.end-(cue["end"] as? Double ?? -1))<0.001}), (doc.segments[i].english ?? "").isEmpty else{continue}
                    doc.segments[i].english=text;changed=true
                }
                continue
            }
            for row in samples["rows"] as? [[String:Any]] ?? [] where row["language"] as? String=="en" {
                guard let text=row["text"] as? String,!text.isEmpty,let i=doc.segments.firstIndex(where:{$0.id==row["editorID"] as? String && $0.speakerId==row["role"] as? String && abs($0.start-(row["start"] as? Double ?? -1))<0.001}),(doc.segments[i].english ?? "").isEmpty else{continue}
                doc.segments[i].english=text;changed=true
            }
        }
        if changed {document=doc;dirty=true;scheduleSave()}
    }
}

extension AppModel {
    func generateProsodyExperiment() {
        let editor=projectEditor
        guard !busy,engineReady("gpt-sovits"),let doc=editor.document,let i=editor.segmentIndex,doc.segments[i].enabled else{return}
        editor.followPlaybackText=false;editor.player.pause();editor.audio.pause();editor.previewEngine="gpt-sovits"
        let count=editorTasks.count
        var settings=workspaceOptions.inferenceSettings
        settings.merge(["experimentalProsody":true,"prosodyStrength":0.65,"pauseAfterVoiceRegeneration":true,"previewNativeAudio":true,"audioRerunToken":UUID().uuidString,"voiceStyleMode":"clone"]) {_,new in new}
        let oldLanguage=editor.previewLanguage;editor.previewLanguage="yue"
        submitEditor(previewOnly:true,audioSettings:settings,startImmediately:false)
        editor.previewLanguage=oldLanguage
        guard editorTasks.count>count,let task=editorTasks.last,task.review==doc.review else{return}
        editorTasks.removeLast();editorTasks.insert(task,at:0);saveEditorQueue();queuePaused=false;pumpEditorQueue()
        editor.auditionLabel=L("正在生成：粵語讀音＋日文表演（實驗）")
    }
    func generateCueVoice(_ engineID:String,language:String) {
        let editor=projectEditor
        guard !busy,engineReady(engineID,language:language),let doc=editor.document,editor.selectedSegment != nil,let i=editor.segmentIndex,doc.segments[i].enabled else{return}
        editor.followPlaybackText=false;editor.player.pause();editor.audio.pause()
        editor.previewEngine=engineID
        let previous=editor.cueVoiceRecording(engineID,language:language)?.seed ?? doc.segments[i].take
        let count=editorTasks.count
        var settings=workspaceOptions.inferenceSettings
        settings.merge(["auditionMatrix":true,"auditionSeed":(previous+31)%2147483647,"pauseAfterVoiceRegeneration":true,"previewNativeAudio":true,"audioRerunToken":UUID().uuidString,"voiceStyleMode":"clone"]) {_,new in new}
        let oldLanguage=editor.previewLanguage;editor.previewLanguage=language
        submitEditor(previewOnly:true,audioSettings:settings,startImmediately:false)
        editor.previewLanguage=oldLanguage
        guard editorTasks.count>count,let task=editorTasks.last,task.review==doc.review else{return}
        editorTasks.removeLast();editorTasks.insert(task,at:0);saveEditorQueue();queuePaused=false;pumpEditorQueue()
        editor.auditionLabel=L("正在生成並保存：")+(VoiceEngineChoice.all.first {$0.id==engineID}?.title ?? engineID)+" · "+L(language=="en" ? "英文":"廣東話")
    }
}

struct CueVoiceGenerationMatrix:View {
    @ObservedObject var model:AppModel
    @ObservedObject var editor:ProjectEditor
    var body:some View {
        VStack(alignment:.leading,spacing:8) {
            Text(L("生成本段配音")).font(.headline)
            if let id=editor.selectedSegment,let gap=(editor.timelineMissingRegions[editor.previewEngine+":"+editor.previewLanguage] ?? []).first(where:{$0.segmentID==id}) {
                Label(L("缺聲原因：")+gap.reason,systemImage:"exclamationmark.triangle").font(.caption).foregroundStyle(.orange).textSelection(.enabled)
            }
            if let i=editor.segmentIndex,let s=editor.document?.segments[i] {
                Text("\(i+1) · "+studioTimecode(s.start)+" – "+studioTimecode(s.end)).font(.caption.monospacedDigit())
                Text(s.text).font(.caption).lineLimit(2)
            }
            ForEach(VoiceEngineChoice.all) {engine in
                HStack(spacing:6) {
                    Text(engine.shortTitle).frame(width:75,alignment:.leading)
                    ForEach(editor.availableDubLanguages.filter {engine.languages.contains($0)},id:\.self) {lang in
                        Button {model.generateCueVoice(engine.id,language:lang)} label:{Label(L(lang=="en" ? "英文":"廣東話"),systemImage:editor.cueVoiceAvailable(engine.id,language:lang) ? "arrow.clockwise":"waveform.badge.plus")}.frame(maxWidth:.infinity)
                        .help(L(editor.cueVoiceAvailable(engine.id,language:lang) ? "重新生成並保存":"生成並保存"))
                        .disabled(model.busy || !model.engineReady(engine.id,language:lang) || editor.segmentIndex==nil)
                    }
                }
            }
            Text(L("每段按引擎及語言獨立保存錄音；生成後在字幕面板播放。橙色錄音需要覆核，唔會自動採用。")).font(.caption).foregroundStyle(.secondary)
            if let error=editor.error {Text(error).font(.caption).foregroundStyle(.orange)}
        }
    }
}
struct CueVoicePlaybackMatrix:View {
    @ObservedObject var editor:ProjectEditor
    var body:some View {
        VStack(alignment:.leading,spacing:6) {
            HStack(spacing:6) {
                Text(L("試聽")).font(.caption.bold()).frame(width:64,alignment:.leading)
                ForEach(editor.availableDubLanguages,id:\.self) {lang in Text(L(lang=="en" ? "英文":"廣東話")).font(.caption2).frame(width:lang=="en" ? 42:64)}
            }
            ForEach(VoiceEngineChoice.all) {engine in
                HStack(spacing:6) {
                    Text(engine.shortTitle).font(.caption).lineLimit(1).frame(width:64,alignment:.leading)
                    ForEach(editor.availableDubLanguages.filter {engine.languages.contains($0)},id:\.self) {lang in
                        playbackButton(engine,language:lang)
                    }
                }
            }
        }.padding(8).background(accent.opacity(0.055),in:RoundedRectangle(cornerRadius:6))
        .fixedSize(horizontal:true,vertical:true)
    }
    private func playbackButton(_ engine:VoiceEngineChoice,language:String)->some View {
        let recording=editor.cueVoiceRecording(engine.id,language:language)
        let warning=recording?.requiresReview==true
        let available=editor.cueVoiceAvailable(engine.id,language:language)
        let preview=editor.versionPreviewTake(engine.id,language:language)
        let roleChanged=preview.map {$0.speakerID != editor.document?.segments.first(where:{$0.id==editor.selectedSegment})?.speakerId} ?? false
        let tint:Color=warning ? .orange:accent
        let title=engine.title+" · "+L(language=="en" ? "英文":"廣東話")
        return Button {editor.playCueVoice(engine.id,language:language)} label:{
            Image(systemName:warning ? "exclamationmark.triangle.fill":"play.fill").frame(width:language=="en" ? 42:64,height:28)
        }.buttonStyle(.plain)
            .background(tint.opacity(available ? 0.13:0.04),in:RoundedRectangle(cornerRadius:5))
            .foregroundStyle(tint)
            .help(title+" · "+L(roleChanged ? "新版人物配音，只作試聽；原稿角色設定保留":warning ? "需要試聽覆核":"播放已保存錄音"))
            .accessibilityLabel(title)
            .disabled(!available)
    }
}
