import Foundation

struct WorkspacePreviewSession:Codable,Equatable {
    let video:String
    let job:String?
    let seconds:Double
    let follow:Bool
}

extension AppModel {
    /// 已提交排程按影片對應；舊設定入面嘅 video 唔可以蓋過 videos 清單。
    func requestVideos(_ data:Data)->[String] {
        guard let cfg=WorkspaceRequestCache.decode(data) else{return []}
        if let videos=cfg["videos"] as? [[String:Any]],!videos.isEmpty {return videos.compactMap {$0["video"] as? String}}
        return (cfg["video"] as? String).map {[$0]} ?? []
    }
    func hasBatchRequest(video:String?)->Bool {
        guard let video else{return false}
        let requests=(busy ? currentBatchRequest.map {[$0]} ?? []:[])+pendingBatchRequests
        return requests.contains {requestVideos($0).contains(video)}
    }
    func queuedEditorVideo(_ task:EditorialTask)->String? {
        let review=ProcessingAudioIndex.read(URL(fileURLWithPath:task.review))
        return (review["config"] as? [String:Any])?["video"] as? String
    }
    func hasSavedRequest(video:String?)->Bool {
        guard let video else{return false}
        return hasBatchRequest(video:video) || editorTasks.contains {$0.status=="queued" && queuedEditorVideo($0)==video}
    }
    var nextSavedVideo:String? {
        editorTasks.first(where:{$0.status=="queued"}).flatMap(queuedEditorVideo) ?? pendingBatchRequests.first.flatMap {requestVideos($0).first}
    }
    func selectWorkspaceProject() {
        guard projectEditor.selectedRow==nil else{return}
        let preferred=[workspacePreview.savedSession?.video,nextSavedVideo,video?.path].compactMap {$0}
        let row=preferred.lazy.compactMap {path in self.projectEditor.projects.first {$0.video==path}}.first ?? projectEditor.projects.first
        if let row {projectEditor.open(row)}
    }
    func resumeWorkspaceProcessing() {
        guard !busy,!pauseStopping,hasSavedWork else{return}
        projectEditor.refresh(self)
        // 續做依真正排程次序揀片，唔用目前畫面嘅新設定重新提交。
        if let video=nextSavedVideo,let row=projectEditor.projects.first(where:{$0.video==video}),projectEditor.selected != row.id {projectEditor.open(row)}
        workspacePreview.refresh(self,video:projectEditor.selectedRow?.video)
        resumeProcessing()
    }
    func switchWorkspaceMode(_ mode:String) {
        selectWorkspaceProject()
        let source=projectEditor.selectedRow?.video
        let processing=usesProcessingPreview(self,projectEditor,workspacePreview)
        workspacePreview.stopInspection();projectEditor.audio.pause()
        if mode=="professional" {
            section = .studio;projectEditor.workspacePage="edit"
            if projectEditor.document != nil,!processing {projectEditor.playSource();projectEditor.seek(workspacePreview.seconds)}
        } else if projectEditor.document != nil,!processing {
            workspacePreview.refresh(self,video:source);workspacePreview.seek(projectEditor.seconds)
        }
        projectEditor.player.pause()
    }
    func saveWorkspaceForExit() {
        if (UserDefaults.standard.string(forKey:"studioInterfaceMode") ?? "simple")=="professional",projectEditor.document != nil,!usesProcessingPreview(self,projectEditor,workspacePreview) {
            workspacePreview.refresh(self,video:projectEditor.selectedRow?.video)
            workspacePreview.seek(projectEditor.seconds)
        }
        workspacePreview.persistSession()
        do {try projectEditor.save()} catch {self.error=error.localizedDescription}
        persistBatch();persistBatchRequests();saveEditorQueue()
    }
}
