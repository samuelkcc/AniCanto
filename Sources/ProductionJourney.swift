import SwiftUI

struct ProductionMilestone:Codable,Identifiable {
    var id:String
    var state:String
    var seconds:Double
    var title:String {L(["prepare":"準備","recognition":"日語辨識","roles":"角色分析","translation":"翻譯","voice":"配音","repair":"修復／核對","export":"匯出"][id] ?? id)}
    var checkpointTitle:String {id=="repair" ? L("修復／核對（關卡）"):title}
    var complete:Bool {state=="complete"}
    var icon:String {complete ? "checkmark.circle.fill":state=="running" ? "circle.inset.filled":state=="skipped" ? "forward.circle":state=="prepared" ? "checkmark.circle":state=="saved" ? "waveform.circle":"circle"}
    var duration:String {
        if state=="skipped" {return L("已略過")}
        if state=="prepared" && seconds<1 {return L("已有資料")}
        if state=="saved" && seconds<1 {return L("已有錄音")}
        if complete && seconds<1 {return L("少於 1 秒")}
        return seconds>0 ? studioTimecode(seconds):"—"
    }
    var checkpointDuration:String {
        guard seconds>=1 else {return duration}
        let whole=Int(seconds),hours=Int(seconds)/3600
        return hours>0 ? String(format:"%d:%02d:%02d",hours,(whole/60)%60,whole%60):String(format:"%02d:%02d",whole/60,whole%60)
    }
}
struct ProductionJourney:Codable {
    var version:Int
    var job:String
    var progress:Double
    var milestones:[ProductionMilestone]
    var complete:Bool
    var resumed:Bool?
    var qualityStatus:String?
    static func restored(folder:URL)->ProductionJourney? {
        guard let data=try? Data(contentsOf:folder.appendingPathComponent("production-progress.json")),var journey=try? JSONDecoder().decode(Self.self,from:data) else{return nil}
        // Older builds used QA warnings to leave an already published movie
        // at 94%. Correct only the display, using evidence of a finished run.
        let timing=ProcessingAudioIndex.read(folder.appendingPathComponent("processing-time.json"))
        let last=(timing["runs"] as? [[String:Any]])?.last
        let report=ProcessingAudioIndex.read(folder.appendingPathComponent("report.json"))
        if !journey.complete,journey.progress>=0.94,last?["status"] as? String=="finished",let output=report["exportedOutput"] as? String ?? report["output"] as? String,FileManager.default.fileExists(atPath:output),let i=journey.milestones.firstIndex(where:{$0.id=="export" && $0.seconds>0}) {
            journey.progress=1;journey.complete=true;journey.milestones[i].state="complete"
            journey.qualityStatus=report["qualityStatus"] as? String ?? "needs-review"
        }
        return journey
    }
}

extension AppModel {
    var displayJourney:ProductionJourney? {
        if busy {return productionJourney}
        if let folder=projectEditor.selectedRow?.review?.deletingLastPathComponent() ?? projectEditor.selectedRow?.previewJob,let saved=ProductionJourney.restored(folder:folder) {return saved}
        return productionJourney
    }
    var displayProgress:Double? {displayJourney?.progress ?? progress}
}

/// Basic mode has checkpoints beneath the theme assistant's path. Expert mode
/// uses a compact status strip. Both read the exact same worker-owned journey.
struct ProductionMilestones:View {
    var journey:ProductionJourney?
    var playful=false
    var body:some View {
        if let journey {
            HStack(alignment:.top,spacing:playful ? 8:12) {
                ForEach(journey.milestones.filter { !playful || !["roles","repair"].contains($0.id) }) {row in
                    if playful {
                        VStack(spacing:4) {
                            HStack(spacing:4) {
                                Image(systemName:row.complete ? "flag.checkered.circle.fill":row.state=="running" ? "flag.circle.fill":row.icon).font(.system(size:14))
                                Text(row.checkpointTitle).font(.system(size:11,weight:row.state=="running" ? .bold:.medium)).lineLimit(1).minimumScaleFactor(0.8)
                            }
                            Text(row.checkpointDuration).font(.system(size:10).monospacedDigit()).foregroundStyle(.secondary)
                        }.frame(maxWidth:.infinity).padding(.vertical,7)
                        .background(row.state=="running" ? accent.opacity(0.12):Color.clear,in:RoundedRectangle(cornerRadius:10))
                        .foregroundStyle(row.complete || row.state=="running" ? accent:Color.secondary)
                        .help(row.title+" · "+row.duration)
                        .accessibilityLabel(row.title+" · "+row.duration)
                    } else {
                        HStack(spacing:5) {
                            Image(systemName:row.icon).foregroundStyle(row.complete || row.state=="running" ? accent:Color.secondary)
                            Text(row.title).fontWeight(row.state=="running" ? .semibold:.regular)
                            Text(row.duration).monospacedDigit().foregroundStyle(.secondary)
                        }.font(.system(size:11)).frame(maxWidth:.infinity,alignment:.leading)
                    }
                }
            }.accessibilityElement(children:.combine)
        }
    }
}
