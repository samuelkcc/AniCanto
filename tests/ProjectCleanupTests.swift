import Foundation
func runCleanupChecks(root:URL) throws {
    let fm=FileManager.default
    for mode in [CleanupMode.outputs,.projects,.all] {
        let data=root.appendingPathComponent("cleanup-"+mode.rawValue),jobs=data.appendingPathComponent("jobs"),job=jobs.appendingPathComponent("one")
        try fm.createDirectory(at:job,withIntermediateDirectories:true)
        let source=data.appendingPathComponent("original-AniCanto.mp4"),export=data.appendingPathComponent("export-AniCanto.mp4"),internalMovie=job.appendingPathComponent("one-AniCanto.mp4"),model=data.appendingPathComponent("models/weight.bin"),reference=job.appendingPathComponent("role.wav")
        try fm.createDirectory(at:model.deletingLastPathComponent(),withIntermediateDirectories:true)
        for file in [source,export,internalMovie,model,reference] {try Data(file.lastPathComponent.utf8).write(to:file)}
        let review=job.appendingPathComponent("review.json")
        try JSONSerialization.data(withJSONObject:["config":["video":source.path],"cues":[],"status":"complete"]).write(to:review)
        try JSONSerialization.data(withJSONObject:["output":internalMovie.path,"exportedOutput":export.path]).write(to:job.appendingPathComponent("report.json"))
        let version=job.appendingPathComponent("versions/invalid")
        try fm.createDirectory(at:version,withIntermediateDirectories:true)
        try JSONSerialization.data(withJSONObject:["output":source.path]).write(to:version.appendingPathComponent("version.json"))
        try JSONSerialization.data(withJSONObject:[["id":"role","name":"role","reference":reference.path,"promptText":"原文"]]).write(to:data.appendingPathComponent("voice-profiles.json"))
        for name in ["batch-queue.json","editor-queue.json","batch-submissions.json"] {try Data("[1]".utf8).write(to:data.appendingPathComponent(name))}
        let cache=data.appendingPathComponent("separations");try fm.createDirectory(at:cache,withIntermediateDirectories:true);try Data("cache".utf8).write(to:cache.appendingPathComponent("stem.wav"))
        let db=try ProjectDatabase(root:data);try db.sync(review:review,output:export)
        let plan=try ProjectCleanupPlan(root:data,mode:mode)
        precondition(!plan.outputs.contains(source))
        let trash=data.appendingPathComponent("test-trash");try fm.createDirectory(at:trash,withIntermediateDirectories:true)
        _ = try plan.execute {file in try fm.moveItem(at:file,to:trash.appendingPathComponent(UUID().uuidString+"-"+file.lastPathComponent))}
        precondition(fm.fileExists(atPath:source.path) && fm.fileExists(atPath:model.path))
        if mode == .outputs {
            precondition(fm.fileExists(atPath:review.path) && !fm.fileExists(atPath:export.path));let deleted=try db.isRemoved(export);precondition(deleted)
        } else {
            precondition(!fm.fileExists(atPath:job.path))
            let profiles=try JSONSerialization.jsonObject(with:Data(contentsOf:data.appendingPathComponent("voice-profiles.json"))) as! [[String:Any]]
            let saved=profiles[0]["reference"] as! String;precondition(fm.fileExists(atPath:saved) && saved.contains("saved-role-recordings"))
            if mode == .projects {
                precondition(fm.fileExists(atPath:export.path));let rows=try db.rows("SELECT path FROM outputs");precondition(rows.contains{ $0.first==export.path })
            } else {
                precondition(!fm.fileExists(atPath:export.path) && !fm.fileExists(atPath:cache.path))
                let rows=try db.rows("SELECT * FROM projects");precondition(rows.isEmpty)
                for name in ["batch-queue.json","editor-queue.json","batch-submissions.json"] {let bytes=try Data(contentsOf:data.appendingPathComponent(name));precondition(bytes==Data("[]".utf8))}
            }
        }
    }
    print("PASS: cleanup scopes, source/model preservation, MP4 tombstones, kept-export indexing, role recording preservation, empty restart queues")
}
