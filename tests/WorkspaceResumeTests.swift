import SwiftUI
import AppKit

@main struct WorkspaceResumeTests {
 @MainActor static func main() throws {
    runManagedToolIfNeeded()
    NSApplication.shared.setActivationPolicy(.prohibited)
    let qa=URL(fileURLWithPath:ProcessInfo.processInfo.environment["CANTO_WORKSPACE_QA"] ?? FileManager.default.currentDirectoryPath+"/.build/qa266")
    let root=URL(fileURLWithPath:ProcessInfo.processInfo.environment["SAM_CANTO_DATA"]!)
    precondition(root.path.hasPrefix(qa.path))
    UserDefaults.standard.set("zh-HK",forKey:"studioLanguage")
    UserDefaults.standard.set("simple",forKey:"studioInterfaceMode")
    func write(_ value:Any,_ path:URL) throws {
        try FileManager.default.createDirectory(at:path.deletingLastPathComponent(),withIntermediateDirectories:true)
        try JSONSerialization.data(withJSONObject:value).write(to:path,options:.atomic)
    }
    let video=qa.appendingPathComponent("preview.mp4")
    let other=qa.appendingPathComponent("other.mp4")
    let job=root.appendingPathComponent("jobs/resume")
    let review=job.appendingPathComponent("review.json")
    let cue:[String:Any]=["start":1.0,"end":3.0,"text":"行こう","cantonese":"一齊出發啦。","speakerId":"role"]
    let cfg:[String:Any]=["video":video.path,"duration":12.0,"selectedEngines":["drama3"],"ttsBackend":"drama3","dubLanguages":["yue"],"includeOriginal":true]
    let request=try JSONSerialization.data(withJSONObject:cfg.merging(["videos":[["id":"paused","video":video.path]]]) {_,new in new},options:[.sortedKeys])
    if CommandLine.arguments.contains("--restore") {
        let model=AppModel()
        precondition(!model.busy && model.queuePaused && model.hasSavedWork,"重開必須停住等用戶繼續")
        precondition(model.pendingBatchRequests==[request],"重開唔改寫保存嘅引擎同語言設定")
        model.projectEditor.refresh(model);model.selectWorkspaceProject()
        precondition(model.projectEditor.selectedRow?.video==video.path,"重開恢復上次揀中影片")
        model.workspacePreview.refresh(model,video:video.path)
        precondition(abs(model.workspacePreview.seconds-2.25)<0.01 && !model.workspacePreview.follow,"重開恢復預覽位置同跟隨選項")
        let simple=SimpleWorkspace(model:model,editor:model.projectEditor)
        precondition(simple.canResume && simple.pendingHere)
        precondition(usesProcessingPreview(model,model.projectEditor,model.workspacePreview),"暫停排程仍然用處理預覽")
        print("PASS 真正新程序重開：排程、影片、預覽位置、跟隨選項全部恢復；冇自動派發")
        return
    }
    try write(["config":cfg,"cues":[cue],"meta":["streams":[]],"status":"pending"],review)
    try write(["video":video.path,"duration":12.0],job.appendingPathComponent("processing-preview.json"))
    let model=AppModel(),editor=model.projectEditor
    model.batchItems=[BatchItem(id:"other",video:other.path),BatchItem(id:"paused",video:video.path,status:"已暫停",review:review.path)]
    model.pendingBatchRequests=[request];model.queuePaused=true;model.persistBatch();model.persistBatchRequests()
    editor.refresh(model)
    editor.open(editor.projects.first {$0.video==other.path}!)
    let simple=SimpleWorkspace(model:model,editor:editor)
    precondition(simple.canResume && !simple.pendingHere,"揀中其他片都要顯示繼續處理")
    precondition(simple.live === model.workspacePreview,"超簡單模式用共用播放器")
    let professional=ProjectWorkspace(model:model,editor:editor)
    precondition(professional.livePreview === model.workspacePreview,"專業模式用同一個播放器")
    editor.open(editor.projects.first {$0.video==video.path}!)
    model.busy=true;model.currentBatchRequest=request;model.activePreviewJob=job.path
    let fresh=LiveVideoPreview()
    precondition(usesProcessingPreview(model,editor,fresh),"未載入 processingVideo 都必須識別目前排程")
    model.workspacePreview.refresh(model,video:video.path)
    model.workspacePreview.follow=false;model.workspacePreview.seek(2.25)
    let frozen=model.currentBatchRequest!
    model.switchWorkspaceMode("professional")
    precondition(model.section == .studio && model.workspacePreview.seconds==2.25 && !model.workspacePreview.follow)
    model.switchWorkspaceMode("simple")
    precondition(model.workspacePreview.seconds==2.25 && model.currentBatchRequest==frozen)
    model.busy=false;model.currentBatchRequest=nil
    model.workspacePreview.follow=true;model.workspacePreview.refresh(model,video:video.path)
    precondition(model.workspacePreview.seconds==2.25,"暫停時唔跳返開頭")
    model.pendingBatchRequests=[]
    editor.seek(4.5)
    model.switchWorkspaceMode("simple")
    precondition(model.workspacePreview.seconds==4.5,"編輯模式位置帶返簡單模式")
    model.workspacePreview.seek(5.25)
    model.switchWorkspaceMode("professional")
    precondition(editor.seconds==5.25,"簡單模式位置帶返編輯模式")
    model.pendingBatchRequests=[request];model.workspacePreview.follow=false;model.workspacePreview.seek(2.25)
    let taskFile=job.appendingPathComponent("submission.json")
    try write(["settings":["ttsBackend":"drama3","dubLanguages":["yue"]]],taskFile)
    model.pendingBatchRequests=[];model.editorTasks=[EditorialTask(id:"queued-editor",review:review.path,submission:taskFile.path)]
    precondition(model.hasSavedRequest(video:video.path) && model.nextSavedVideo==video.path,"編輯排程亦可恢復")
    model.editorTasks=[];model.pendingBatchRequests=[request]
    // 用真實 SwiftUI 元件驗證兩個模式共用預覽，唔派發配音。
    func render<V:View>(_ view:V,_ name:String) throws {
        let host=NSHostingView(rootView:view.frame(width:1280,height:1000).environment(\.locale,Locale(identifier:"zh-HK")).environment(\.colorScheme,.light).background(StudioPalette.base).foregroundStyle(ink).tint(accent))
        host.frame=NSRect(x:0,y:0,width:1280,height:1000)
        let window=NSWindow(contentRect:host.frame,styleMask:[.borderless],backing:.buffered,defer:false);window.contentView=host
        host.layoutSubtreeIfNeeded();RunLoop.main.run(until:Date().addingTimeInterval(0.5));host.layoutSubtreeIfNeeded()
        if let bitmap=host.bitmapImageRepForCachingDisplay(in:host.bounds) {host.cacheDisplay(in:host.bounds,to:bitmap);try bitmap.representation(using:.png,properties:[:])!.write(to:qa.appendingPathComponent(name))}
        window.close()
    }
    try render(SimpleWorkspace(model:model,editor:editor),"simple-paused.png")
    try render(ProjectWorkspace(model:model,editor:editor),"professional-paused.png")
    model.workspacePreview.follow=false;model.workspacePreview.seek(2.25)
    model.saveWorkspaceForExit()
    // 保留 inflight 模擬生成期間退出；下一次程序要去重還原。
    try request.write(to:root.appendingPathComponent("batch-inflight.json"),options:.atomic)
    print("PASS 全局繼續按鈕、共用播放器、首次跟隨、雙向位置同步、編輯排程、原生介面；已保存重開測試資料")
 }
}
