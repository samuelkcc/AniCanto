import SwiftUI
import AVKit

struct WorkspaceControlPanel:View {
    @ObservedObject var model:AppModel
    @ObservedObject var editor:ProjectEditor
    var showPlayback=true
    var body:some View {
        VStack(alignment:.leading,spacing:7) {
            if showPlayback {HStack {
                Button(L("原片"),action:editor.playSource).disabled(editor.document==nil)
                Button {if editor.player.rate==0 {editor.player.play()} else {editor.player.pause()}} label:{Label(L("播放／暫停"),systemImage:"playpause.fill")}.disabled(editor.document==nil)
                Spacer();Text(String(format:"%.1fs",editor.seconds)).font(.caption.monospacedDigit())
            }
            if model.workspaceControlTab=="play" {Slider(value:Binding(get:{min(editor.outputDuration,editor.seconds)},set:{editor.seek($0)}),in:0...max(1,editor.outputDuration)).disabled(editor.document==nil)}
            Picker(L("控制面板"),selection:$model.workspaceControlTab) {Text(L("播放／配音")).tag("play");Text(L("全局設定")).tag("settings")}.pickerStyle(.segmented)}
            if showPlayback && model.workspaceControlTab=="play" {playback} else {settings}
            Spacer(minLength:0)
        }.padding(10).background(surface,in:RoundedRectangle(cornerRadius:10)).clipped()
    }
    var playback:some View {
        VStack(alignment:.leading,spacing:7) {
            Picker(L("成品版本"),selection:Binding(get:{editor.playingVersion ?? "source"},set:{v in if v=="source" {editor.playSource()} else if let version=editor.versions.first(where:{$0.id==v}) {editor.play(version)}})) {
                Text(L("原片＋編輯字幕")).tag("source")
                ForEach(editor.versions.filter{$0.output != nil}) {v in Text(v.id=="original" ? L("原始成品"):String(v.created.prefix(19))).tag(v.id)}
            }
            if editor.playingVersion != nil {PlayerTrackControls(player:editor.player)}
            else {
                HStack {
                    Button {editor.playSegment()} label:{Image(systemName:"waveform")}.help(L("原聲")).disabled(editor.segmentIndex==nil)
                    ForEach(VoiceEngineChoice.all) {engine in
                        Button(engine.id=="cosyvoice3" ? "Cosy":engine.id=="gpt-sovits" ? "GPT":"Qwen") {
                            editor.previewEngine=engine.id
                            if editor.deliveredTake(engine.id) != nil {editor.playEngine(engine.id)} else {model.generateAndPlayEditor(engine.id)}
                        }.help(L(editor.deliveredTake(engine.id)==nil ? "生成並播放呢段":"播放呢段配音"))
                        .disabled(editor.segmentIndex==nil || (model.busy && editor.deliveredTake(engine.id)==nil))
                    }
                    Button {editor.audio.pause();editor.player.pause();editor.auditionLabel=""} label:{Image(systemName:"stop.fill")}
                }
                HStack {
                    Picker(L("採用引擎"),selection:$editor.previewEngine) {ForEach(VoiceEngineChoice.all) {Text($0.shortTitle).tag($0.id)}}.labelsHidden()
                    Button(L("採用錄音")) {editor.playEngine(editor.previewEngine,use:true)}.disabled(editor.deliveredTake(editor.previewEngine)==nil)
                }
            }
            Toggle(L("循環片段"),isOn:$editor.looping).toggleStyle(.checkbox)
            if !editor.auditionLabel.isEmpty {Text(editor.auditionLabel).font(.caption2).foregroundStyle(accent).lineLimit(1)}
            if !editor.failedTracks.isEmpty || !editor.segmentIssues.isEmpty {Button(L("重試未完成配音")) {model.repairMissingTracks()}.disabled(model.busy)}
        }
    }
    var settings:some View {
        VStack(alignment:.leading,spacing:6) {
            Picker(L("配音語言"),selection:$model.dubMode) {Text(L("廣東話")).tag("yue");Text(L("英文")).tag("en");Text(L("雙語")).tag("both")}.pickerStyle(.segmented)
            OpeningTreatmentControls(detect:$model.autoSkipOP,translate:$model.translateOPED)
            HStack {ForEach(VoiceEngineChoice.all) {choice in
                Toggle(choice.shortTitle,isOn:Binding(get:{model.selectedEngines.contains(choice.id)},set:{value in if value {model.extraEngines.insert(choice.id)} else if choice.id != model.ttsBackend {model.extraEngines.remove(choice.id)}})).toggleStyle(.checkbox).disabled(choice.id==model.ttsBackend)
            }}
            Picker(L("處理範圍"),selection:$model.limit) {Text(L("60 秒")).tag(60);Text(L("3 分鐘")).tag(180);Text(L("全片")).tag(0)}.pickerStyle(.segmented)
            Toggle(L("自動批核字幕並配音"),isOn:$model.autoApprove).toggleStyle(.checkbox)
            HStack {Button(L("全部設定…")) {model.showWorkspaceSettings=true};Button(L("輸出位置…"),action:model.chooseExportFolder)}
            Button(L("儲存製作預設"),action:model.saveStudioPreset)
            if let saved=model.presetSavedAt {Text(L("預設已儲存")+" · "+saved.formatted(date:.omitted,time:.shortened)).font(.caption).foregroundStyle(.secondary)}
        }.disabled(model.busy)
    }
}
struct CompactWorkspaceStatus:View {
    @ObservedObject var model:AppModel
    var body:some View {
        VStack(alignment:.leading,spacing:8) {
            if !model.busy,model.batchNeedsAttention {
                HStack {
                    Label(String(format:L("%d 條影片未完成；其他影片已繼續處理。"),model.batchItems.filter {$0.status=="需要處理" && !$0.message.isEmpty}.count),systemImage:"exclamationmark.triangle").foregroundStyle(.orange)
                    Spacer()
                    Button(L("查看錯誤摘要")) {model.showLogs=true}
                }.font(.system(size:14))
            }
            HStack(spacing:14) {
                if model.busy && model.progress==nil {ProgressView().controlSize(.regular)}
                Text(localizedProgressDetail(model.stage)).font(.system(size:16,weight:.semibold))
                Text(localizedProgressDetail(model.detail)).font(.system(size:14)).lineLimit(1).frame(maxWidth:.infinity,alignment:.leading)
                if let value=model.progress {Text("\(Int(min(1,max(0,value))*100))%").font(.system(size:16,weight:.semibold,design:.monospaced))}
                
            }
            if model.processingClock.started != nil {
                TimelineView(.periodic(from:.now,by:1)) {context in
                    HStack(spacing:24) {
                        Label(L("已用時間：")+ProcessingClock.duration(model.processingClock.elapsed(at:context.date),english:appInterfaceLocale.identifier.hasPrefix("en")),systemImage:"clock")
                        if model.busy {
                            Text(L("本階段已用時間：")+ProcessingClock.duration(model.processingClock.phaseElapsed(at:context.date),english:appInterfaceLocale.identifier.hasPrefix("en")))
                            if let fraction=model.processingClock.passProgress {Text(L("本階段進度：")+String(format:"%.0f%%",fraction*100)+" · "+model.processingClock.passLabel)}
                            if let remaining=model.processingClock.remaining(at:context.date), remaining>0 {
                                Text(L("本階段預計剩餘：")+ProcessingClock.duration(remaining*0.8,english:appInterfaceLocale.identifier.hasPrefix("en"))+" – "+ProcessingClock.duration(remaining*1.3,english:appInterfaceLocale.identifier.hasPrefix("en")))
                                    .help(L(model.processingClock.estimateBasis(at:context.date)))
                                if model.processingClock.estimateDelayed(at:context.date) {Text(L(model.processingClock.estimateBasis(at:context.date)))}
                            } else {Text(L(model.processingClock.estimateDelayed(at:context.date) ? model.processingClock.estimateBasis(at:context.date):model.processingClock.waitingReason))}
                        }
                        Spacer(minLength:0)
                    }.font(.system(size:13)).foregroundStyle(.secondary).monospacedDigit()
                }
            } else if model.projectEditor.generationSeconds>0 {
                Text(L("已保存生成時間：")+ProcessingClock.duration(model.projectEditor.generationSeconds,english:appInterfaceLocale.identifier.hasPrefix("en"))).font(.system(size:13)).foregroundStyle(.secondary)
            }
            if let transfer=model.downloadTransfer {
                HStack(spacing:20) {
                    Text(transfer.stateTitle).fontWeight(.semibold)
                    Text(transfer.sizeText).monospacedDigit()
                    Text(L("下載速度")+": "+transfer.speedText).monospacedDigit()
                    Text(L("目前檔案剩餘時間")+": "+transfer.remainingText).monospacedDigit()
                    Spacer()
                    if transfer.attempt>1 {Text(L("連線嘗試")+" \(transfer.attempt)/5")}
                }.font(.system(size:14)).foregroundStyle(.secondary)
            }
            if let value=model.progress {
                GeometryReader {g in ZStack(alignment:.leading) {Capsule().fill(accent.opacity(0.15));Capsule().fill(accent).frame(width:g.size.width*min(1,max(0,value)))}}.frame(height:10).accessibilityValue("\(Int(min(1,max(0,value))*100))%")
            }
        }.padding(.horizontal,18).padding(.vertical,12).background(surface)
    }
}
