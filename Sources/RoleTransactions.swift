import SwiftUI
import AppKit
import CryptoKit

struct PendingRoleChange: Codable, Equatable, Identifiable {
    var id:String
    var source:String
    var target:String
}

struct RoleDragPayload:Codable {
    var kind:String
    var id:String
    var review:String
    var text:String {String(data:(try? JSONEncoder().encode(self)) ?? Data(),encoding:.utf8) ?? ""}
    static func parse(_ text:String,review:String?)->RoleDragPayload? {
        guard let payload=try? JSONDecoder().decode(Self.self,from:Data(text.utf8)),
              ["role","line"].contains(payload.kind),!payload.id.isEmpty,payload.review==review else{return nil}
        return payload
    }
}

/// Dragging changes this proposal only. The editor is untouched until commit.
struct RoleAssignmentDraft:Codable {
    private(set) var changes:[String:PendingRoleChange]=[:]
    private(set) var history:[[String:PendingRoleChange]]=[]
    func role(for segment:EditSegment)->String {changes[segment.id]?.target ?? segment.speakerId}
    mutating func stage(_ target:String, segments:[EditSegment]) {
        var next=changes
        for s in segments {
            if s.speakerId==target {next.removeValue(forKey:s.id)}
            else {next[s.id]=PendingRoleChange(id:s.id,source:s.speakerId,target:target)}
        }
        guard next != changes else{return}
        history.append(changes);changes=next
    }
    mutating func undo() {if let prior=history.popLast(){changes=prior}}
    mutating func clear() {changes=[:];history=[]}
}

private struct RoleCommit:Codable {
    var before:[EditSegment]
    var changes:[PendingRoleChange]
}

extension ProjectEditor {
    private var roleHistoryURL:URL? {draftURL?.deletingLastPathComponent().appendingPathComponent("role-change-history.json")}
    private func roleHistory()->[RoleCommit] {
        guard let url=roleHistoryURL,let data=try? Data(contentsOf:url) else{return []}
        return (try? JSONDecoder().decode([RoleCommit].self,from:data)) ?? []
    }
    var canRestoreRoleCommit:Bool {
        guard let current=document,let last=roleHistory().last else{return false}
        return last.changes.allSatisfy {change in current.segments.contains(where:{$0.id==change.id && $0.speakerId==change.target})}
    }
    private func persistRoleMutation(_ journal:[RoleCommit],mutate:(inout EditDocument)->Void) throws {
        guard let url=roleHistoryURL else{return}
        let before=document,priorDirty=dirty,priorUndo=undoStack,priorRedo=redoStack
        let priorJournal=try? Data(contentsOf:url)
        try JSONEncoder().encode(journal).write(to:url,options:.atomic)
        do {update(mutate);try save()}
        catch {
            document=before;dirty=priorDirty;undoStack=priorUndo;redoStack=priorRedo
            // A partial filesystem/SQLite save must not leave roles changed in
            // memory or enqueue regeneration. Restore writable saved state too.
            try? save()
            if let priorJournal {try? priorJournal.write(to:url,options:.atomic)}
            else {try? FileManager.default.removeItem(at:url)}
            throw error
        }
    }
    func commitRoles(_ changes:[PendingRoleChange]) throws {
        guard !readOnlyPreview,let current=document,roleHistoryURL != nil else{return}
        let byID=Dictionary(uniqueKeysWithValues:current.segments.map{($0.id,$0)})
        guard !changes.isEmpty,Set(changes.map(\.id)).count==changes.count,
              changes.allSatisfy({change in byID[change.id]?.speakerId==change.source && profiles.contains(where:{$0.id==change.target})}) else {
            throw NSError(domain:"RoleCommit",code:1,userInfo:[NSLocalizedDescriptionKey:L("對白已修改，請取消待提交修改後重新配對。")])
        }
        var journal=roleHistory();journal.append(RoleCommit(before:changes.compactMap{byID[$0.id]},changes:changes))
        if journal.count>20 {journal.removeFirst(journal.count-20)}
        // Journal precedes the mutation, so a saved assignment remains reversible
        // after reopening. Every segment in this batch is one editor undo step.
        let targets=Dictionary(uniqueKeysWithValues:changes.map{($0.id,$0.target)})
        try persistRoleMutation(journal) {d in for i in d.segments.indices {
            guard let target=targets[d.segments[i].id] else{continue}
            d.segments[i].speakerId=target;d.segments[i].audioTake=nil;d.segments[i].audioLength=nil
            d.segments[i].preserveOriginalSpeech=false
            d.segments[i].trimStart=0;d.segments[i].trimEnd=0
        }}
    }
    func restoreRoleCommit() throws {
        guard !readOnlyPreview,let current=document,roleHistoryURL != nil else{return}
        var journal=roleHistory();guard let last=journal.last else{return}
        let targets=Dictionary(uniqueKeysWithValues:last.changes.map{($0.id,$0.target)})
        guard last.before.allSatisfy({old in current.segments.contains(where:{$0.id==old.id && $0.speakerId==targets[old.id]})}) else {
            throw NSError(domain:"RoleCommit",code:2,userInfo:[NSLocalizedDescriptionKey:L("角色配對已再次修改，請先撤銷較新修改。")])
        }
        let previous=Dictionary(uniqueKeysWithValues:last.before.map{($0.id,$0)})
        journal.removeLast()
        try persistRoleMutation(journal) {d in for i in d.segments.indices {
            guard let old=previous[d.segments[i].id] else{continue}
            let unchanged=d.segments[i].text==old.text && d.segments[i].english==old.english && d.segments[i].start==old.start && d.segments[i].end==old.end
            d.segments[i].speakerId=old.speakerId
            d.segments[i].audioTake=unchanged ? old.audioTake:nil
            d.segments[i].audioAcceptedHistoryID=unchanged ? old.audioAcceptedHistoryID:nil
            d.segments[i].audioLength=unchanged ? old.audioLength:nil
            if unchanged {d.segments[i].preserveOriginalSpeech=old.preserveOriginalSpeech}
            d.segments[i].trimStart=unchanged ? old.trimStart:0;d.segments[i].trimEnd=unchanged ? old.trimEnd:0
        }}
    }
}

/// Source frame thumbnails are evidence of the picture, never identified heads.
@MainActor final class RoleFrameThumbnails:ObservableObject {
    @Published private(set) var images:[String:NSImage]=[:]
    private var requested=Set<String>()
    private let queue:OperationQueue={let q=OperationQueue();q.maxConcurrentOperationCount=2;q.qualityOfService = .utility;return q}()
    func key(video:String,time:Double)->String {video+"@"+String(format:"%.3f",time)}
    func request(video:String,time:Double,ffmpeg:URL,folder:URL?) {
        let key=key(video:video,time:time)
        guard !requested.contains(key),!video.isEmpty,let folder else{return}
        requested.insert(key)
        let source=URL(fileURLWithPath:video),attrs=try? FileManager.default.attributesOfItem(atPath:video)
        let stamp="\(attrs?[.size] ?? 0)-\(attrs?[.modificationDate] ?? Date.distantPast)"
        let hash=SHA256.hash(data:Data((key+stamp).utf8)).map{String(format:"%02x",$0)}.joined()
        let cache=folder.appendingPathComponent("role-frame-thumbnails"),path=cache.appendingPathComponent(hash+".jpg")
        queue.addOperation { [weak self] in
            var bytes=try? Data(contentsOf:path)
            if bytes==nil,FileManager.default.fileExists(atPath:source.path) {
                let p=Process(),pipe=Pipe();p.executableURL=ffmpeg
                p.arguments=["-v","error","-threads","1","-ss",String(max(0,time)),"-i",video,"-frames:v","1","-vf","scale=240:-2","-f","image2pipe","-c:v","mjpeg","pipe:1"]
                p.standardOutput=pipe;p.standardError=FileHandle.nullDevice
                do {try p.run();let data=pipe.fileHandleForReading.readDataToEndOfFile();p.waitUntilExit()
                    if p.terminationStatus==0,!data.isEmpty {bytes=data;try FileManager.default.createDirectory(at:cache,withIntermediateDirectories:true);try data.write(to:path,options:.atomic)}
                } catch {}
            }
            let data=bytes
            Task {@MainActor [weak self] in if let data,let image=NSImage(data:data){self?.images[key]=image}}
        }
    }
}
