import Foundation

struct WorkspacePreviewInput:Equatable {
    let root:URL,video:String?,preferredJob:String?,selectedJob:String?,activeJob:String?,restoredJob:String?
    let sourceDuration:Double
}
struct WorkspacePreviewSnapshot {
    var path:String?,job:String?,activeVideo:String?
    var start=0.0,length=0.0,sourceExists=false,matches=false
    var config:[String:Any]=[:],rows:[[String:Any]]=[]
    var captions:[PreviewCaption]=[],profiles:[VoiceProfile]=[]
    /// Called only on the preview I/O queue. Network/cloud file waits cannot
    /// hold AppKit, and repeated refresh ticks do not queue duplicate scans.
    static func read(_ input:WorkspacePreviewInput)->Self {
        let activeConfig=input.activeJob.flatMap {ProcessingAudioIndex.read(URL(fileURLWithPath:$0).appendingPathComponent("review.json"))["config"] as? [String:Any]} ?? [:]
        let activeVideo=activeConfig["video"] as? String ?? input.activeJob.flatMap {ProcessingAudioIndex.read(URL(fileURLWithPath:$0).appendingPathComponent("processing-preview.json"))["video"] as? String}
        let saved=(activeVideo==input.video || input.preferredJob != nil || input.selectedJob != nil) ? nil:input.video.flatMap {SavedWorkspace.folder(root:input.root,video:$0,preferred:input.restoredJob)?.path}
        let job=(activeVideo==input.video ? input.activeJob:nil) ?? input.preferredJob ?? input.selectedJob ?? saved
        var result=Self(path:input.video,job:job,activeVideo:activeVideo,length:input.sourceDuration)
        if let job {
            let folder=URL(fileURLWithPath:job)
            let review=ProcessingAudioIndex.read(folder.appendingPathComponent("review.json"))
            let meta=ProcessingAudioIndex.read(folder.appendingPathComponent("processing-preview.json"))
            let cfg=review["config"] as? [String:Any] ?? [:]
            let active=cfg["video"] as? String ?? meta["video"] as? String
            if active==input.video || input.video==nil {
                result.matches=true
                result.config=cfg;result.path=active ?? input.video
                result.start=cfg["startOffset"] as? Double ?? meta["offset"] as? Double ?? 0
                result.length=cfg["duration"] as? Double ?? meta["duration"] as? Double ?? result.length
                result.rows=review["cues"] as? [[String:Any]] ?? ((try? Data(contentsOf:folder.appendingPathComponent("cues.json"))).flatMap {try? JSONSerialization.jsonObject(with:$0) as? [[String:Any]]} ?? [])
                result.captions=SavedWorkspace.captions(folder:folder)
                let voices=ProcessingAudioIndex.read(folder.appendingPathComponent("auto-speakers.json"))
                let independent=ProcessingAudioIndex.read(folder.appendingPathComponent("independent-voices.json"))
                let turns=(try? Data(contentsOf:folder.appendingPathComponent("turn-voices.json"))).flatMap {try? JSONSerialization.jsonObject(with:$0)}
                let configured=cfg["voiceProfiles"] as? [[String:Any]]
                if let raw=(configured?.isEmpty==false ? configured:nil) ?? (turns as? [[String:Any]]) ?? (independent["profiles"] as? [[String:Any]]) ?? (voices["profiles"] as? [[String:Any]]),let data=try? JSONSerialization.data(withJSONObject:raw) {result.profiles=(try? JSONDecoder().decode([VoiceProfile].self,from:data)) ?? []}
            }
        }
        if let path=result.path {result.sourceExists=FileManager.default.fileExists(atPath:path)}
        return result
    }
}
