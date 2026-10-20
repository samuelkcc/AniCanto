import Foundation

/// Explicit generation failures are distinct from pending work and quality hints.
@MainActor enum VoiceFailureEvidence {
    static func rows(timing:[[String:Any]],issues:[[String:Any]],engine:String,language:String)->[[String:Any]] {
        var failures:[Int:[String:Any]]=[:]
        var ready=Set<Int>()
        for row in timing {
            guard let index=row["index"] as? Int else{continue}
            let path=row["renderedAudio"] as? String ?? row["audio"] as? String
            let absent=(row["renderedSeconds"] as? Double ?? 0)>0 && (path.flatMap {ProcessingAudioIndex.length($0)}==nil)
            if row["skipped"] as? Bool==true || (row["renderedSeconds"] as? Double)==0 || absent {failures[index]=row}
            else if (row["renderedSeconds"] as? Double ?? 0)>0 {ready.insert(index)}
        }
        for issue in issues where issue["status"] as? String=="skipped" {
            guard let index=issue["index"] as? Int else{continue}
            if issue["kind"] as? String=="delivery-missing" || (failures[index]==nil && !ready.contains(index)) {failures[index]=issue}
        }
        return failures.keys.sorted().map {index in
            var row=failures[index]!
            let evidence=issues.filter {$0["index"] as? Int==index}
            var messages:[String]=[]
            for value in evidence.compactMap({$0["message"] as? String}) where !value.isEmpty && !messages.contains(value) {messages.append(value)}
            row["message"]=messages.isEmpty ? (row["message"] as? String ?? L("錄音缺失或無有效聲音；請查看生成紀錄。")):messages.joined(separator:" · ")
            row["engine"]=engine;row["language"]=language
            return row
        }
    }
}
