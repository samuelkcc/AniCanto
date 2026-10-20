import SwiftUI
import AVKit

/// Read original tracks with a separate engine so preview extraction cannot replace
/// or cancel the conversion engine's active worker. Times remain source-file times.
@MainActor final class MonitorSubtitles:ObservableObject {
    @Published var tracks:[SubtitleTrack]=[]
    @Published var selected:Set<Int>=[]
    @Published var captions:[Int:[PreviewCaption]]=[:]
    @Published var loading=false
    @Published var message=""
    private var request=UUID()
    private var identity=""
    private let extractor=Engine()
    func load(video:String?,external:String?,preferred:Int?) {
        let key=(video ?? "")+"|"+(external ?? "")+"|\(preferred ?? -1)"
        guard key != identity else{return}
        identity=key;request=UUID();let token=request
        tracks=[];selected=[];captions=[:];message="";loading=false
        guard let video else{return}
        loading=true
        let engine=extractor
        Task {
            do {
                let result=try await Task.detached {() throws -> ([SubtitleTrack],[Int:[PreviewCaption]]) in
                    if let external,FileManager.default.fileExists(atPath:external) {
                        let track=SubtitleTrack(id:-1,language:"",title:L("外掛字幕"),codec:"subrip")
                        return ([track],[-1:try engine.previewCaptions(source:URL(fileURLWithPath:external),stream:nil)])
                    }
                    let raw=try engine.run(engine.ffprobe,["-v","error","-select_streams","s","-show_streams","-of","json",video])
                    let obj=try JSONSerialization.jsonObject(with:Data(raw.utf8)) as? [String:Any]
                    let tracks=(obj?["streams"] as? [[String:Any]] ?? []).compactMap {row -> SubtitleTrack? in
                        guard let id=row["index"] as? Int else{return nil}
                        let tags=row["tags"] as? [String:String] ?? [:]
                        return SubtitleTrack(id:id,language:tags["language"] ?? "und",title:tags["title"] ?? "",codec:row["codec_name"] as? String ?? "")
                    }.filter(\.supported)
                    var rows:[Int:[PreviewCaption]]=[:]
                    for track in tracks {rows[track.id]=try engine.previewCaptions(source:URL(fileURLWithPath:video),stream:track.id)}
                    return (tracks,rows)
                }.value
                guard request==token else{return}
                tracks=result.0;captions=result.1;loading=false
                if let track=tracks.first(where:{$0.id==preferred}) ?? tracks.first(where:{["chi","zh","yue"].contains(where:$0.language.lowercased().hasPrefix)}) ?? tracks.first {selected=[track.id]}
                else {message="未有可選文字字幕軌；畫面原有字幕會保留"}
            } catch {
                guard request==token else{return}
                loading=false;message="原片字幕載入失敗"
            }
        }
    }
    func cancelAndClear() async {
        request=UUID();identity="";loading=false;tracks=[];selected=[];captions=[:];message=""
        let engine=extractor
        await Task.detached {engine.cancel()}.value
        engine.resetCancellation()
    }
    var visible:[PreviewCaption] {tracks.filter{selected.contains($0.id)}.flatMap{captions[$0.id] ?? []}.sorted{$0.start<$1.start}}
    func toggle(_ id:Int) {if selected.contains(id) {selected.remove(id)} else {selected.insert(id)}}
}
