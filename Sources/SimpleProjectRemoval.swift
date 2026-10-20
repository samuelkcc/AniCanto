import Foundation
import CryptoKit
import Darwin
import AppKit

/// Per-source cleanup. Never infer ownership from a basename or delete a whole
/// shared cache. All managed paths are checked without traversing symlinks.
struct SimpleProjectRemovalPlan {
    let root:URL,video:URL
    var folders:[URL]=[],caches:[URL]=[],outputs:[URL]=[],requests:[URL]=[]
    var requestUpdates:[URL:Data]=[:]
    var sharedMetadata:[URL]=[]
    static let cacheNames=["separations","openings","previews","ocr-previews","engine-references","qwen-references","voice-previews"]
    static func canonical(_ url:URL)->String {url.resolvingSymlinksInPath().standardizedFileURL.path}
    static func strings(_ object:Any)->[String] {
        if let value=object as? String {return [value]}
        if let values=object as? [Any] {return values.flatMap(strings)}
        if let values=object as? [String:Any] {return values.values.flatMap(strings)}
        return []
    }
    static func json(_ file:URL)->Any? {(try? Data(contentsOf:file)).flatMap {try? JSONSerialization.jsonObject(with:$0)}}
    static func files(_ folder:URL)->[URL] {
        guard let walk=FileManager.default.enumerator(at:folder,includingPropertiesForKeys:[.isSymbolicLinkKey,.isRegularFileKey],options:[.skipsHiddenFiles]) else{return []}
        var result:[URL]=[]
        for case let file as URL in walk {
            guard let values=try? file.resourceValues(forKeys:[.isSymbolicLinkKey,.isRegularFileKey]) else{continue}
            if values.isSymbolicLink==true {walk.skipDescendants();continue}
            if values.isRegularFile==true {result.append(file)}
        }
        return result
    }
    static func safe(_ url:URL,under parent:URL)->Bool {
        let base=parent.standardizedFileURL.path,path=url.standardizedFileURL.path
        guard path.hasPrefix(base+"/"),canonical(parent)==base,canonical(url)==path else{return false}
        return (try? url.resourceValues(forKeys:[.isSymbolicLinkKey]).isSymbolicLink)==false
    }
    static func prune(_ data:Data,video:String,ids:Set<String>)->Data? {
        guard var cfg=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any] else{return data}
        if let rows=cfg["videos"] as? [[String:Any]] {
            let kept=rows.filter {row in !ids.contains(row["id"] as? String ?? "") && (row["video"] as? String).map {canonical(URL(fileURLWithPath:$0)) != video} != false}
            guard !kept.isEmpty else{return nil}
            if kept.count==rows.count {return data}
            cfg["videos"]=kept;cfg["video"]=kept[0]["video"]
            return try? JSONSerialization.data(withJSONObject:cfg)
        }
        if let source=cfg["video"] as? String,canonical(URL(fileURLWithPath:source))==video {return nil}
        return data
    }
    init(root:URL,video:String,knownOutputs:[String]=[]) throws {
        self.root=root.standardizedFileURL;self.video=URL(fileURLWithPath:video).resolvingSymlinksInPath().standardizedFileURL
        let fm=FileManager.default,jobs=self.root.appendingPathComponent("jobs"),source=self.video.path
        guard Self.canonical(self.root)==self.root.path else{throw AppFailure(message:L("專案儲存位置無效，未有移除任何檔案。"))}
        let children=(try? fm.contentsOfDirectory(at:jobs,includingPropertiesForKeys:nil)) ?? []
        var protectedSources=Set([source])
        var otherReferences:[String]=[],selectedReferences:[String]=[],candidates=knownOutputs.map {URL(fileURLWithPath:$0)}
        for folder in children where Self.safe(folder,under:jobs) {
            let review=(Self.json(folder.appendingPathComponent("review.json")) as? [String:Any])?["config"] as? [String:Any]
            let meta=Self.json(folder.appendingPathComponent("processing-preview.json")) as? [String:Any]
            let owner=review?["video"] as? String ?? meta?["video"] as? String
            if let owner {protectedSources.insert(Self.canonical(URL(fileURLWithPath:owner)))}
            let selected=owner.map {Self.canonical(URL(fileURLWithPath:$0))==source} ?? false
            let files=Self.files(folder)
            let objects=files.filter {$0.pathExtension=="json"}.compactMap {Self.json($0)}
            let refs=objects.flatMap(Self.strings).filter {$0.hasPrefix("/")}
            if selected {
                folders.append(folder);selectedReferences += refs
                for file in files where OutputStore.isOutputName(file.lastPathComponent) {candidates.append(file)}
                for file in files where ["report.json","version.json"].contains(file.lastPathComponent) {
                    guard let row=Self.json(file) as? [String:Any] else{continue}
                    for key in ["output","exportedOutput"] {if let path=row[key] as? String {candidates.append(URL(fileURLWithPath:path))}}
                }
            } else {otherReferences += refs;sharedMetadata += files.filter {$0.pathExtension=="json"}}
        }
        // A role explicitly saved to the global voice library remains reusable.
        let library=Self.json(self.root.appendingPathComponent("voice-profiles.json"))
        otherReferences += library.map(Self.strings) ?? []
        let db=try ProjectDatabase(root:self.root)
        for row in try db.rows("SELECT path,project FROM outputs") where row.count>1 && folders.contains(where:{row[1].hasPrefix($0.path+"/")}) {candidates.append(URL(fileURLWithPath:row[0]))}
        var seen=Set<String>()
        outputs=candidates.filter {file in
            let path=Self.canonical(file)
            guard !protectedSources.contains(path),seen.insert(path).inserted,path==file.standardizedFileURL.path,
                  let values=try? file.resourceValues(forKeys:[.isRegularFileKey,.isSymbolicLinkKey]),values.isRegularFile==true,values.isSymbolicLink != true else{return false}
            return ["mp4","mkv","mov","m4v"].contains(file.pathExtension.lowercased())
        }
        // A source accidentally stored inside managed work must never be removed.
        guard !folders.contains(where:{folder in protectedSources.contains {$0.hasPrefix(folder.path+"/")}}) else{throw AppFailure(message:L("原片存放喺專案內，請先移走原片再移除專案。"))}
        let ownedFolders=folders
        func belongs(_ refs:[String])->Bool {refs.contains {ref in ref==source || ownedFolders.contains {ref.hasPrefix($0.path+"/")}}}
        for name in Self.cacheNames {
            let base=self.root.appendingPathComponent(name)
            var units=(try? fm.contentsOfDirectory(at:base,includingPropertiesForKeys:nil)) ?? []
            if name=="engine-references" {units=units.filter {Self.safe($0,under:base)}.flatMap {(try? fm.contentsOfDirectory(at:$0,includingPropertiesForKeys:nil)) ?? []}}
            for unit in units where Self.safe(unit,under:base) {
                let prefix=unit.path+"/"
                let referenced=selectedReferences.contains {$0==unit.path || $0.hasPrefix(prefix)}
                let refs=unit.pathExtension=="json" ? Self.json(unit).map(Self.strings) ?? []:Self.files(unit).filter {$0.pathExtension=="json"}.compactMap(Self.json).flatMap(Self.strings)
                guard referenced || belongs(refs) else{continue}
                guard !otherReferences.contains(where:{$0==unit.path || $0.hasPrefix(prefix)}),!source.hasPrefix(prefix) else{continue}
                caches.append(unit)
            }
        }
        // Legacy preview files have deterministic native keys but no manifest.
        // Recreate the exact keys for this source; never sweep other previews.
        if let attrs=try? fm.attributesOfItem(atPath:source) {
            let base=self.root.appendingPathComponent("previews")
            func hash(_ value:String)->String {SHA256.hash(data:Data(value.utf8)).prefix(12).map {String(format:"%02x",$0)}.joined()}
            let preview=hash("preview-v2|"+source+"\(attrs[.size] ?? 0)"+"\(attrs[.modificationDate] ?? "")")
            var names=[preview+".mp4",preview+".partial.mp4"]
            for stream in -1...255 {
                let tail="|\(stream)|\(attrs[.size] ?? 0)|\(attrs[.modificationDate] ?? "")"
                names += ["captions-"+hash(source+tail)+".srt",hash("vlc-ass-v1|"+source+tail)+".ass"]
            }
            caches += names.map {base.appendingPathComponent($0)}.filter {Self.safe($0,under:base)}
        }
        // Legacy opening caches use Python's stable ASCII JSON identity.
        var statValue=stat()
        if stat(source,&statValue)==0 {
            let data=try JSONSerialization.data(withJSONObject:source,options:[.fragmentsAllowed,.withoutEscapingSlashes])
            let escaped=String(decoding:data,as:UTF8.self).unicodeScalars.map {scalar -> String in
                if scalar.value<128 {return String(scalar)}
                return String(scalar).utf16.map {String(format:"\\u%04x",$0)}.joined()
            }.joined()
            let identity="[\(escaped), \(statValue.st_size), \(statValue.st_mtimespec.tv_sec*1_000_000_000+Int(statValue.st_mtimespec.tv_nsec)), 3]"
            let key=SHA256.hash(data:Data(identity.utf8)).prefix(10).map {String(format:"%02x",$0)}.joined()
            let base=self.root.appendingPathComponent("openings"),cache=base.appendingPathComponent(key)
            if Self.safe(cache,under:base) {caches.append(cache)}
        }
        caches=Array(Set(caches)).filter {cache in !outputs.contains(where:{$0.path==cache.path || $0.path.hasPrefix(cache.path+"/")})}
        for file in (try? fm.contentsOfDirectory(at:self.root,includingPropertiesForKeys:nil)) ?? [] {
            guard file.lastPathComponent.hasPrefix("request-"),file.pathExtension=="json",Self.safe(file,under:self.root),let data=try? Data(contentsOf:file) else{continue}
            if let kept=Self.prune(data,video:source,ids:[]) {if kept != data {requestUpdates[file]=kept}}
            else {requests.append(file)}
        }
    }
    func execute(move:((URL)throws->Void)?=nil) throws -> [URL] {
        let fm=FileManager.default,db=try ProjectDatabase(root:root)
        let trash=move ?? {try fm.trashItem(at:$0,resultingItemURL:nil)}
        var retained:[URL]=[]
        // Copy and hash-verify internal outputs before any project is trashed.
        for output in outputs {
            if folders.contains(where:{output.path.hasPrefix($0.path+"/")}) {
                let destination=root.appendingPathComponent("exports").appendingPathComponent(UUID().uuidString).appendingPathComponent(output.lastPathComponent)
                try fm.createDirectory(at:destination.deletingLastPathComponent(),withIntermediateDirectories:true)
                try fm.copyItem(at:output,to:destination)
                guard try Self.digest(output)==Self.digest(destination) else{throw AppFailure(message:L("成品保留驗證失敗，未有移除專案。"))}
                retained.append(destination)
            } else {retained.append(output)}
        }
        try ProjectCleanupPlan.preserveRoleRecordings(root:root,folders:folders,cacheFolders:caches)
        for file in sharedMetadata {
            guard let before=try? Data(contentsOf:file) else{continue}
            let after=try preservingSharedFiles(before)
            if after != before {
                try after.write(to:file,options:.atomic)
                try db.execute("UPDATE documents SET payload=?,updated=? WHERE path=?",[String(decoding:after,as:UTF8.self),String(Date().timeIntervalSince1970),file.path])
            }
        }
        for file in retained {try db.execute("INSERT OR REPLACE INTO outputs VALUES(?,?,?,?)",[file.path,"","complete",String(Date().timeIntervalSince1970)])}
        for folder in folders {guard Self.safe(folder,under:root.appendingPathComponent("jobs")) else{throw AppFailure(message:L("專案儲存位置無效，未有移除任何檔案。"))};try trash(folder);try db.removeProject(folder.appendingPathComponent("review.json"),keepExportedOutputs:true)}
        for file in caches+requests where fm.fileExists(atPath:file.path) {try trash(file)}
        for (file,data) in requestUpdates {try preservingSharedFiles(data).write(to:file,options:.atomic)}
        let receipts=root.appendingPathComponent("cleanup-receipts")
        try fm.createDirectory(at:receipts,withIntermediateDirectories:true)
        try JSONSerialization.data(withJSONObject:["mode":"simple-video","source":video.path,"removed":(folders+caches+requests).map(\.path),"keptOutputs":retained.map(\.path)],options:.prettyPrinted).write(to:receipts.appendingPathComponent(UUID().uuidString+".json"),options:.atomic)
        return retained
    }
    /// Other projects and their frozen requests may reuse a saved role from this
    /// job. Preserve only those referenced files and rewrite their paths first.
    func preservingSharedFiles(_ data:Data) throws -> Data {
        guard let object=try? JSONSerialization.jsonObject(with:data) else{return data}
        var changed=false,files:[String:String]=[:]
        func rewrite(_ object:Any) throws -> Any {
            if let value=object as? String,value.hasPrefix("/") {
                let file=URL(fileURLWithPath:value).resolvingSymlinksInPath().standardizedFileURL
                guard folders.contains(where:{file.path.hasPrefix($0.path+"/") || file.path==$0.path}),FileManager.default.fileExists(atPath:file.path) else{return value}
                if let saved=files[file.path] {changed=true;return saved}
                guard (try file.resourceValues(forKeys:[.isRegularFileKey])).isRegularFile==true else{throw AppFailure(message:L("其他專案仍然使用此資料夾，未有移除專案。"))}
                let hash=try Self.digest(file).map {String(format:"%02x",$0)}.joined()
                let target=root.appendingPathComponent("saved-project-assets").appendingPathComponent(hash+(file.pathExtension.isEmpty ? "":"."+file.pathExtension))
                try FileManager.default.createDirectory(at:target.deletingLastPathComponent(),withIntermediateDirectories:true)
                if !FileManager.default.fileExists(atPath:target.path) {try FileManager.default.copyItem(at:file,to:target)}
                guard try Self.digest(file)==Self.digest(target) else{throw AppFailure(message:L("共用聲音保留驗證失敗，未有移除專案。"))}
                files[file.path]=target.path;changed=true;return target.path
            }
            if let rows=object as? [Any] {return try rows.map(rewrite)}
            if let rows=object as? [String:Any] {return try rows.mapValues(rewrite)}
            return object
        }
        let result=try rewrite(object)
        return changed ? try JSONSerialization.data(withJSONObject:result,options:.prettyPrinted):data
    }
    private static func digest(_ file:URL) throws -> SHA256.Digest {
        let handle=try FileHandle(forReadingFrom:file);defer {try? handle.close()}
        var hash=SHA256()
        while let data=try handle.read(upToCount:1_048_576),!data.isEmpty {hash.update(data:data)}
        return hash.finalize()
    }
}

extension AppModel {
    func removeSimpleVideo(_ item:BatchItem,onPrepare:@escaping () async -> Void) {
        guard !busy,!simpleQueuePreparing,!simpleCleanupBusy,activeEditorTask==nil else{return}
        let alert=NSAlert();alert.messageText=L("移除影片，保留成品？")
        alert.informativeText=URL(fileURLWithPath:item.video).lastPathComponent+"\n\n"+L("會移除呢條影片嘅排程、字幕、配音、角色分析同處理快取。已輸出成品會保留；原片、模型同其他影片唔受影響。")
        alert.addButton(withTitle:L("移除並清理"));alert.addButton(withTitle:L("取消"))
        guard alert.runModal() == .alertFirstButtonReturn else{return}
        simpleCleanupBusy=true;busy=true;stage=L("正在移除影片");detail=L("正在保留成品及清理專案資料…")
        let root=engine.root,source=SimpleProjectRemovalPlan.canonical(URL(fileURLWithPath:item.video))
        let ids=Set(batchItems.filter {SimpleProjectRemovalPlan.canonical(URL(fileURLWithPath:$0.video))==source}.map(\.id))
        let knownOutputs=batchItems.filter {ids.contains($0.id)}.compactMap(\.output)
        Task {
            defer {simpleCleanupBusy=false;busy=false}
            await onPrepare()
            if projectEditor.dirty {
                do {try projectEditor.save()} catch {self.error=error.localizedDescription;return}
            }
            let previousSelection=projectEditor.selected
            projectEditor.closeForCleanup()
            player.pause();audioPlayer.pause()
            if video.map({SimpleProjectRemovalPlan.canonical($0)==source})==true {player.replaceCurrentItem(with:nil);video=nil;previewURL=nil;reviewURL=nil}
            do {
                let plan=try await Task.detached {try SimpleProjectRemovalPlan(root:root,video:item.video,knownOutputs:knownOutputs)}.value
                let paths=Set(plan.folders.map {$0.appendingPathComponent("review.json").path})
                let nextBatch=batchItems.filter {!ids.contains($0.id)}
                let nextEditor=editorTasks.filter {!paths.contains($0.review)}
                let nextRequests=try pendingBatchRequests.compactMap {SimpleProjectRemovalPlan.prune($0,video:source,ids:ids)}.map {try plan.preservingSharedFiles($0)}
                // Persist removal from every resumable queue before deleting work.
                // A crash/restart must not silently regenerate a removed video.
                try JSONEncoder().encode(nextBatch).write(to:root.appendingPathComponent("batch-queue.json"),options:.atomic)
                try JSONEncoder().encode(nextEditor).write(to:root.appendingPathComponent("editor-queue.json"),options:.atomic)
                try JSONEncoder().encode(nextRequests).write(to:root.appendingPathComponent("batch-submissions.json"),options:.atomic)
                let inflight=root.appendingPathComponent("batch-inflight.json")
                if let data=try? Data(contentsOf:inflight) {
                    if let kept=SimpleProjectRemovalPlan.prune(data,video:source,ids:ids) {try plan.preservingSharedFiles(kept).write(to:inflight,options:.atomic)}
                    else {try FileManager.default.removeItem(at:inflight)}
                }
                batchItems=nextBatch;editorTasks=nextEditor;pendingBatchRequests=nextRequests
                _ = try await Task.detached {try plan.execute()}.value
                projectEditor.productionSelections=projectEditor.productionSelections.filter {!paths.contains($0.key)}
                if let activePreviewJob,plan.folders.contains(where:{$0.path==activePreviewJob}) {self.activePreviewJob=nil}
                persistBatch();saveEditorQueue();persistBatchRequests();loadProfiles();refresh();projectEditor.refresh(self)
                error=nil;stage=L("移除完成");detail=L("影片處理資料已移除，輸出成品已保留。")
                if let row=projectEditor.projects.first(where:{$0.id==previousSelection}) ?? projectEditor.projects.first {projectEditor.open(row)}
            } catch {self.error=error.localizedDescription;refresh();projectEditor.refresh(self)}
        }
    }
}
