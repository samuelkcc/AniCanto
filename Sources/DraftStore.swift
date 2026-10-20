import Foundation

enum DraftStore {
    static func mergeEdits(original: [[String:Any]], edited: [[String:Any]]) throws -> [[String:Any]] {
        guard original.count == edited.count else {
            throw NSError(domain:"AniCanto",code:2,userInfo:[NSLocalizedDescriptionKey:"校稿句數有變，請重新載入。"])
        }
        return try zip(original, edited).map { old, edit in
            guard old["text"] as? String == edit["text"] as? String,
                  old["start"] as? Double == edit["start"] as? Double,
                  old["end"] as? Double == edit["end"] as? Double else {
                throw NSError(domain:"AniCanto",code:3,userInfo:[NSLocalizedDescriptionKey:"原聲時間或台詞有變，請重新載入。"])
            }
            var merged = old
            for key in ["cantonese", "enabled", "speakerId"] {
                if let value = edit[key] { merged[key] = value }
            }
            if old["cantonese"] as? String != edit["cantonese"] as? String {
                merged.removeValue(forKey:"deliveryPlan")
                merged.removeValue(forKey:"deliveryParts")
            }
            return merged
        }
    }

    /// Move editable draft data together, keeping source media, models, cached audio and exports.
    static func trash(_ review: URL, jobs: URL, moveToTrash: (URL) throws -> Void = { url in
        try FileManager.default.trashItem(at: url, resultingItemURL: nil)
    }) throws {
        let fm = FileManager.default
        let folder = review.deletingLastPathComponent().standardizedFileURL
        guard review.lastPathComponent == "review.json",
              folder.resolvingSymlinksInPath().deletingLastPathComponent() == jobs.resolvingSymlinksInPath().standardizedFileURL,
              try review.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey]).isRegularFile == true,
              try review.resourceValues(forKeys: [.isSymbolicLinkKey]).isSymbolicLink != true else {
            throw NSError(domain: "AniCanto", code: 1, userInfo: [NSLocalizedDescriptionKey: "只可以清除工作紀錄入面嘅校稿。"])
        }
        let files = try fm.contentsOfDirectory(at: folder, includingPropertiesForKeys: nil).filter {
            ["review.json", "cues.json", "timing.json", "duration-edits.json", "duration-attempts.json",
             "register-edits.json", "script-preflight.json", "script-preflight-cache.json",
             "caption-allocation.json", "rejected-duration-edits.json"].contains($0.lastPathComponent)
            || (["duration-candidates-", "duration-semantic-check-", "duration-rejected-"].contains(where: $0.lastPathComponent.hasPrefix) && $0.pathExtension == "json")
        }
        let bundle = jobs.deletingLastPathComponent().appendingPathComponent("AniCanto-校稿-\(folder.lastPathComponent)-\(UUID().uuidString)")
        try fm.createDirectory(at: bundle, withIntermediateDirectories: false)
        var moved: [URL] = []
        do {
            for file in files {
                try fm.moveItem(at: file, to: bundle.appendingPathComponent(file.lastPathComponent))
                moved.append(file)
            }
            try moveToTrash(bundle)
        } catch {
            // Failed trash operations must leave the draft usable, not half deleted.
            for file in moved.reversed() {
                try fm.moveItem(at: bundle.appendingPathComponent(file.lastPathComponent), to: file)
            }
            try? fm.removeItem(at: bundle)
            throw error
        }
    }
}

enum OutputStore {
    static func isOutputName(_ name: String) -> Bool {
        name == "廣東話配音.mp4" || name.range(of:#"-(?:AniCanto|CantoSync)(?: \([1-9][0-9]*\))?\.mp4$"#,options:.regularExpression) != nil
    }
}
