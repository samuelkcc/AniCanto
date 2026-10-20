import SwiftUI
import AppKit

/// Information is a transient side panel; the workspace remains mounted beneath it.
struct StudioInformationDrawer:View {
    @Binding var about:Bool
    @Binding var guide:Bool
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    private var visible:Bool {about || guide}
    func close() {about=false;guide=false}
    var body:some View {
        GeometryReader {g in
            ZStack(alignment:.trailing) {
                if visible {
                    Color.black.opacity(0.24).ignoresSafeArea().onTapGesture(perform:close)
                        .accessibilityLabel(L("關閉面板"))
                        .transition(.opacity)
                    Group {
                        if about {AboutStudioWindow(close:close)}
                        else {StudioTutorial(close:close)}
                    }
                    .frame(width:min(780,max(360,g.size.width*0.62)),height:g.size.height)
                    .background(StudioPalette.panel)
                    .overlay(alignment:.leading) {Rectangle().fill(StudioPalette.border).frame(width:1)}
                    .shadow(color:.black.opacity(0.15),radius:24,x:-8,y:0)
                    .transition(.move(edge:.trailing))
                    .accessibilityAddTraits(.isModal)
                }
            }.frame(maxWidth:.infinity,maxHeight:.infinity,alignment:.trailing)
            .animation(reduceMotion ? nil:.easeInOut(duration:0.25),value:visible)
        }.allowsHitTesting(visible)
    }
}

struct StudioSectionTitle:View {
    @AppStorage("studioLanguage") private var interfaceLanguage="system"
    var number:String
    var title:String
    var detail:String=""
    var body:some View {
        VStack(alignment:.leading,spacing:6) {
            HStack(spacing:9) {
                Text(number).font(.system(size:11,weight:.bold,design:.monospaced)).foregroundStyle(accent)
                    .frame(width:26,height:26).background(accent.opacity(0.09),in:RoundedRectangle(cornerRadius:7))
                Text(L(title)).font(.headline)
            }
            if !detail.isEmpty {Text(L(detail)).font(.caption).foregroundStyle(.secondary).fixedSize(horizontal:false,vertical:true)}
        }
    }
}

extension SimpleWorkspace {
    var previewHeading:some View {
        HStack(alignment:.top,spacing:12) {
            VStack(alignment:.leading,spacing:6) {
                Text(L("預覽與試聽")).font(.system(size:24,weight:.bold,design:.rounded))
                Menu {
                    ForEach(editor.projects) {row in Button(row.name) {editor.open(row);refreshPreview()}}
                } label:{
                    Text(editor.selectedRow?.name ?? L("放入影片，交畀 AniCanto"))
                        .font(.callout).lineLimit(2)
                }.menuStyle(.borderlessButton).fixedSize(horizontal:false,vertical:true)
                    .foregroundStyle(.secondary).help(source ?? L("專案庫"))
            }
            Spacer(minLength:8)
            Button(action:importVideos) {Label(L("加入影片"),systemImage:"plus")}
                .disabled(model.busy || model.simpleQueuePreparing)
        }
    }
    var productionProgress:some View {
        SimpleProcessingProgress(model:model,ready:live.takes.filter {take in
            take.engine==selectedEngine && playbackLanguages.contains(take.language) && live.cues.contains {cue in
                abs(cue.start-take.start)<0.001 && abs(cue.end-take.end)<0.001 && cue.text(take.language)==take.text && cue.speakerID==take.speakerID
            }
        }.count,languages:playbackLanguages,incomplete:model.batchItems.first(where:{$0.video==source})?.status=="需要處理")
    }
    var productionSidebar:some View {
        VStack(alignment:.leading,spacing:0) {
            HStack {Text(L("製作設定")).font(.title3.bold());Spacer();Image(systemName:"sparkles").foregroundStyle(accent)}.padding(22)
            Divider()
            ScrollView {quickSetup.padding(22)}
            Divider()
            VStack(alignment:.leading,spacing:14) {
                Label(L(plan.productionMode=="fast" ? "自動翻譯 → 配音 → 輸出":"自動翻譯 · 修復 · 匯出"),systemImage:plan.productionMode=="fast" ? "bolt":"wand.and.stars").font(.caption).foregroundStyle(.secondary)
                startProductionButton
                if !model.busy,model.simpleBatchPending.count>1 {
                    Button {model.submitSimpleBatch(plan,selectedVideo:source)} label:{
                        Text(L("開始全部待處理")+" (\(model.simpleBatchPending.count))").frame(maxWidth:.infinity)
                    }.disabled(model.simpleQueuePreparing || !model.engineReady(selectedEngine) || originalsLoading)
                }
                if pendingHere || model.busy {Text(L("已保存工作會沿用提交時設定；切換介面唔會改動排程。")).font(.caption).foregroundStyle(.secondary)}
            }.padding(22)
        }.background(StudioPalette.panel)
    }
    @ViewBuilder var startProductionButton:some View {
        if model.busy {
            Button(action:model.pauseProcessing) {
                Label(L(model.pauseRequested ? "正在暫停…":"暫停並保存"),systemImage:"pause.fill").frame(maxWidth:.infinity).padding(.vertical,6)
            }.disabled(!model.canPauseProcessing || model.pauseRequested)
        } else {
            Button {
                if canResume {model.resumeWorkspaceProcessing()}
                else if let row=editor.selectedRow {model.submitSimple(plan,row:row)}
            } label:{Label(L(canResume ? "繼續處理":editor.document==nil ? "開始自動製作":"製作新版"),systemImage:"play.fill").frame(maxWidth:.infinity).padding(.vertical,6)}
                .buttonStyle(StudioButtonStyle(prominent:true))
                .disabled(model.simpleQueuePreparing || model.pauseStopping || (!canResume && (source==nil || !model.engineReady(selectedEngine) || originalsLoading)))
        }
    }
    var episodeShelf:some View {
        VStack(alignment:.leading,spacing:0) {
            HStack {Text(L("影片清單")).font(.headline);Spacer();Text("\(model.batchItems.count)").font(.caption.monospacedDigit()).foregroundStyle(.secondary)}.padding(20)
            Divider()
            if model.batchItems.isEmpty {
                VStack(spacing:14) {
                    Image(systemName:"film.stack").font(.system(size:32)).foregroundStyle(accent)
                    Text(L("一集，或者成季。")).font(.headline)
                    Text(L("加入多條影片，共用設定自動製作。")).font(.callout).foregroundStyle(.secondary).multilineTextAlignment(.center)
                    Button(action:importVideos) {Label(L("加入影片"),systemImage:"plus")}.disabled(model.busy)
                }.padding(24).frame(maxHeight:.infinity)
            } else {
                ScrollViewReader {scroll in
                    ScrollView {
                        LazyVStack(spacing:8) {
                            ForEach(Array(model.batchItems.enumerated()),id:\.element.id) {index,item in
                                HStack(alignment:.top,spacing:8) {
                                    Button {
                                        if let row=editor.projects.first(where:{$0.id==item.id}) ?? editor.projects.first(where:{$0.video==item.video}) {editor.open(row);refreshPreview()}
                                    } label:{
                                        VStack(alignment:.leading,spacing:9) {
                                            HStack {Text(String(format:"%02d",index+1)).font(.caption.monospacedDigit());Spacer();Text(L(item.status=="待處理" ? "等候":item.status)).font(.caption)}.foregroundStyle(source==item.video ? accent:Color.secondary)
                                            Text(URL(fileURLWithPath:item.video).lastPathComponent).font(.system(size:13,weight:.medium)).lineLimit(3).multilineTextAlignment(.leading).frame(maxWidth:.infinity,alignment:.leading)
                                            ProductionDurationLabel(folder:item.previewJob.map {URL(fileURLWithPath:$0)} ?? item.review.map {URL(fileURLWithPath:$0).deletingLastPathComponent()})
                                        }.contentShape(Rectangle())
                                    }.buttonStyle(.plain).help(item.video)
                                    Button(role:.destructive) {removeSimpleVideo(item)} label:{Image(systemName:"xmark").font(.caption)}.buttonStyle(.plain)
                                        .accessibilityLabel(L("移除")+" "+URL(fileURLWithPath:item.video).lastPathComponent)
                                        .help(L("移除影片同處理資料，保留輸出成品"))
                                        .disabled(model.busy || model.simpleQueuePreparing || model.simpleCleanupBusy)
                                }.padding(14).background(source==item.video ? accent.opacity(0.08):StudioPalette.panel,in:RoundedRectangle(cornerRadius:10))
                                    .overlay(RoundedRectangle(cornerRadius:10).stroke(source==item.video ? accent.opacity(0.5):StudioPalette.border.opacity(0.4),lineWidth:1)).id(item.id)
                            }
                        }.padding(12)
                    }.onChange(of:editor.selected) {id in if let id {scroll.scrollTo(id,anchor:.center)}}
                }
            }
            Divider()
            Text(L("移除會清理該片處理資料，保留成品同原片。")).font(.caption).foregroundStyle(.secondary).padding(18)
        }.background(StudioPalette.panel.opacity(0.55))
    }
    @ViewBuilder var outputFeedback:some View {
        if let error=model.error ?? editor.error ?? live.error {
            Label(error,systemImage:"exclamationmark.triangle").font(.callout).foregroundStyle(.orange).textSelection(.enabled)
        }
        result
    }
}

extension ProjectWorkspace {
    var expertWorkspaceBar:some View {
        HStack(spacing:12) {
            Text(L(editor.workspacePage=="terminal" ? "終端機":editor.workspacePage=="produce" ? "製作與匯出":editor.workspacePage=="review" ? "校對報告":editor.workspacePage=="queue" ? "工作佇列":editor.workspacePage=="roles" ? "角色":"聲演剪輯室")).font(.system(size:13,weight:.semibold)).fixedSize()
            Divider().frame(height:14)
            Text(editor.selectedRow?.name ?? L("匯入影片開始製作")).font(.caption).foregroundStyle(.secondary).lineLimit(1).truncationMode(.middle)
            Spacer(minLength:12)
        }.padding(.horizontal,16).frame(height:30).background(StudioPalette.panel)
    }
    var inspectorVoiceChoices:[VoiceEngineChoice] {
        let planned=model.submittedVoiceSelection(video:editor.selectedRow?.video)?.engines ?? livePreview.requestedEngines ?? editor.availableVoiceEngines
        return VoiceEngineChoice.all.filter {choice in
            choice.languages.contains(editor.previewLanguage) && (planned.contains(choice.id) || livePreview.take(choice.id,language:editor.previewLanguage) != nil || editor.cueVoiceAvailable(choice.id,language:editor.previewLanguage))
        }
    }
    var expertTakeList:some View {
        VStack(alignment:.leading,spacing:8) {
            Text(L("本段錄音")).font(.headline)
            Text(L("有錄音即可試聽，毋須等待整集完成。")).font(.caption).foregroundStyle(.secondary)
            ForEach(inspectorVoiceChoices) {choice in
                let processing=usesProcessingPreview(model,editor,livePreview)
                let liveTake=livePreview.take(choice.id,language:editor.previewLanguage)
                let available=processing ? liveTake != nil:editor.cueVoiceAvailable(choice.id,language:editor.previewLanguage)
                let needsReview = !processing && editor.cueVoiceRecording(choice.id,language:editor.previewLanguage)?.requiresReview==true
                HStack(spacing:10) {
                    VStack(alignment:.leading,spacing:3) {
                        Text(choice.shortTitle).font(.system(size:14,weight:.semibold))
                        Text(L(needsReview ? "需要試聽覆核":available ? "可試聽":"未有錄音")).font(.caption).foregroundStyle(needsReview ? Color.orange:Color.secondary)
                    }
                    Spacer()
                    Button {
                        editor.selectVoiceTrack(choice.id,language:editor.previewLanguage)
                        if processing,let take=liveTake {editor.audio.pause();livePreview.playTake(take)}
                        else {editor.playCueVoice(choice.id,language:editor.previewLanguage)}
                    } label:{Label(L("試聽"),systemImage:"play.fill")}.disabled(!available)
                        .accessibilityLabel(choice.title+" · "+L("試聽"))
                }.padding(12).background(editor.previewEngine==choice.id ? accent.opacity(0.08):Color.primary.opacity(0.025),in:RoundedRectangle(cornerRadius:9))
            }
        }
    }
}
