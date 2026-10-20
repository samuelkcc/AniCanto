import SwiftUI

/// Persisted worker accounting excludes idle time between resumed runs.
enum ProductionTiming {
    static func seconds(folder:URL?)->Double? {
        guard let folder,let seconds=ProcessingAudioIndex.read(folder.appendingPathComponent("processing-time.json"))["seconds"] as? Double,seconds.isFinite,seconds>0 else{return nil}
        return seconds
    }
    static func breakdown(folder:URL?,output:URL?)->String {
        let path=output.map {$0.deletingPathExtension().appendingPathExtension("processing-time.json")} ?? folder?.appendingPathComponent("processing-time.json")
        guard let path,let rows=ProcessingAudioIndex.read(path)["milestones"],let data=try? JSONSerialization.data(withJSONObject:rows),let milestones=try? JSONDecoder().decode([ProductionMilestone].self,from:data) else {return L("此成品未有階段耗時紀錄")}
        return milestones.map {$0.title+" · "+$0.duration}.joined(separator:"\n")
    }
    static func seconds(output:URL)->Double? {
        let timing=ProcessingAudioIndex.read(output.deletingPathExtension().appendingPathExtension("processing-time.json"))
        if let seconds=timing["seconds"] as? Double,seconds.isFinite,seconds>0 {return seconds}
        let report=ProcessingAudioIndex.read(output.deletingPathExtension().appendingPathExtension("report.json"))
        return (report["processingSeconds"] as? Double).flatMap {$0.isFinite && $0>0 ? $0:nil}
    }
}
struct ProductionDurationLabel:View {
    var folder:URL?=nil
    var output:URL?=nil
    var fallbackSeconds:Double=0
    var body:some View {
        TimelineView(.periodic(from:.now,by:2)) {_ in
            if let seconds=output.flatMap({ProductionTiming.seconds(output:$0)}) ?? ProductionTiming.seconds(folder:folder) ?? (fallbackSeconds>0 ? fallbackSeconds:nil) {
                Text(L("總轉換時間：")+studioTimecode(seconds)).font(.caption.monospacedDigit()).foregroundStyle(.secondary)
                    .help(ProductionTiming.breakdown(folder:folder,output:output))
            } else if output != nil {Text(L("此成品未有時間紀錄")).font(.caption).foregroundStyle(.secondary)}
        }
    }
}
struct ProductionTimeStatus:View {
    @ObservedObject var model:AppModel
    var compact=false
    var body:some View {
        TimelineView(.periodic(from:.now,by:1)) {context in
            let root=model.displayJourney.map {URL(fileURLWithPath:$0.job)} ?? model.activePreviewJob.map {URL(fileURLWithPath:$0)} ?? model.projectEditor.selectedRow?.review?.deletingLastPathComponent() ?? model.projectEditor.selectedRow?.previewJob
            let record=root.map {ProcessingAudioIndex.read($0.appendingPathComponent("processing-time.json"))} ?? [:]
            let total=ProductionTiming.seconds(folder:root) ?? model.processingClock.elapsed(at:context.date)
            let run=(record["currentRunSeconds"] as? Double) ?? (record["runs"] as? [[String:Any]])?.last?["seconds"] as? Double
            let runs=(record["runs"] as? [[String:Any]])?.count ?? 1
            VStack(alignment:compact ? .trailing:.leading,spacing:compact ? 2:4) {
                HStack(spacing:10) {
                    Text(L("累計處理：")+studioTimecode(total))
                    if runs>1,let run {Text(L("本次：")+studioTimecode(run))}
                }.monospacedDigit().help(L("包括模型載入、等待及重試；累計包含之前續跑，暫停後程序結束至下次續跑之間不計時。"))
                if model.busy {
                    if let remaining=model.processingClock.overallRemaining(at:context.date),remaining>0 {
                        Text(L("整個工作預計剩餘：")+studioTimecode(remaining*0.7)+" – "+studioTimecode(remaining*1.5))
                    } else if let remaining=model.processingClock.remaining(at:context.date),remaining>0,!model.processingClock.estimateDelayed(at:context.date) {
                        Text(L("本階段預計剩餘：")+studioTimecode(remaining*0.8)+" – "+studioTimecode(remaining*1.3))
                        if !compact {Text(L(model.processingClock.estimateBasis(at:context.date)))}
                    } else {Text(L(model.processingClock.estimateDelayed(at:context.date) ? model.processingClock.estimateBasis(at:context.date):model.processingClock.waitingReason))}
                }
            }.font(.caption).foregroundStyle(.secondary).fixedSize(horizontal:false,vertical:true)
        }.frame(minHeight:compact ? (model.busy ? 30:16):(model.busy ? 42:20),alignment:compact ? .topTrailing:.topLeading)
    }
}
