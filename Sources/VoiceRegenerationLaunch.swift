import Foundation

extension AppModel {
    /// Explicit launch argument for a user-requested rerun. Existing pending
    /// conversions stay paused; this creates a separate editorial voice version.
    func regenerateExistingVoices(review:String) {
        guard !busy else{return}
        let url=URL(fileURLWithPath:review).resolvingSymlinksInPath()
        guard url.lastPathComponent=="review.json",url.path.hasPrefix(engine.root.appendingPathComponent("jobs").resolvingSymlinksInPath().path+"/") else{error="重新配音專案路徑無效。";return}
        projectEditor.refresh(self)
        guard let row=projectEditor.projects.first(where:{$0.review?.resolvingSymlinksInPath()==url}) else{error="未找到重新配音專案。";return}
        projectEditor.open(row)
        guard projectEditor.document != nil else{return}
        projectEditor.document?.voiceStyleMode=voiceStyleMode
        section = .studio;queuePaused=true
        let selected=(projectEditor.config["selectedEngines"] as? [String] ?? [projectEditor.config["ttsBackend"] as? String ?? "gpt-sovits"]).filter {VoiceEngineChoice.all.map(\.id).contains($0)}
        let languages=projectEditor.document?.dubLanguages ?? projectEditor.config["dubLanguages"] as? [String] ?? ["yue"]
        let previous=Set(editorTasks.map(\.id))
        submitEditor(audioSettings:["voiceStyleMode":voiceStyleMode,"selectedEngines":selected,"defaultAudioEngine":selected.first ?? "gpt-sovits","dubLanguages":languages,"audioOnlyRerun":true,"audioRerunToken":UUID().uuidString,"fillMissingVoiceScripts":true,"pauseAfterVoiceRegeneration":true])
        guard let index=editorTasks.firstIndex(where:{!previous.contains($0.id)}) else{return}
        let task=editorTasks.remove(at:index);editorTasks.insert(task,at:0);saveEditorQueue()
        pauseAfterVoiceRegeneration=true;queuePaused=false;pumpEditorQueue()
    }
}
