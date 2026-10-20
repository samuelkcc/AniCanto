import Foundation

/// Resume browsing partial work without starting the conversion worker.
enum SavedWorkspace {
    private static var folders:[String:URL]=[:]
    private static let lock=NSLock()
    static func folder(root:URL,video:String,preferred:String?)->URL? {
        func matches(_ folder:URL)->Bool {
            guard let data=try? Data(contentsOf:folder.appendingPathComponent("processing-preview.json")),let meta=try? JSONSerialization.jsonObject(with:data) as? [String:Any] else{return false}
            return meta["video"] as? String==video
        }
        func remember(_ candidate:URL) {lock.lock();folders[root.path+video]=candidate;lock.unlock()}
        if let preferred {let candidate=URL(fileURLWithPath:preferred);if matches(candidate) {remember(candidate);return candidate}}
        lock.lock();let cached=folders[root.path+video];lock.unlock()
        if let cached,matches(cached) {return cached}
        let jobs=(try? FileManager.default.contentsOfDirectory(at:root.appendingPathComponent("jobs"),includingPropertiesForKeys:[.contentModificationDateKey])) ?? []
        let candidates=jobs.filter(matches).sorted {a,b in
            let date:(URL)->Date={url in (try? url.appendingPathComponent("cues.json").resourceValues(forKeys:[.contentModificationDateKey]).contentModificationDate) ?? .distantPast}
            return date(a)>date(b)
        }
        if let candidate=candidates.first {remember(candidate);return candidate}
        return nil
    }
    static func captions(folder:URL)->[PreviewCaption] {
        guard let data=try? Data(contentsOf:folder.appendingPathComponent("subtitle-context.json")),let rows=try? JSONSerialization.jsonObject(with:data) as? [[String:Any]] else{return []}
        return rows.compactMap {row in
            guard let a=row["start"] as? Double,let b=row["end"] as? Double,let text=row["text"] as? String,a.isFinite,b.isFinite,b>a else{return nil}
            return PreviewCaption(start:a,end:b,text:text)
        }
    }
}
