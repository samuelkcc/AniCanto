import Foundation

// Stable bounded payload shared by the native worker and the desktop queue.
extension WorkerEvent {
    func sharedStudioFields() -> [String:Any] {
        var row:[String:Any] = ["stage":self.stage,"message":self.message]
        if let v=self.progress {row["progress"]=v}
        if let v=self.output {row["output"]=v}
        if let v=self.job {row["job"]=v}
        if let v=self.review {row["review"]=v}
        if let v=self.deliveryKind {row["deliveryKind"]=v}
        if let v=self.artifactRole {row["artifactRole"]=v}
        if let v=self.previewOutput {row["previewOutput"]=v}
        if let v=self.missingDialogue {row["missingDialogue"]=v}
        if let v=self.incompleteDialogue {row["incompleteDialogue"]=v}
        if let v=self.trackOutput {row["trackOutput"]=v}
        if let v=self.primaryVoiceFraction {row["primaryVoiceFraction"]=v}
        if let v=self.workCached {row["workCached"]=v}
        if let v=self.partial {row["partial"]=v}
        if let v=self.workID {row["workID"]=v}
        if let v=self.workCompleted {row["workCompleted"]=v}
        if let v=self.workTotal {row["workTotal"]=v}
        if let v=self.cueIndex {row["cueIndex"]=v}
        if let v=self.batchStatus {row["batchStatus"]=v}
        if let v=self.download,let data=try? JSONEncoder().encode(v),let obj=try? JSONSerialization.jsonObject(with:data) {row["download"]=obj}
        if let v=self.journey,let data=try? JSONEncoder().encode(v),let obj=try? JSONSerialization.jsonObject(with:data) {row["journey"]=obj}
        return row
    }
}
