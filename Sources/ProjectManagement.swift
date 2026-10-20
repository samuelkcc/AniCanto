import SwiftUI
import AppKit
import CryptoKit

enum CleanupMode:String {case outputs,projects,all}
struct ProjectCleanupPlan {
    let root:URL
    let mode:CleanupMode
    var folders:[URL]=[]
    var reviews:[URL]=[]
    var outputs:[URL]=[]
    var cacheFolders:[URL]=[]
    var sources=Set<String>()
    var keptExports:[URL]=[]
    init(root:URL,mode:CleanupMode,review:URL?=nil) throws {
        self.root=root;self.mode=mode
        let fm=FileManager.default,jobs=root.appendingPathComponent("jobs").resolvingSymlinksInPath()
        let children=(try? fm.contentsOfDirectory(at:jobs,includingPropertiesForKeys:[.isDirectoryKey,.isSymbolicLinkKey])) ?? []
        let db=try ProjectDatabase(root:root)
        var candidates:[URL]=[]
        for folder in children {
            let values=try folder.resourceValues(forKeys:[.isDirectoryKey,.isSymbolicLinkKey])
            guard values.isDirectory==true,values.isSymbolicLink != true else{continue}
            let file=folder.appendingPathComponent("review.json")
            if let data=try? Data(contentsOf:file),let o=try? JSONSerialization.jsonObject(with:data) as? [String:Any],let cfg=o["config"] as? [String:Any],let video=cfg["video"] as? String {sources.insert(URL(fileURLWithPath:video).resolvingSymlinksInPath().path)}
            let versions=(try? fm.contentsOfDirectory(at:folder.appendingPathComponent("versions"),includingPropertiesForKeys:nil)) ?? []
            for p in [folder]+versions {
                for name in ["report.json","version.json"] {
                    guard let data=try? Data(contentsOf:p.appendingPathComponent(name)),let o=try? JSONSerialization.jsonObject(with:data) as? [String:Any] else{continue}
                    for field in ["output","exportedOutput"] {if let path=o[field] as? String {candidates.append(URL(fileURLWithPath:path))}}
                }
            }
            if review==nil || file.resolvingSymlinksInPath()==review?.resolvingSymlinksInPath() {
                if fm.fileExists(atPath:file.path) {reviews.append(file)}
                folders.append(folder)
            }
        }
        if let review,review.deletingLastPathComponent().resolvingSymlinksInPath().deletingLastPathComponent() != jobs {throw AppFailure(message:"只可以清理 App 管理嘅專案。")}
        candidates += try db.rows("SELECT path FROM outputs").compactMap {$0.first.map {URL(fileURLWithPath:$0)}}
        var seen=Set<String>()
        outputs=candidates.filter {url in
            let path=url.resolvingSymlinksInPath().path
            guard !sources.contains(path),OutputStore.isOutputName(url.lastPathComponent),seen.insert(path).inserted,let values=try? url.resourceValues(forKeys:[.isRegularFileKey,.isSymbolicLinkKey]) else{return false}
            return values.isRegularFile==true && values.isSymbolicLink != true
        }
        if mode == .outputs {folders=[];reviews=[]}
        if mode == .projects {keptExports=outputs.filter {!$0.resolvingSymlinksInPath().path.hasPrefix(jobs.path+"/")};outputs=[]}
        for folder in folders where sources.contains(where:{$0.hasPrefix(folder.resolvingSymlinksInPath().path+"/")}) {throw AppFailure(message:"原片存放喺專案內，請先將原片移到其他資料夾："+folder.lastPathComponent)}
        if mode == .all {
            for name in ["separations","performance","openings","previews","ocr-previews","qwen-references","engine-references","legacy-export-sidecars"] {
                let url=root.appendingPathComponent(name)
                guard let values=try? url.resourceValues(forKeys:[.isDirectoryKey,.isSymbolicLinkKey]),values.isDirectory==true,values.isSymbolicLink != true,!sources.contains(where:{$0.hasPrefix(url.resolvingSymlinksInPath().path+"/")}) else{continue}
                cacheFolders.append(url)
            }
        }
    }
    var summary:String {L("專案")+": \(folders.count) · "+L("成品 MP4")+": \(outputs.count) · "+L("處理快取")+": \(cacheFolders.count)"}
    func execute(move:((URL)throws->Void)?=nil) throws -> [String] {
        let fm=FileManager.default,db=try ProjectDatabase(root:root)
        let trash:(URL)throws->Void=move ?? {try fm.trashItem(at:$0,resultingItemURL:nil)}
        var moved:[String]=[]
        // Keep reusable role recordings even when they originally lived in a job/cache.
        if mode != .outputs {try preserveRoleRecordings()}
        for file in keptExports {try db.execute("INSERT OR IGNORE INTO outputs VALUES(?,?,?,?)",[file.resolvingSymlinksInPath().path,"","complete",String(Date().timeIntervalSince1970)])}
        for url in outputs {try trash(url);try db.removeOutput(url);moved.append(url.path)}
        for folder in folders {
            try trash(folder);moved.append(folder.path)
            let review=folder.appendingPathComponent("review.json")
            try db.removeProject(review,keepExportedOutputs:mode == .projects)
        }
        for folder in cacheFolders {try trash(folder);moved.append(folder.path)}
        if mode == .all {
            for name in ["batch-queue.json","editor-queue.json","batch-submissions.json","batch-inflight.json"] {
                let file=root.appendingPathComponent(name)
                if fm.fileExists(atPath:file.path) {try trash(file);moved.append(file.path)}
            }
            for name in ["batch-queue.json","editor-queue.json","batch-submissions.json"] {try Data("[]".utf8).write(to:root.appendingPathComponent(name),options:.atomic)}
            try db.execute("DELETE FROM documents");try db.execute("DELETE FROM projects");try db.execute("DELETE FROM outputs")
            if !(try db.rows("SELECT name FROM sqlite_master WHERE type='table' AND name='issues'")).isEmpty {try db.execute("DELETE FROM issues")}
        }
        let receipt=root.appendingPathComponent("cleanup-receipts")
        try fm.createDirectory(at:receipt,withIntermediateDirectories:true)
        try JSONSerialization.data(withJSONObject:["mode":mode.rawValue,"moved":moved,"created":ISO8601DateFormatter().string(from:Date())],options:.prettyPrinted).write(to:receipt.appendingPathComponent(UUID().uuidString+".json"),options:.atomic)
        return moved
    }
    func preserveRoleRecordings() throws {try Self.preserveRoleRecordings(root:root,folders:folders,cacheFolders:cacheFolders)}
    static func preserveRoleRecordings(root:URL,folders:[URL],cacheFolders:[URL]) throws {
        let file=root.appendingPathComponent("voice-profiles.json")
        guard let data=try? Data(contentsOf:file),var profiles=try? JSONSerialization.jsonObject(with:data) as? [[String:Any]] else{return}
        let removed=(folders+cacheFolders).map {$0.resolvingSymlinksInPath().path+"/"}
        let destination=root.appendingPathComponent("saved-role-recordings")
        func preserve(_ path:String) throws -> String {
            guard removed.contains(where:{URL(fileURLWithPath:path).resolvingSymlinksInPath().path.hasPrefix($0)}),FileManager.default.fileExists(atPath:path) else{return path}
            let bytes=try Data(contentsOf:URL(fileURLWithPath:path)),hash=SHA256.hash(data:bytes).map{String(format:"%02x",$0)}.joined()
            try FileManager.default.createDirectory(at:destination,withIntermediateDirectories:true)
            let target=destination.appendingPathComponent(hash+".wav");try bytes.write(to:target,options:.atomic)
            return target.path
        }
        for i in profiles.indices {
            if let path=profiles[i]["reference"] as? String {profiles[i]["reference"]=try preserve(path)}
            if var own=profiles[i]["engineReferences"] as? [String:[String:Any]] {
                for key in Array(own.keys) {if let path=own[key]?["reference"] as? String {own[key]?["reference"]=try preserve(path)}}
                profiles[i]["engineReferences"]=own
            }
        }
        try JSONSerialization.data(withJSONObject:profiles,options:.prettyPrinted).write(to:file,options:.atomic)
    }
}

extension AppModel {
    func manageCleanup(mode:CleanupMode,review:URL?=nil) {
        guard !busy,activeEditorTask==nil else{return}
        do {
            let plan=try ProjectCleanupPlan(root:engine.root,mode:mode,review:review)
            let alert=NSAlert();alert.messageText=L(mode == .all ? "全部清理並重新開始？":mode == .outputs ? "刪除成品？":"刪除專案？")
            alert.informativeText=plan.summary+"\n"+L(mode == .projects ? "專案字幕、配音及草稿會移到垃圾桶；外部 MP4 保留。":"所選內容會移到垃圾桶，可以由 Finder 還原。")+"\n"+L("原片、下載模型及全局設定會保留。")
            alert.addButton(withTitle:L("移到垃圾桶"));alert.addButton(withTitle:L("取消"))
            guard alert.runModal() == .alertFirstButtonReturn else{return}
            projectEditor.closeForCleanup();player.pause();player.replaceCurrentItem(with:nil);audioPlayer.pause()
            let moved=try plan.execute()
            if mode == .all {batchItems=[];editorTasks=[];pendingBatchRequests=[];currentBatchRequest=nil;queuePaused=false;reviewURL=nil;video=nil;output=nil;previewURL=nil;activePreviewJob=nil;scriptCues=[];timingRows=[]}
            else if mode == .projects {
                let paths=Set(plan.reviews.map(\.path))
                let ids=Set(batchItems.filter {item in item.review.map{paths.contains($0)} ?? false}.map(\.id))
                batchItems.removeAll {ids.contains($0.id)};editorTasks.removeAll {paths.contains($0.review)}
                pendingBatchRequests=pendingBatchRequests.filter {data in
                    guard let cfg=try? JSONSerialization.jsonObject(with:data) as? [String:Any],let videos=cfg["videos"] as? [[String:Any]] else{return true}
                    return !videos.contains {ids.contains($0["id"] as? String ?? "")}
                }
                if review==nil {batchItems=[];editorTasks=[];pendingBatchRequests=[];reviewURL=nil;video=nil;previewURL=nil;activePreviewJob=nil}
            } else {for i in batchItems.indices {batchItems[i].output=nil};output=nil}
            persistBatch();saveEditorQueue();persistBatchRequests();loadProfiles()
            refresh();projectEditor.refresh(self);error=nil;stage=L("清理完成");detail=String(moved.count)+L(" 項已移到垃圾桶；可以加入新影片開始。");logs.append("[清理] "+plan.summary)
        } catch {self.error=error.localizedDescription;refresh();projectEditor.refresh(self)}
    }
}
extension ProjectEditor {
    func closeForCleanup() {
        player.pause();player.replaceCurrentItem(with:nil);audio.pause();audio.replaceCurrentItem(with:nil)
        document=nil;selected=nil;selectedSegment=nil;versions=[];profiles=[];dirty=false;pendingAudition=nil
    }
}
final class ProjectManagerOptions:ObservableObject {@Published var tab="projects";@Published var outputs:[URL]=[]}
struct ProjectManagerView:View {
    @AppStorage("studioLanguage") private var language="system"
    @ObservedObject var model:AppModel
    @StateObject private var options=ProjectManagerOptions()
    func reload() {model.refresh();model.projectEditor.refresh(model);options.outputs=(try? ProjectCleanupPlan(root:model.engine.root,mode:.outputs).outputs) ?? []}
    var body:some View {
        VStack(alignment:.leading,spacing:12) {
            HStack {Text(L("專案／成品管理")).font(.title2.bold());Spacer();Button(L("重新整理"),action:reload)}
            Text(L("專案係字幕、配音同編輯資料；成品係已生成 MP4。")).foregroundStyle(.secondary)
            Picker(L("管理內容"),selection:$options.tab) {Text(L("專案")).tag("projects");Text(L("成品 MP4")).tag("outputs");Text(L("編輯排程")).tag("queue")}.pickerStyle(.segmented)
            ScrollView {LazyVStack(alignment:.leading,spacing:8) {
                if options.tab=="projects" {
                    if model.projectEditor.projects.isEmpty {Text(L("未有專案")).font(.headline);Text(L("加入影片開始第一個專案。")).foregroundStyle(.secondary)}
                    ForEach(model.projectEditor.projects) {row in
                        HStack {VStack(alignment:.leading) {Text(row.name).font(.headline);Text(L(row.status)).font(.caption);if let path=row.review {Text(path.deletingLastPathComponent().lastPathComponent).font(.caption2.monospaced()).foregroundStyle(.secondary)}};Spacer()
                            if let review=row.review {Button(L("刪除專案，保留成品"),role:.destructive) {model.manageCleanup(mode:.projects,review:review);reload()}}
                            else {Button(L("移出佇列")) {model.removeBatchItem(id:row.id);reload()}}
                        }.padding(10).background(Color.secondary.opacity(0.05),in:RoundedRectangle(cornerRadius:8))
                    }
                } else if options.tab=="queue" {
                    ProjectWorkspace(model:model,editor:model.projectEditor).queue
                    
                } else {
                    if options.outputs.isEmpty {Text(L("未有輸出成品")).font(.headline);Text(L("完成製作後，成品會顯示喺呢度。")).foregroundStyle(.secondary)}
                    ForEach(options.outputs,id:\.path) {file in
                        HStack {VStack(alignment:.leading) {Text(file.lastPathComponent).font(.headline);ProductionDurationLabel(output:file);Text(file.path).font(.caption2).foregroundStyle(.secondary).lineLimit(1).truncationMode(.middle)};Spacer();Button(L("用播放器開啟")) {NSWorkspace.shared.open(file)};Button(L("檔案")) {NSWorkspace.shared.activateFileViewerSelecting([file])};Button(L("移到垃圾桶"),role:.destructive) {model.trashOutput(file);reload()}}
                    }
                }
            }}.frame(maxHeight:.infinity)
            HStack {
                Menu {
                    Button(L("刪除全部成品…"),role:.destructive) {model.manageCleanup(mode:.outputs);reload()}.disabled(options.outputs.isEmpty)
                    Button(L("刪除全部專案，保留成品…"),role:.destructive) {model.manageCleanup(mode:.projects);reload()}
                    Divider()
                    Button(L("全部清理並重新開始…"),role:.destructive) {model.manageCleanup(mode:.all);reload()}
                } label:{Label(L("清理選項"),systemImage:"trash")}
                Spacer()
            }

            Text(L("原片、下載模型及全局設定會保留。")).font(.caption).foregroundStyle(.secondary)
            if let error=model.error {Text(error).foregroundStyle(.red)}
        }.padding(28).frame(maxWidth:.infinity,maxHeight:.infinity,alignment:.topLeading).background(StudioPalette.panel).font(.system(size:15)).buttonStyle(StudioButtonStyle()).onAppear(perform:reload).disabled(model.busy)
    }
}
