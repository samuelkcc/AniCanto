import SwiftUI

extension AppModel {
    var hasSavedWork:Bool {!pendingBatchRequests.isEmpty || editorTasks.contains {$0.status=="queued"}}
    var canPauseProcessing:Bool {busy && (batchRunning || activeEditorTask != nil)}
    func pauseProcessing() {
        guard canPauseProcessing,!pauseRequested else {return}
        queuePaused=true;pauseRequested=true;pauseStopping=true;activeAudioTrack=nil
        persistBatchRequests();persistBatch();saveEditorQueue()
        detail="正在暫停；完成嘅進度會保留。"
        let e=engine
        // Stopping child processes must not block the main UI thread.
        Task {await Task.detached {e.cancel()}.value;pauseStopping=false}
    }
    func resumeProcessing() {
        guard !busy,!pauseStopping,hasSavedWork else {return}
        pauseRequested=false;queuePaused=false;error=nil
        logs.append("[繼續摘要] 使用已保存設定續做，重用有效嘅字幕、翻譯及配音快取。")
        pumpEditorQueue()
        if !busy {pumpBatchRequests()}
    }
}

struct ProcessingQueueButton:View {
    @ObservedObject var model:AppModel
    var iconOnly=false
    var body:some View {
        if model.canPauseProcessing {
            Button(action:model.pauseProcessing) {controlLabel(model.pauseRequested ? "正在暫停…":"暫停並保存","pause.circle")}
                .disabled(model.pauseRequested).help(L("保留完成進度及設定；未完成步驟可能需要重做。"))
        } else if !model.busy && model.hasSavedWork {
            Button(action:model.resumeWorkspaceProcessing) {controlLabel("繼續處理","play.circle")}.buttonStyle(StudioButtonStyle(prominent:true)).disabled(model.pauseStopping)
        } else {
            Button(action:model.startBatch) {controlLabel("開始佇列","play.circle")}.disabled(model.busy || !model.batchItems.contains {["待處理","需要處理","已中斷，可重試","已暫停"].contains($0.status)}).buttonStyle(StudioButtonStyle(prominent:true))
        }
    }
    @ViewBuilder private func controlLabel(_ title:String,_ icon:String)->some View {
        if iconOnly {StudioToolbarIcon(name:icon).help(L(title)).accessibilityLabel(L(title))}
        else {Label(L(title),systemImage:icon)}
    }

}
