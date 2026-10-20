import SwiftUI
import AVKit

struct ProcessingVoiceTake:Identifiable,Equatable {
    let engine:String,language:String,path:String,text:String,speakerID:String
    let start:Double,end:Double,length:Double
    var editorID:String?=nil
    // Match the frozen request, not an automatic repair attempt's random seed.
    var seed=42
    var rate=1.0
    var trimStart=0.0
    var trimEnd=0.0
    var modelVersion:String?=nil
    var id:String {engine+":"+language+":"+String(start)+":"+path}
}

/// The preview manifest names the final WAV before synthesis starts. Only a
/// completed final file is playable; no report or entire-track completion needed.
enum ProcessingAudioIndex {
    private static let cacheLock=NSLock()
    private static let scanQueue=DispatchQueue(label:"AniCanto.preview-audio",qos:.utility)
    private static var snapshots:[String:[ProcessingVoiceTake]]=[:]
    private static var scanning=Set<String>()
    /// One background scan at a time per source; UI ticks reuse the last snapshot.
    @MainActor static func request(_ root:URL,video:String,complete:@escaping ([ProcessingVoiceTake])->Void) {
        let key=root.path+"\n"+video
        cacheLock.lock();let previous=snapshots[key] ?? [];let start=scanning.insert(key).inserted;cacheLock.unlock()
        complete(previous)
        guard start else{return}
        scanQueue.async {
            let result=scan(root,video:video)
            cacheLock.lock();snapshots[key]=result;scanning.remove(key);cacheLock.unlock()
            DispatchQueue.main.async {complete(result)}
        }
    }
    private static var lengths:[String:(UInt64,Date,Double)]=[:]
    static func length(_ path:String,diagnostic:Bool=false)->Double? {
        let name=URL(fileURLWithPath:path).lastPathComponent
        guard name.hasSuffix(".wav"),!name.hasPrefix("skipped-"),(diagnostic || ![".partial.",".raw.",".rejected."].contains(where:name.contains)),
              let attr=try? FileManager.default.attributesOfItem(atPath:path),let size=attr[.size] as? UInt64,size>44,let date=attr[.modificationDate] as? Date else{return nil}
        cacheLock.lock();let saved=lengths[path];cacheLock.unlock()
        if let saved,saved.0==size,saved.1==date {return saved.2}
        guard let file=try? AVAudioFile(forReading:URL(fileURLWithPath:path)),file.length>0,file.fileFormat.sampleRate>0 else{return nil}
        let seconds=Double(file.length)/file.fileFormat.sampleRate
        guard seconds.isFinite,seconds>0 else{return nil}
        cacheLock.lock();if lengths.count>8000 {lengths.removeAll()};lengths[path]=(size,date,seconds);cacheLock.unlock();return seconds
    }
    private static var jsonCache:[String:(UInt64,Date,[String:Any])]=[:]
    static func read(_ url:URL)->[String:Any] {
        guard let attr=try? FileManager.default.attributesOfItem(atPath:url.path),let size=attr[.size] as? UInt64,let date=attr[.modificationDate] as? Date else{return [:]}
        cacheLock.lock();let saved=jsonCache[url.path];cacheLock.unlock()
        if let saved,saved.0==size,saved.1==date {return saved.2}
        let row=(try? Data(contentsOf:url)).flatMap {try? JSONSerialization.jsonObject(with:$0) as? [String:Any]} ?? [:]
        cacheLock.lock();if jsonCache.count>4096 {jsonCache.removeAll()};jsonCache[url.path]=(size,date,row);cacheLock.unlock();return row
    }
    static func scan(_ root:URL,video:String)->[ProcessingVoiceTake] {
        let fm=FileManager.default
        let versions=((try? fm.contentsOfDirectory(at:root.appendingPathComponent("versions"),includingPropertiesForKeys:nil)) ?? []).filter {
            ["running","complete","partial","preview","audition-review","failed"].contains(read($0.appendingPathComponent("version.json"))["status"] as? String ?? "")
        }.sorted { (read($0.appendingPathComponent("version.json"))["created"] as? String ?? "") > (read($1.appendingPathComponent("version.json"))["created"] as? String ?? "") }
        var folders:[URL]=[]
        for parent in versions+[root] {
            folders.append(parent)
            let progress=read(parent.appendingPathComponent("track-progress.json"))["tracks"] as? [[String:Any]] ?? []
            folders += progress.compactMap {($0["folder"] as? String).map {URL(fileURLWithPath:$0)}}
            folders += (try? fm.contentsOfDirectory(at:parent.appendingPathComponent("tracks"),includingPropertiesForKeys:nil)) ?? []
        }
        var visited=Set<String>(),keys=Set<String>(),result:[ProcessingVoiceTake]=[]
        var projectRoot=root
        if root.deletingLastPathComponent().lastPathComponent=="versions" {projectRoot=root.deletingLastPathComponent().deletingLastPathComponent()}
        else if root.deletingLastPathComponent().lastPathComponent=="tracks" {projectRoot=root.deletingLastPathComponent().deletingLastPathComponent();if projectRoot.deletingLastPathComponent().lastPathComponent=="versions" {projectRoot=projectRoot.deletingLastPathComponent().deletingLastPathComponent()}}
        let allowed=projectRoot.resolvingSymlinksInPath().path+"/"
        for folder in folders where visited.insert(folder.path).inserted {
            let review=read(folder.appendingPathComponent("review.json")),cfg=review["config"] as? [String:Any] ?? [:]
            guard cfg["video"] as? String==video else{continue}
            let manifest=read(folder.appendingPathComponent("audio-preview.json"))
            guard let engine=manifest["engine"] as? String ?? cfg["ttsBackend"] as? String,let language=manifest["language"] as? String ?? cfg["targetLanguage"] as? String,VoiceEngineChoice.all.contains(where:{$0.id==engine && $0.languages.contains(language)}) else{continue}
            let cues=review["cues"] as? [[String:Any]] ?? []
            let submitted=Dictionary(((review["cues"] as? [[String:Any]]) ?? []).compactMap {cue -> (String,[String:Any])? in
                guard let id=cue["editorID"] as? String else{return nil};return (id,cue)
            },uniquingKeysWith:{first,_ in first})
            let report=read(folder.appendingPathComponent("report.json"))
            let timing=(try? Data(contentsOf:folder.appendingPathComponent("timing.json"))).flatMap {try? JSONSerialization.jsonObject(with:$0) as? [[String:Any]]} ?? []
            // Both interfaces audition the delivered take first: an accepted
            // fallback, then post-tempo PCM, then a completed in-progress take.
            let delivered=((report["audioFallbacks"] as? [[String:Any]] ?? [])+timing).compactMap {row -> [String:Any]? in
                guard row["skipped"] as? Bool != true,let audio=row["renderedAudio"] as? String ?? row["audio"] as? String,
                      let cue=cues.first(where:{abs(($0["start"] as? Double ?? -1)-(row["start"] as? Double ?? -2))<0.001 && abs(($0["end"] as? Double ?? -1)-(row["end"] as? Double ?? -2))<0.001}),
                      let text=row["text"] as? String,text==cue["cantonese"] as? String else{return nil}
                var result=cue;result["audio"]=audio;result["cantonese"]=text
                result["_seed"]=cue["_seed"] as? Int ?? 42
                return result
            }
            for row in delivered+((manifest["rows"] as? [[String:Any]] ?? []).reversed()) {
                guard let start=row["start"] as? Double,let end=row["end"] as? Double,start.isFinite,end.isFinite,end>start,
                      let path=row["audio"] as? String else{continue}
                let key=engine+":"+language+":"+String(start)+":"+String(end)
                guard !keys.contains(key),URL(fileURLWithPath:path).resolvingSymlinksInPath().path.hasPrefix(allowed),let length=length(path) else{continue}
                keys.insert(key)
                let frozen=(row["editorID"] as? String).flatMap {submitted[$0]}
                let sameCue=abs((frozen?["start"] as? Double ?? -1)-start)<0.001 && abs((frozen?["end"] as? Double ?? -1)-end)<0.001
                let requestedSeed=sameCue ? frozen?["_seed"] as? Int:nil
                result.append(ProcessingVoiceTake(engine:engine,language:language,path:path,text:row["cantonese"] as? String ?? "",speakerID:row["speakerId"] as? String ?? "",start:start,end:end,length:length,editorID:row["editorID"] as? String,seed:requestedSeed ?? row["_seed"] as? Int ?? 42,rate:row["editorRate"] as? Double ?? 1,trimStart:row["editorTrimStart"] as? Double ?? 0,trimEnd:row["editorTrimEnd"] as? Double ?? 0,modelVersion:row["modelVersion"] as? String ?? cfg["gsvVersion"] as? String))
            }
        }
        return result
    }
}

struct ProcessingCueVoicePlaybackMatrix:View {
    @ObservedObject var editor:ProjectEditor
    @ObservedObject var live:LiveVideoPreview
    var languages:[String]=["yue"]
    var body:some View {
        VStack(alignment:.leading,spacing:6) {
            HStack {Text(L("試聽")).font(.caption.bold()).frame(width:64,alignment:.leading);ForEach(languages,id:\.self) {language in Text(L(language=="en" ? "英文":"廣東話")).font(.caption2).frame(width:language=="en" ? 42:64)}}
            ForEach(VoiceEngineChoice.all) {engine in
                HStack(spacing:6) {
                    Text(engine.shortTitle).font(.caption).frame(width:64,alignment:.leading)
                    ForEach(languages.filter {engine.languages.contains($0)},id:\.self) {language in
                        let take=live.take(engine.id,language:language)
                        Button {if let take {editor.selectVoiceTrack(engine.id,language:language);live.playTake(take)}} label:{Image(systemName:"play.fill").frame(width:language=="en" ? 42:64,height:28)}
                            .buttonStyle(.plain).foregroundStyle(accent).background(accent.opacity(take==nil ? 0.04:0.13),in:RoundedRectangle(cornerRadius:5))
                            .disabled(take==nil).help(L("播放已完成配音；轉換會繼續"))
                            .accessibilityLabel(engine.title+" · "+L(language=="en" ? "英文":"廣東話"))
                    }
                }
            }
        }.padding(8).background(accent.opacity(0.055),in:RoundedRectangle(cornerRadius:6)).fixedSize()
    }
}
