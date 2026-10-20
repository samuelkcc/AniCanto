import SwiftUI
import AVKit
import CryptoKit

struct HistoricalRecording:Identifiable,Equatable {
    var id:String,path:String,engine:String,language:String,text:String,reason:String
    var index:Int,created:Double,start:Double?,end:Double?,editorID:String?
    var length:Double?
    var sourceAudio:String=""
    var sourceMTime:Double=0
    var spokenText:String=""
    var partialSequence:Bool=false
    var isFragment:Bool {
        let requested=spokenText.filter {$0.isLetter || $0.isNumber}
        let approved=text.filter {$0.isLetter || $0.isNumber}
        return partialSequence || (!requested.isEmpty && requested != approved && approved.contains(requested))
    }
}

/// Only known project/version/track folders are read, on a background task.
/// Legacy rejected files remain discoverable without rewriting a running job.
enum RecordingHistoryReader {
    static func partialSequence(_ generation:[String:Any])->Bool {
        guard let total=generation["plannedParts"] as? Int,let parts=generation["parts"] as? [[String:Any]] else{return false}
        return parts.count<total
    }
    static func folders(_ root:URL)->[URL] {
        func directories(_ parent:URL)->[URL] {
            ((try? FileManager.default.contentsOfDirectory(at:parent,includingPropertiesForKeys:[.isDirectoryKey],options:.skipsHiddenFiles)) ?? []).filter {(try? $0.resourceValues(forKeys:[.isDirectoryKey]).isDirectory)==true}
        }
        let bases=[root]+directories(root.appendingPathComponent("versions"))
        let attempts=bases.flatMap {base in directories(base.appendingPathComponent("ai-result-repair")).flatMap {directories($0)}}
        return bases+bases.flatMap {directories($0.appendingPathComponent("tracks"))}+attempts
    }
    static func load(root:URL,engine:String,language:String,index:Int,segmentID:String?)->[HistoricalRecording] {
        let root=root.resolvingSymlinksInPath()
        func safe(_ path:URL)->Bool {path.resolvingSymlinksInPath().path.hasPrefix(root.path+"/")}
        func matches(_ row:[String:Any])->Bool {
            if let id=row["editorID"] as? String,let segmentID {return id==segmentID}
            return row["index"] as? Int==index
        }
        var result:[HistoricalRecording]=[]
        for folder in folders(root) where safe(folder) || folder==root {
            let archive=folder.appendingPathComponent("recording-history")
            let entries=(try? FileManager.default.contentsOfDirectory(at:archive,includingPropertiesForKeys:nil,options:.skipsHiddenFiles)) ?? []
            for entry in entries where safe(entry) {
                let row=ProcessingAudioIndex.read(entry.appendingPathComponent("take.json"))
                guard row["engine"] as? String==engine,row["language"] as? String==language,matches(row),let id=row["id"] as? String,let name=row["audio"] as? String else{continue}
                let audio=entry.appendingPathComponent(name).resolvingSymlinksInPath()
                guard safe(audio),audio.deletingLastPathComponent()==entry.resolvingSymlinksInPath(),FileManager.default.fileExists(atPath:audio.path) else{continue}
                result.append(HistoricalRecording(id:id,path:audio.path,engine:engine,language:language,text:row["text"] as? String ?? "",reason:row["reason"] as? String ?? "",index:row["index"] as? Int ?? index,created:row["created"] as? Double ?? 0,start:row["start"] as? Double,end:row["end"] as? Double,editorID:row["editorID"] as? String,length:ProcessingAudioIndex.length(audio.path,diagnostic:true),sourceAudio:row["sourceAudio"] as? String ?? "",sourceMTime:row["sourceMTime"] as? Double ?? 0,spokenText:row["spokenText"] as? String ?? "",partialSequence:partialSequence(row["generation"] as? [String:Any] ?? [:])))
            }
            let review=ProcessingAudioIndex.read(folder.appendingPathComponent("review.json"))
            let cfg=review["config"] as? [String:Any] ?? [:]
            let actualEngine=cfg["ttsBackend"] as? String ?? ""
            guard actualEngine==engine,(cfg["targetLanguage"] as? String ?? "yue")==language else{continue}
            let script=engine=="drama3" ? "drama3":engine=="cosyvoice3" ? "cosy":engine=="gpt-sovits" || engine=="gpt-sovits-v2" ? "tts":engine
            let request=ProcessingAudioIndex.read(folder.appendingPathComponent(script+"-request.json"))
            let cues=review["cues"] as? [[String:Any]] ?? []
            for item in request["items"] as? [[String:Any]] ?? [] {
                guard let position=item["reviewIndex"] as? Int,position>=0,let output=item["output"] as? String else{continue}
                guard let cue=cues.enumerated().first(where:{($0.element["reviewIndex"] as? Int ?? $0.offset)==position})?.element else{continue}
                if let id=cue["editorID"] as? String,let segmentID {if id != segmentID {continue}}
                else if position+1 != index {continue}
                let path=URL(fileURLWithPath:output)
                let failure=ProcessingAudioIndex.read(path.deletingPathExtension().appendingPathExtension("failure.json"))
                let generation=ProcessingAudioIndex.read(path.deletingPathExtension().appendingPathExtension("generation.json"))
                let reason=failure["error"] as? String ?? (generation["status"] as? String=="generation-limit" ? "generation-limit":"")
                guard !reason.isEmpty || !FileManager.default.fileExists(atPath:output) else{continue}
                let candidates=["rejected.raw.wav","raw.wav","rejected.wav"].map {path.deletingPathExtension().appendingPathExtension($0)}
                guard let audio=candidates.first(where:{safe($0) && FileManager.default.fileExists(atPath:$0.path)}),let attrs=try? FileManager.default.attributesOfItem(atPath:audio.path),let date=attrs[.modificationDate] as? Date else{continue}
                if result.contains(where:{$0.sourceAudio==audio.path && abs($0.sourceMTime-date.timeIntervalSince1970)<0.001}) {continue}
                result.append(HistoricalRecording(id:"legacy:"+audio.path+String(date.timeIntervalSince1970),path:audio.path,engine:engine,language:language,text:item["approvedText"] as? String ?? item["text"] as? String ?? "",reason:reason.isEmpty ? L("原始生成錄音未通過檢查"):reason,index:position+1,created:date.timeIntervalSince1970,start:cue["start"] as? Double,end:cue["end"] as? Double,editorID:cue["editorID"] as? String,length:ProcessingAudioIndex.length(audio.path,diagnostic:true),spokenText:item["text"] as? String ?? "",partialSequence:partialSequence(generation)))
            }
        }
        var ids=Set<String>()
        return result.filter {ids.insert($0.id).inserted}.sorted {$0.created>$1.created}
    }
}

@MainActor final class RecordingHistoryLoader:ObservableObject {
    @Published var rows:[HistoricalRecording]=[]
    @Published var loading=false
    @Published var expanded=false
    @Published var limit=20
    private var revision=UUID()
    func load(root:URL,engine:String,language:String,index:Int,segmentID:String?) async {
        let token=UUID();revision=token;loading=true
        let found=await Task.detached(priority:.utility) {RecordingHistoryReader.load(root:root,engine:engine,language:language,index:index,segmentID:segmentID)}.value
        guard !Task.isCancelled,revision==token else{return}
        if rows != found {rows=found};loading=false
    }
}

struct RecordingHistoryPanel:View {
    @ObservedObject var editor:ProjectEditor
    @ObservedObject var model:AppModel
    var engine:String,language:String,index:Int
    @StateObject private var history=RecordingHistoryLoader()
    var root:URL? {editor.document.map {URL(fileURLWithPath:$0.review).deletingLastPathComponent()}}
    var segment:EditSegment? {editor.document?.segments.first {$0.sources.contains(index-1)}}
    var identity:String {(root?.path ?? "")+engine+language+String(index)+editor.versions.prefix(3).map(\.id).joined()}
    var body:some View {
        VStack(alignment:.leading,spacing:8) {
            if let first=history.rows.first {
                Text(L("失敗錄音已保留，未自動採用")).font(.caption).foregroundStyle(.secondary)
                recording(first,latest:true)
                if history.rows.count>1 {
                    DisclosureGroup(L("先前失敗版本")+" (\(history.rows.count-1))",isExpanded:$history.expanded) {
                        ForEach(Array(history.rows.dropFirst().prefix(history.limit))) {row in recording(row,latest:false)}
                        if history.rows.count>history.limit+1 {Button(L("顯示更多")) {history.limit+=20}}
                    }
                }
                HStack {Spacer();Button {Task {await reload()}} label:{Label(L("重新整理錄音歷史"),systemImage:"arrow.clockwise")}.font(.caption)}
            } else if history.loading {ProgressView().controlSize(.small)}
        }.task(id:identity) {await reload()}
    }
    @ViewBuilder func recording(_ row:HistoricalRecording,latest:Bool)->some View {
        HStack(alignment:.top,spacing:16) {
          VStack(alignment:.leading,spacing:5) {
            HStack(spacing:8) {
                Text(L(latest ? "最近未採用錄音":"未採用錄音")).font(.caption.weight(.semibold))
                Text(Date(timeIntervalSince1970:row.created).formatted(date:.abbreviated,time:.shortened)).font(.caption).foregroundStyle(.secondary)
                if let length=row.length {Text(studioTimecode(length)).font(.caption.monospacedDigit())}
                Spacer()
            }
            if row.isFragment {
                Text(L("分段試音，並非完整對白")+" · "+row.spokenText).font(.caption).foregroundStyle(.orange).textSelection(.enabled)
            }
            if !row.reason.isEmpty {Text(row.reason).font(.caption).foregroundStyle(.secondary).lineLimit(3).textSelection(.enabled)}
            if let segment,let length=row.length,length>segment.end-segment.start+0.05 {Text(L("錄音較原時段長，匯出時仍須按原時限調整。請先聽完整段。")).font(.caption).foregroundStyle(.orange)}
            if let segment,row.text != (language=="en" ? segment.english ?? "":segment.text) {Text(L("台詞已改動；此版本只供比較，未套用至新台詞。")).font(.caption).foregroundStyle(.secondary)}
          }.frame(maxWidth:.infinity,alignment:.leading)
          VStack(alignment:.trailing,spacing:6) {
                Button {editor.playHistoricalRecording(row)} label:{Label(L("試聽失敗錄音"),systemImage:"play.fill")}.disabled(row.length==nil)
                Button {editor.adoptHistoricalRecording(row)} label:{Label(L("接受並採用此版本"),systemImage:"checkmark.circle")}
                    .disabled(model.busy || editor.readOnlyPreview || !canAdopt(row))
          }.fixedSize(horizontal:true,vertical:false)
        }.padding(10).background(Color.primary.opacity(0.025),in:RoundedRectangle(cornerRadius:6))
    }
    private func canAdopt(_ row:HistoricalRecording)->Bool {
        guard row.length != nil,!row.isFragment,let segment else{return false}
        return row.text==(language=="en" ? segment.english ?? "":segment.text) && abs((row.start ?? -1)-segment.start)<0.001 && abs((row.end ?? -1)-segment.end)<0.001
    }
    private func reload() async {
        if let root {await history.load(root:root,engine:engine,language:language,index:index,segmentID:segment?.id)}
    }
}

extension ProjectEditor {
    func playHistoricalRecording(_ row:HistoricalRecording) {
        guard let root=document.map({URL(fileURLWithPath:$0.review).deletingLastPathComponent().resolvingSymlinksInPath()}),URL(fileURLWithPath:row.path).resolvingSymlinksInPath().path.hasPrefix(root.path+"/"),ProcessingAudioIndex.length(row.path,diagnostic:true) != nil else{return}
        player.pause();audio.pause();clearAuditionStop()
        audio.replaceCurrentItem(with:AVPlayerItem(url:URL(fileURLWithPath:row.path)));audio.play()
        auditionLabel=L("正在播放未採用錄音")+" · "+(VoiceEngineChoice.all.first {$0.id==row.engine}?.shortTitle ?? row.engine)
    }
    func adoptHistoricalRecording(_ row:HistoricalRecording) {
        guard !readOnlyPreview,!row.isFragment,let doc=document,let selected=doc.segments.first(where:{row.editorID != nil ? $0.id==row.editorID:$0.sources.contains(row.index-1)}),ProcessingAudioIndex.length(row.path,diagnostic:true) != nil,row.text==(row.language=="en" ? selected.english ?? "":selected.text),abs((row.start ?? -1)-selected.start)<0.001,abs((row.end ?? -1)-selected.end)<0.001 else{return}
        let root=URL(fileURLWithPath:doc.review).deletingLastPathComponent().resolvingSymlinksInPath()
        guard URL(fileURLWithPath:row.path).resolvingSymlinksInPath().path.hasPrefix(root.path+"/") else{return}
        do {
            let folder=root.appendingPathComponent("accepted-recordings").appendingPathComponent(UUID().uuidString)
            try FileManager.default.createDirectory(at:folder,withIntermediateDirectories:true)
            let audio=folder.appendingPathComponent("audio.wav")
            try FileManager.default.copyItem(at:URL(fileURLWithPath:row.path),to:audio)
            guard let length=ProcessingAudioIndex.length(audio.path,diagnostic:true) else{throw AppFailure(message:L("未能讀取錄音。"))}
            let digest=SHA256.hash(data:try Data(contentsOf:audio)).map {String(format:"%02x",$0)}.joined()
            let acceptance:[String:Any]=["historyID":row.id,"acceptedByUser":true,"acceptedAt":Date().timeIntervalSince1970,"engine":row.engine,"language":row.language,"text":row.text,"reason":row.reason,"audioSHA256":digest,"source":row.path]
            try JSONSerialization.data(withJSONObject:acceptance,options:.sortedKeys).write(to:folder.appendingPathComponent("acceptance.json"),options:.atomic)
            let provenance:[String:Any]=["config":["ttsBackend":row.engine,"targetLanguage":row.language,"gsvVersion":row.engine=="gpt-sovits-v2" ? "v2ProPlus":"v4"]]
            try JSONSerialization.data(withJSONObject:provenance).write(to:folder.appendingPathComponent("review.json"),options:.atomic)
            selectedSegment=selected.id;previewEngine=row.engine;previewLanguage=row.language
            updateSegment {$0.audioTake=audio.path;$0.audioLength=length;$0.audioAcceptedHistoryID=row.id;$0.rate=1;$0.trimStart=0;$0.trimEnd=0}
            invalidateTakes()
            var adopted=row;adopted.path=audio.path;playHistoricalRecording(adopted)
            auditionLabel=L("已由用戶接受此錄音；原失敗原因仍保留")
        } catch {self.error=error.localizedDescription}
    }
}
