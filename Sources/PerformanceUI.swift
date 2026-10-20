import SwiftUI
struct PerformanceEvent: Decodable, Identifiable {
    var start: Double
    var end: Double
    var label: String
    var gain: Double?
    var id: String { "\(start)-\(end)" }
    var name: String { ["laughter":"笑聲","baby_laughter":"笑聲","belly_laugh":"大笑","crying_sobbing":"哭聲","sigh":"嘆氣／呻吟","breathing":"呼吸","gasp":"吸氣"][label] ?? label }
}
struct PerformanceReport: Decodable { var events: [PerformanceEvent]; var reviewEvents: [PerformanceEvent]? }
struct ValidationRow: Decodable, Identifiable {
    var index: Int
    var audibleStart: Double
    var text: String
    var requiresTimingReview: Bool
    var startError: Double?
    var endError: Double?
    var id: Int { index }
}
struct ValidationReport: Decodable {
    var qualityStatus: String
    var contentCheck: String
    var contentReviewIndices: [Int]
    var languageReviewIndices: [Int]?
    var scriptReviewIndices: [Int]?
    var voiceReviewIndices: [Int]?
    var sourceReviewIndices: [Int]?
    var speakerReviewIndices: [Int]?
    var nonverbalReviewCount: Int?
    var rows: [ValidationRow]
}
struct ValidationSummary: View {
    let output: URL
    let onPlay: (Double) -> Void
    private var report: ValidationReport? {
        guard let data = try? Data(contentsOf:outputReportURL(output,"validation.json")) else { return nil }
        return try? JSONDecoder().decode(ValidationReport.self,from:data)
    }
    var body: some View {
        if let report {
            DisclosureGroup(report.qualityStatus == "automatic-checks-passed" ? "自動檢查通過 · 可試聽確認" : "影片已輸出 · 有配音項目需要覆核") {
                VStack(alignment:.leading,spacing:8) {
                    Text(L("已檢查整條影片解碼同每句人聲。時間檢查根據聲音活動；AI 聽寫亦可能讀錯人名，唔代表已通過母語聽感或口形驗收。")).font(.caption).foregroundStyle(.secondary)
                    if report.contentCheck == "not-run" { Text(L("呢次未執行本機配音覆聽。")).font(.caption).foregroundStyle(.orange) }
                    if let count = report.nonverbalReviewCount, count > 0 { Text("另有 \(count) 段疑似笑聲／呼吸未完整保留；原聲混有對白，未自動補入。").font(.caption).foregroundStyle(.orange) }
                    ForEach(report.rows.filter { $0.requiresTimingReview || report.contentReviewIndices.contains($0.index) || (report.scriptReviewIndices ?? []).contains($0.index) || (report.voiceReviewIndices ?? []).contains($0.index) || (report.sourceReviewIndices ?? []).contains($0.index) || (report.speakerReviewIndices ?? []).contains($0.index) }) { row in
                        HStack {
                            VStack(alignment:.leading) {
                                Text("第 \(row.index) 句 · \(row.text)")
                                if row.requiresTimingReview { Text(String(format:"發聲起點偏差 %+.2f 秒 · 收尾偏差 %+.2f 秒",row.startError ?? 0,row.endError ?? 0)).foregroundStyle(.secondary) }
                                if (report.languageReviewIndices ?? []).contains(row.index) {Text(L("偵測語言與所選配音語言有差異，請試聽核對。")).foregroundStyle(.orange)}
                                if report.contentReviewIndices.contains(row.index) { Text(L("覆聽同台詞有差異：請核對有冇漏字或讀錯。")).foregroundStyle(.orange) }
                                if (report.scriptReviewIndices ?? []).contains(row.index) { Text(L("台詞需核對：口語用字、字數密度或疑似鄰句重複。")).foregroundStyle(.orange) }
                                if (report.voiceReviewIndices ?? []).contains(row.index) { Text(L("同角色聲線有差異，請比較前後句。")).foregroundStyle(.orange) }
                                if (report.sourceReviewIndices ?? []).contains(row.index) { Text(L("日語聽寫有分歧：原意未能確認。")).foregroundStyle(.orange) }
                                if (report.speakerReviewIndices ?? []).contains(row.index) { Text(L("角色身份未確定或參考原聲較短，請試聽聲線。")).foregroundStyle(.orange) }
                            }
                            Spacer()
                            Button(L("試聽")) { onPlay(max(0,row.audibleStart - 0.3)) }
                        }.font(.caption)
                    }
                }.padding(.top,8)
            }
        }
    }
}
struct PerformanceSummary: View {
    let output: URL
    let onPlay: (Double) -> Void
    private var events: [PerformanceEvent] {
        guard let data = try? Data(contentsOf:outputReportURL(output,"nonverbal-report.json")), let report = try? JSONDecoder().decode(PerformanceReport.self,from:data) else { return [] }
        return report.events
    }
    var body: some View {
        DisclosureGroup("保留嘅非語言聲音 · \(events.count) 段") {
            VStack(alignment:.leading,spacing:8) {
                Text(L("按原片時間補回；同新配音重疊時會降低音量。原本同日語對白混埋或未能可靠辨識嘅聲音，仍可能缺少。")).font(.caption).foregroundStyle(.secondary)
                ForEach(events) { e in
                    HStack { Text(String(format:"%02d:%05.2f – %02d:%05.2f",Int(e.start)/60,e.start.truncatingRemainder(dividingBy:60),Int(e.end)/60,e.end.truncatingRemainder(dividingBy:60))).monospacedDigit(); Text(e.name); if (e.gain ?? 1)<1 { Text(L("重疊部分已降低音量")).foregroundStyle(.secondary) }; Spacer(); Button(L("播放呢段")) { onPlay(e.start) } }.font(.caption)
                }
            }.padding(.top,8)
        }
    }
}

func outputReportURL(_ output: URL, _ name: String) -> URL {
    let sidecar = output.deletingLastPathComponent().appendingPathComponent(output.deletingPathExtension().lastPathComponent + "." + name)
    return FileManager.default.fileExists(atPath:sidecar.path) ? sidecar : output.deletingLastPathComponent().appendingPathComponent(name)
}
