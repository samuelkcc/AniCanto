import Foundation

@main struct DraftStoreTests {
    static func main() throws {
        let source: [[String:Any]] = [["start":1.0,"end":2.0,"text":"待て","cantonese":"企定","japaneseAlt":"待って","acousticParts":[["start":1.1,"end":1.9]],"deliveryPlan":[["text":"企定"]]]]
        let edited: [[String:Any]] = [["start":1.0,"end":2.0,"text":"待て","cantonese":"唔好郁","enabled":true]]
        let merged = try DraftStore.mergeEdits(original: source, edited: edited)
        precondition(merged[0]["japaneseAlt"] as? String == "待って")
        precondition(merged[0]["acousticParts"] != nil && merged[0]["deliveryPlan"] == nil)
        precondition(merged[0]["cantonese"] as? String == "唔好郁")
        precondition(OutputStore.isOutputName("影片-AniCanto.mp4"))
        precondition(OutputStore.isOutputName("廣東話配音.mp4"))
        precondition(!OutputStore.isOutputName("output.partial.mp4"))
        precondition(!OutputStore.isOutputName("原片.mp4"))
        precondition(OutputStore.isOutputName("影片-AniCanto (2).mp4"))
        precondition(!OutputStore.isOutputName("影片-AniCanto (2).mp4.backup"))
        let fm = FileManager.default
        let root = fm.temporaryDirectory.appendingPathComponent("canto-draft-test-\(UUID().uuidString)")
        defer { try? fm.removeItem(at: root) }
        let jobs = root.appendingPathComponent("jobs"), job = jobs.appendingPathComponent("abc")
        try fm.createDirectory(at: job, withIntermediateDirectories: true)
        let names = ["review.json", "cues.json", "timing.json", "duration-edits.json", "廣東話配音.mp4", "cantonese.srt", "report.json", "cosyvoice3-cached.wav"]
        for name in names { try Data(name.utf8).write(to: job.appendingPathComponent(name)) }
        try Data("{}".utf8).write(to: job.appendingPathComponent("duration-attempts.json"))
        let review = job.appendingPathComponent("review.json")
        enum Failure: Error { case refused }
        do {
            try DraftStore.trash(review, jobs: jobs) { _ in throw Failure.refused }
            fatalError("should fail")
        } catch Failure.refused {}
        for name in names { precondition(fm.fileExists(atPath: job.appendingPathComponent(name).path), "rollback lost \(name)") }
        let trash = root.appendingPathComponent("trash")
        try DraftStore.trash(review, jobs: jobs) { try fm.moveItem(at: $0, to: trash) }
        for name in names.prefix(4) { precondition(fm.fileExists(atPath: trash.appendingPathComponent(name).path)); precondition(!fm.fileExists(atPath: job.appendingPathComponent(name).path)) }
        precondition(fm.fileExists(atPath: trash.appendingPathComponent("duration-attempts.json").path), "fresh draft must reset automatic retry budget")
        for name in names.suffix(4) { precondition(fm.fileExists(atPath: job.appendingPathComponent(name).path), "export/cache deleted") }
        let outside = root.appendingPathComponent("outside"); try fm.createDirectory(at: outside, withIntermediateDirectories: true)
        try Data("source".utf8).write(to: outside.appendingPathComponent("review.json"))
        let link = jobs.appendingPathComponent("symlink")
        try fm.createSymbolicLink(at: link, withDestinationURL: outside)
        do {
            try DraftStore.trash(link.appendingPathComponent("review.json"), jobs: jobs) { _ in fatalError("followed symlink") }
            fatalError("accepted escaped job")
        } catch {}
        precondition(fm.fileExists(atPath: outside.appendingPathComponent("review.json").path))
        print("PASS: draft trash, rollback, preservation of exports/audio, symlink escape rejected")
    }
}
