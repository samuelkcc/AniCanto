import SwiftUI
import AVKit

final class StudioRefreshClock:ObservableObject {
    let preview=Timer.publish(every:1,on:.main,in:.common).autoconnect()
    let projects=Timer.publish(every:5,on:.main,in:.common).autoconnect()
}

extension ProjectWorkspace {
    var professionalWorkspace:some View {
        VStack(spacing:0) {
            expertWorkspaceBar
            Divider()
            HStack(spacing:0) {
                Group {
                if editor.workspacePage=="terminal" {
                    TerminalLogView(model:model,embedded:true)
                } else if editor.workspacePage=="queue" {
                    ScrollView {queue.padding(24).frame(maxWidth:1100)}
                } else if editor.workspacePage=="roles" {
                    RoleManager(model:model,editor:editor.rolePageEditor ?? editor,close:{editor.workspacePage="edit"},fullscreen:{NSApp.keyWindow?.toggleFullScreen(nil)},options:editor.rolePageState)
                } else if editor.workspacePage=="review" {
                    ScrollView {StudioIssueList(model:model,editor:editor,edit:{editor.workspacePage="edit";options.inspector="dialogue"}).padding(24).frame(maxWidth:1100)}
                } else if editor.workspacePage=="produce" {
                    ScrollView {VStack(alignment:.leading,spacing:24) {ProductionControls(model:model,editor:editor,options:options);Divider();versionList}.padding(24).frame(maxWidth:1000)}
                } else {
            GeometryReader {g in
                let browser=options.showBrowser && !options.focusPreview ? min(max(190,g.size.width*0.16),min(340,max(190,options.browserWidth))):0
                let inspector=options.showInspector && !options.focusPreview ? min(max(320,g.size.width*0.25),min(480,max(320,options.inspectorWidth))):0
                let submitted=model.submittedVoiceSelection(video:editor.selectedRow?.video)
                let engines=submitted?.engines.count ?? (editor.document==nil ? model.selectedEngines.count:editor.availableVoiceEngines.count)
                let languages=options.allTracks ? (submitted?.languages ?? (editor.document==nil ? model.dubLanguages:editor.availableDubLanguages)).count:1
                let naturalTimeline=Double(5+engines*languages)*24+110
                let timelineHeight=options.focusPreview ? 0:min(max(280,options.timelineHeight>0 ? options.timelineHeight:min(320,naturalTimeline+30)),g.size.height*0.42)
                let topHeight=g.size.height-timelineHeight-(options.focusPreview ? 0:6)
                VStack(spacing:0) {
                    HStack(spacing:0) {
                        if browser>0 {professionalBrowser.frame(width:browser);StudioDockDivider(label:"調整專案庫寬度") {options.browserWidth=min(340,max(210,options.browserWidth+$0))}}
                        VStack(spacing:0) {
                            ProfessionalMonitor(model:model,editor:editor,live:livePreview,originals:transcriptOriginals).frame(maxHeight:.infinity)
                            if !options.focusPreview {
                                StudioDockDivider(vertical:true,label:"調整台詞面板高度") {options.transcriptHeight=min(480,max(180,options.transcriptHeight-$0))}
                                professionalTranscript.frame(height:StudioTranscriptLayout.height(preferred:options.transcriptHeight,topHeight:topHeight))
                            }
                        }.frame(maxWidth:.infinity,maxHeight:.infinity)
                        if inspector>0 {StudioDockDivider(label:"調整檢查器寬度") {options.inspectorWidth=min(560,max(340,options.inspectorWidth-$0))};professionalInspector.frame(width:inspector)}
                    }.frame(height:topHeight)
                    if !options.focusPreview {
                        StudioDockDivider(vertical:true,label:"調整時間軸高度") {options.timelineHeight=min(550,max(210,timelineHeight-$0))}
                        ProfessionalTimeline(model:model,editor:editor,live:livePreview,allTracks:$options.allTracks,showCuts:{options.inspector="cuts"}).frame(height:timelineHeight)
                    }
                }
            }
                }
                }.frame(maxWidth:.infinity,maxHeight:.infinity)
            }
            Divider()
            HStack {
                Image(systemName:model.busy ? "circle.dotted":"checkmark.circle").foregroundStyle(model.busy ? accent:.green)
                Text(model.busy ? localizedProgressDetail(model.stage):L("就緒")).lineLimit(1)
                if editor.dirty {Text(L("草稿已修改")).foregroundStyle(.orange)}
                if let error=editor.error {Text(error).foregroundStyle(.red).lineLimit(1).help(error)}
                Spacer()
                Text(editor.selectedRow?.name ?? L("未選擇影片")).lineLimit(1)
                Text("v"+(Bundle.main.object(forInfoDictionaryKey:"CFBundleShortVersionString") as? String ?? "—")).foregroundStyle(.secondary)
            }.font(.system(size:12)).padding(.horizontal,12).frame(height:28).background(StudioPalette.panel)
        }.sheet(item:$options.subtitleProposal) {SubtitleProposalView(editor:editor,version:$0)}
        .sheet(item:$options.voiceSampleVersion) {VoiceSamplesView(editor:editor,version:$0)}
        .onChange(of:editor.projects.map(\.id)) {_ in selectFirstProject()}
        .onAppear {selectFirstProject();if editor.document != nil {options.inspector="dialogue"}}
        .onChange(of:editor.document?.review) {_ in options.inspector=editor.document==nil ? "convert":"dialogue"}
    }
    var workspaceNavigation:some View {
        VStack(spacing:12) {
            ForEach([(id:"edit",title:"剪輯",icon:"slider.horizontal.below.rectangle"),(id:"roles",title:"角色",icon:"person.3"),(id:"review",title:"校對報告",icon:"checklist"),(id:"produce",title:"製作匯出",icon:"square.and.arrow.up")],id:\.id) {page in
                Button {
                    if page.id=="roles" {RoleManagerWindow.present(model:model,editor:editor,live:livePreview)}
                    else {withAnimation(.easeInOut(duration:0.2)) {editor.workspacePage=page.id}}
                } label: {VStack(spacing:6) {Image(systemName:page.icon).font(.system(size:20));Text(L(page.title)).font(.caption)}.frame(width:76,height:64).background(editor.workspacePage==page.id ? accent.opacity(0.16):Color.clear,in:RoundedRectangle(cornerRadius:10))}.buttonStyle(.plain).disabled(page.id != "edit" && editor.document==nil && livePreview.profiles.isEmpty)
            }
            Spacer()
        }.padding(8).background(StudioPalette.panel)
    }
    func selectFirstProject() {
        model.selectWorkspaceProject()
    }
    var professionalBrowser:some View {
        GeometryReader {browser in VStack(spacing:0) {
            StudioPanelHeader(title:"專案庫",icon:"folder")
            HStack {Picker(L("篩選"),selection:$editor.filter) {ForEach(["全部","待處理","待批核","處理中","已暫停","生成中","已完成","需修正"],id:\.self) {Text(L($0))}}.labelsHidden();Button {model.showProjectManager=true} label:{Image(systemName:"trash")}.help(L("管理專案及成品"))}.padding(10)
            Divider()
            ScrollView {LazyVStack(spacing:1) {
                ForEach(editor.projects.filter {editor.filter=="全部" || $0.status==editor.filter}) {row in
                    Button {editor.open(row);options.inspector=row.review==nil ? "convert":"dialogue"} label:{
                        HStack(alignment:.top,spacing:10) {
                            Image(systemName:row.review==nil ? "film":"doc.text").foregroundStyle(accent).padding(.top,3)
                            VStack(alignment:.leading,spacing:6) {Text(row.name).font(.system(size:14,weight:.medium)).lineLimit(2);Text(L(row.status)).font(.system(size:13)).foregroundStyle(.secondary)}
                            Spacer(minLength:0)
                        }.padding(12).frame(maxWidth:.infinity,alignment:.leading).background(editor.selected==row.id ? accent.opacity(0.17):.clear)
                    }.buttonStyle(.plain).contextMenu {
                        if let review=row.review {Button(L("刪除專案，保留成品"),role:.destructive) {model.manageCleanup(mode:.projects,review:review)}}
                        else {Button(L("移出佇列")) {model.removeBatchItem(id:row.id);editor.refresh(model)}}
                    }
                }
            }}.frame(minHeight:140,maxHeight:.infinity).layoutPriority(1)
            Divider()
            VStack(alignment:.leading,spacing:8) {
                Text(L("影片資訊")).font(.system(size:13,weight:.semibold))
                Text(editor.selectedRow?.name ?? L("拖入影片開始製作")).font(.system(size:13)).lineLimit(3)
                if let row=editor.selectedRow {Text(URL(fileURLWithPath:row.video).deletingLastPathComponent().path).font(.system(size:12)).foregroundStyle(.secondary).lineLimit(3).textSelection(.enabled)}
                if editor.generationSeconds>0 {VStack(alignment:.leading,spacing:3) {Text(L("總生成時間")).font(.system(size:12));Text(studioTimecode(editor.generationSeconds)).font(.system(size:14,design:.monospaced))}}
                if !editor.generationBreakdown.isEmpty {
                    DisclosureGroup(L("各階段耗時")) {
                        ForEach(editor.generationBreakdown.keys.sorted {editor.generationBreakdown[$0,default:0]>editor.generationBreakdown[$1,default:0]},id:\.self) {key in
                            let titles=["script":"翻譯與稿件","recognition":"聲音辨識","roles":"角色與畫面","verification":"聲音覆核","voice":"配音生成","separation":"音訊分離","export":"影片輸出","preparation":"準備"]
                            HStack {Text(L(titles[key] ?? key));Spacer();Text(studioTimecode(editor.generationBreakdown[key,default:0])).monospacedDigit()}.font(.caption)
                        }
                    }
                }
                Text("\(editor.projects.count) "+L("個專案")).font(.system(size:12)).foregroundStyle(.secondary)
            }.frame(maxWidth:.infinity,alignment:.leading).padding(12)
            if browser.size.height>470 {CompanionDock(model:model,maximumHeight:max(80,browser.size.height-410))}
        }.background(FrameChrome(sidebar:true))}
    }
    var professionalInspector:some View {
        VStack(spacing:0) {
            StudioPanelHeader(title:options.inspector=="dialogue" ? "對白工作台":"檢查器",icon:"slider.horizontal.3")
            Picker(L("檢查器"),selection:$options.inspector) {
                Text(L("製作設定頁")).tag("convert");Text(L("對白")).tag("dialogue");Text(L("畫面")).tag("cuts");Text(L("混音")).tag("sound")
            }.pickerStyle(.segmented).labelsHidden().padding(10)
            Divider()
            ScrollView {
                VStack(alignment:.leading,spacing:12) {
                    if options.inspector=="convert" {ProfessionalConversionControls(model:model,snapshot:ConversionInspectorSnapshot(model)).equatable()}
                    else if let document=editor.document {
                        if options.inspector=="production" {ProductionControls(model:model,editor:editor,options:options)}
                        else if options.inspector=="dialogue" {professionalDialogueInspector(document)}
                        else if options.inspector=="cuts" {cuts(document)}
                        else if options.inspector=="sound" {StudioSoundMixer(editor:editor,live:livePreview)}
                        else {
                            Picker(L("成品"),selection:$options.exportPanel) {Text(L("版本")).tag("versions");Text(L("問題與紀錄")).tag("issues")}.pickerStyle(.segmented)
                            if options.exportPanel=="versions" {versionList;queue} else {steps}
                        }
                    } else if options.inspector=="dialogue" {
                        expertTakeList
                    .onAppear {synchronizeAuditionEngine()}
                    .onChange(of:inspectorVoiceChoices.map(\.id)) {_ in synchronizeAuditionEngine()}
                    } else if options.inspector=="sound" {StudioSoundMixer(editor:editor,live:livePreview)}
                    else if options.inspector=="voices" {
                        Button {RoleManagerWindow.present(model:model,editor:editor,live:livePreview)} label:{Label(L("開啟角色相簿"),systemImage:"person.3.sequence.fill")}.buttonStyle(StudioButtonStyle(prominent:true)).disabled(livePreview.profiles.isEmpty)
                        Text(String(format:L("%d 個角色"),livePreview.profiles.count)).foregroundStyle(.secondary)
                        if livePreview.profiles.isEmpty {Text(L("角色分析尚未完成")).foregroundStyle(.secondary)}
                        else {
                            LazyVGrid(columns:[GridItem(.adaptive(minimum:100))]) {
                                ForEach(livePreview.profiles) {profile in
                                    VStack {RoleAvatarBadge(profile:profile);Text(localizedRoleName(profile.name)).font(.caption).lineLimit(2)}
                                }
                            }
                        }
                    } else {
                        Text(L("影片完成辨識後，會喺呢度顯示對白、角色同成品。")).foregroundStyle(.secondary)
                        Button(L("開始處理"),action:model.startBatch).disabled(model.busy || model.batchItems.isEmpty)
                    }
                }.padding(12).frame(maxWidth:.infinity,alignment:.leading)
            }
        }.background(StudioPalette.panel).transaction {$0.animation=nil}

    }
    func synchronizeAuditionEngine() {
        let choices=inspectorVoiceChoices.map(\.id)
        guard !choices.contains(editor.previewEngine) else{return}
        let primary=model.submittedVoiceSelection(video:editor.selectedRow?.video)?.primary ?? WorkspaceVoiceSelection(editor.config)?.primary
        if let primary,choices.contains(primary) {editor.previewEngine=primary}
        else if let first=choices.first {editor.previewEngine=first}
    }
    @ViewBuilder func professionalDialogueInspector(_ document:EditDocument)->some View {
        if let i=editor.segmentIndex {
            let segment=document.segments[i]
            HStack {
                VStack(alignment:.leading,spacing:5) {
                    Text(String(format:L("第 %d 段對白"),i+1)).font(.title3.bold())
                    Text(studioTimecode(segment.start)+" – "+studioTimecode(segment.end)).font(.caption.monospacedDigit()).foregroundStyle(.secondary)
                }
                Spacer()
                Button {editor.playSegment()} label:{Image(systemName:"speaker.wave.2")}.help(L("聽本段原聲"))
            }.padding(.vertical,8)
            Picker(L("語言"),selection:$editor.previewLanguage) {
                ForEach(transcriptLanguages,id:\.self) {language in Text(L(language=="en" ? "英文":"廣東話")).tag(language)}
            }.pickerStyle(.segmented).labelsHidden()
            Picker(L("對白工具"),selection:$options.dialogueTab) {
                Text(L("試聽")).tag("listen");Text(L("重錄")).tag("record");Text(L("調整")).tag("adjust")
            }.pickerStyle(.segmented).labelsHidden().padding(.vertical,8)
            if options.dialogueTab=="listen" {
                expertTakeList
                    .onAppear {synchronizeAuditionEngine()}
                    .onChange(of:inspectorVoiceChoices.map(\.id)) {_ in synchronizeAuditionEngine()}
                if let segment=editor.document?.segments.first(where:{$0.id==editor.selectedSegment}),let source=segment.sources.first {
                    RecordingHistoryPanel(editor:editor,model:model,engine:editor.previewEngine,language:editor.previewLanguage,index:source+1)
                }
                if !editor.auditionLabel.isEmpty {Text(editor.auditionLabel).font(.caption).foregroundStyle(accent)}
                Divider()
                Picker(L("採用引擎"),selection:$editor.previewEngine) {ForEach(inspectorVoiceChoices) {Text($0.title).tag($0.id)}}
                Button {editor.playEngine(editor.previewEngine,use:true)} label:{Label(L("採用錄音"),systemImage:"checkmark.circle").frame(maxWidth:.infinity)}
                    .buttonStyle(StudioButtonStyle(prominent:true)).disabled(editor.deliveredTake(editor.previewEngine)==nil)
                if let take=editor.fallbackTake(editor.previewEngine) {Button(L("試聽補聲")+" · "+take.source,action:editor.playFallback)}
                if editor.fallbackTake(editor.previewEngine) != nil,editor.engineTake(editor.previewEngine) != nil {
                    Button(L("比較原引擎錄音（未修復）")) {editor.playEngine(editor.previewEngine,native:true)}
                }
                Text(L("先試聽，再採用。重錄會保留之前嘅錄音。")).font(.caption).foregroundStyle(.secondary)
            } else if options.dialogueTab=="record" {
                StudioSectionTitle(number:"↻",title:"重新生成配音",detail:"只重錄所選對白，其他錄音保留。")
                Picker(L("配音引擎"),selection:$editor.previewEngine) {ForEach(VoiceEngineChoice.all) {Text($0.title).tag($0.id)}}
                Button {model.generateCueVoice(editor.previewEngine,language:editor.previewLanguage)} label:{Label(L("生成新錄音"),systemImage:"waveform.badge.plus").frame(maxWidth:.infinity)}
                    .buttonStyle(StudioButtonStyle(prominent:true))
                    .disabled(model.busy || !model.engineReady(editor.previewEngine,language:editor.previewLanguage))
                if model.busy {Text(L("製作繼續進行，已完成錄音仍可試聽。")).font(.caption).foregroundStyle(.secondary)}
                DisclosureGroup(L("聲線生成參數")) {VoiceInferenceControls(editor:editor,options:options).padding(.vertical,8)}
                if let id=editor.selectedSegment,let gap=(editor.timelineMissingRegions[editor.previewEngine+":"+editor.previewLanguage] ?? []).first(where:{$0.segmentID==id}) {
                    DisclosureGroup(L("本段診斷記錄")) {Text(gap.reason).font(.caption).textSelection(.enabled).foregroundStyle(.orange)}
                }
            } else {
            StudioSectionTitle(number:"↔",title:"角色與時間",detail:"微調所選對白嘅參考聲線同節奏。")
            Picker(L(editor.isIndependentVoiceMapping ? "配音參考":"角色"),selection:segmentText(\.speakerId)) {Text(L("未指定")).tag("");ForEach(editor.profiles) {Text(localizedRoleName($0.name)).tag($0.id)}}
            Toggle(L("啟用對白"),isOn:Binding(get:{segment.enabled},set:{v in editor.updateSegment {$0.enabled=v}}))
            Toggle(L("此段保留日文原聲"),isOn:Binding(get:{segment.preserveOriginalSpeech ?? false},set:{v in editor.updateSegment {$0.preserveOriginalSpeech=v}})).toggleStyle(.checkbox)
            DisclosureGroup(L("批量套用角色")) {
                VStack(alignment:.leading,spacing:12) {
                    Toggle(L("加入多選"),isOn:Binding(get:{editor.selectedSegments.contains(segment.id)},set:{value in if value {editor.selectedSegments.insert(segment.id)} else {editor.selectedSegments.remove(segment.id)}}))
                    Button(L("套用聲線到所選對白")) {editor.update {doc in for j in doc.segments.indices where editor.selectedSegments.contains(doc.segments[j].id) {doc.segments[j].speakerId=segment.speakerId;doc.segments[j].audioTake=nil}}}.disabled(editor.selectedSegments.isEmpty)
                    Picker(L("取代本片角色"),selection:$options.speakerTarget) {Text(L("揀原角色")).tag("");ForEach(editor.profiles) {Text(localizedRoleName($0.name)).tag($0.id)}}
                    Button(L("取代全部同角色對白")) {editor.update {doc in for j in doc.segments.indices where doc.segments[j].speakerId==options.speakerTarget {doc.segments[j].speakerId=segment.speakerId;doc.segments[j].audioTake=nil}}}.disabled(options.speakerTarget.isEmpty)
                }.padding(.vertical,10)
            }

            DisclosureGroup(L("時段與語速")+" · "+studioTimecode(segment.start)+" – "+studioTimecode(segment.end)) {
                VStack(alignment:.leading,spacing:12) {
                    number(L("配音開始"),segmentNumber(\.start));number(L("配音結束"),segmentNumber(\.end))
                    number(L("字幕開始"),segmentNumber(\.captionStart));number(L("字幕結束"),segmentNumber(\.captionEnd));number(L("語速"),segmentNumber(\.rate))
                }.padding(10)
            }
            Button(L("詳細裁切、改稿與其他 take")) {options.showAdvancedCue=true}
            Button {editor.workspacePage="review"} label:{Label(L("查看此音軌校對報告"),systemImage:"checklist")}
            }
            Text(editor.activeTrackTitle).font(.caption).foregroundStyle(.secondary)
            if editor.flaggedSegments.contains(segment.id) {Label(L("所選音軌需要覆核"),systemImage:"exclamationmark.triangle").foregroundStyle(.orange)}
        } else {Text(L("喺字幕清單或時間軸選擇對白。")).foregroundStyle(.secondary)}
    }
    var professionalTranscript:some View {
        VStack(spacing:0) {
            HStack(spacing:10) {
                Text(L("字幕與台詞")).font(.system(size:16,weight:.semibold))
                if let i=editor.segmentIndex,let document=editor.document {
                    Text("\(i+1) / \(document.segments.count)").foregroundStyle(.secondary)
                    Button {editor.selectSegment(document.segments[max(0,i-1)].id)} label:{Image(systemName:"chevron.left")}.disabled(i==0)
                    Button {editor.selectSegment(document.segments[min(document.segments.count-1,i+1)].id)} label:{Image(systemName:"chevron.right")}.disabled(i+1>=document.segments.count)
                }
                Spacer(minLength:4)
                Menu {
                    Toggle(L("循環"),isOn:$editor.looping)
                    Toggle(L("跟隨播放字幕"),isOn:$editor.followPlaybackText)
                    Picker(L("語言"),selection:$editor.previewLanguage) {ForEach(transcriptLanguages,id:\.self) {language in Text(L(language=="en" ? "英文":"廣東話")).tag(language)}}
                } label:{Image(systemName:"text.bubble")}.help(L("字幕選項")).accessibilityLabel(L("字幕選項"))
                Button {options.showInspector=true;options.inspector="dialogue";options.dialogueTab="listen"} label:{Image(systemName:"headphones")}.help(L("試聽")).accessibilityLabel(L("試聽"))
                Button {editor.audio.pause();editor.player.pause();livePreview.stopInspection();editor.auditionLabel=""} label:{Image(systemName:"stop.fill")}.help(L("停止試聽")).accessibilityLabel(L("停止試聽"))
            }.padding(.horizontal,12).frame(height:46)
            Divider()
            GeometryReader {g in
                HStack(spacing:0) {
                    VStack(spacing:0) {
                        Picker(L("來源文字"),selection:$options.sourceTranscript) {
                            Text(L("原片字幕")).tag("original");Text(L("日文原文")).tag("japanese")
                        }.pickerStyle(.segmented).labelsHidden().padding(.horizontal,12).padding(.top,10)
                        if options.sourceTranscript=="japanese" {japaneseTranscript}
                        else {originalTranscript(compact:true).padding(12).frame(maxHeight:.infinity,alignment:.topLeading)}
                    }.frame(width:g.size.width*0.40)
                    Divider()
                    targetTranscript.frame(maxWidth:.infinity,maxHeight:.infinity)
                }

            }
        }.background(StudioPalette.panel)
        .onAppear {alignTranscriptLanguage()}
        .onChange(of:transcriptLanguages) {_ in alignTranscriptLanguage()}
        .onChange(of:editor.previewLanguage) {language in if language=="en" {model.prepareEnglishForAudition()}}
        .onChange(of:editor.seconds) {time in if !usesProcessingPreview(model,editor,livePreview) {editor.followPlaybackCue(at:time)}}
        .onChange(of:livePreview.seconds) {time in if usesProcessingPreview(model,editor,livePreview) {editor.followPlaybackCue(at:time)}}
        .onChange(of:editor.followPlaybackText) {follow in if follow {editor.followPlaybackCue(at:usesProcessingPreview(model,editor,livePreview) ? livePreview.seconds:editor.seconds)}}
    }
    var transcriptLanguages:[String] {usesProcessingPreview(model,editor,livePreview) ? livePreview.requestedLanguages ?? editor.availableDubLanguages:editor.availableDubLanguages}
    func alignTranscriptLanguage() {if !transcriptLanguages.contains(editor.previewLanguage),let first=transcriptLanguages.first {editor.previewLanguage=first}}
    var activeTranscriptCues:[LiveSubtitleCue] {livePreview.cues.filter {$0.start<=livePreview.seconds && livePreview.seconds<$0.end}}
    var japaneseTranscript:some View {
        VStack(alignment:.leading,spacing:10) {
            HStack(spacing:8) {
                Text(L("日文原文")).font(.system(size:13,weight:.semibold)).lineLimit(1)
                Spacer(minLength:0)
                Button {
                    if editor.segmentIndex != nil {editor.playSegment()}
                    else if let cue=activeTranscriptCues.first {livePreview.playInterval(cue.start,cue.end)}
                } label:{Image(systemName:"speaker.wave.2.fill")}
                .help(L("聽本段原聲")).accessibilityLabel(L("聽本段原聲"))
                .disabled(editor.segmentIndex==nil && activeTranscriptCues.isEmpty)
                Button {editor.playDialogue()} label:{Image(systemName:"waveform")}
                .help(L("分離對白")).accessibilityLabel(L("分離對白")).disabled(editor.segmentIndex==nil || editor.dialoguePath==nil)
            }.frame(minHeight:34)
            if let i=editor.segmentIndex,let segment=editor.document?.segments[i] {
                TextEditor(text:Binding(get:{segment.original},set:{value in editor.followPlaybackText=false;editor.updateSegment {$0.original=value}})).font(.system(size:16)).frame(maxHeight:.infinity)
            } else {transcriptText(activeTranscriptCues.map(\.original).joined(separator:"\n"))}
        }.padding(12).frame(maxHeight:.infinity,alignment:.topLeading)
    }
    var targetTranscript:some View {
        GeometryReader {geometry in
            let compactRole=geometry.size.width<560
            let ids=editor.segmentIndex.flatMap{editor.document?.segments[$0].speakerId}.map{[$0]} ?? activeTranscriptCues.map(\.speakerID)
            let profiles=editor.document==nil ? livePreview.profiles:editor.profiles
            let profile=profiles.first(where:{ids.contains($0.id)})
            VStack(alignment:.leading,spacing:8) {
                HStack(spacing:8) {
                    Text(L(editor.previewLanguage=="en" ? "英文配音台詞":"廣東話配音台詞")).font(.system(size:16,weight:.semibold)).lineLimit(1)
                    Spacer(minLength:0)
                    if compactRole,let profile {
                        Button {RoleManagerWindow.present(model:model,editor:editor,live:livePreview,roleID:profile.id)} label:{
                            HStack(spacing:5) {
                                if let image=roleImage(profile.avatar) ?? roleImage(profile.sourceFrame) {
                                    Image(nsImage:image).resizable().scaledToFill().frame(width:28,height:28).clipped().clipShape(RoundedRectangle(cornerRadius:4))
                                } else {Image(systemName:"person.crop.square.fill").foregroundStyle(roleColor(profile.id))}
                                Text(profiles.firstIndex(where:{$0.id==profile.id}).map{String(format:"R%02d",$0+1)} ?? "").font(.caption.bold())
                            }
                        }.buttonStyle(.plain).help(L("開啟角色相簿")+" · "+localizedRoleName(profile.name))
                    }
                }.frame(minHeight:30)
                HStack(alignment:.top,spacing:8) {
                    if !compactRole,let profile {
                        Button {RoleManagerWindow.present(model:model,editor:editor,live:livePreview,roleID:profile.id)} label:{
                            EditorTranscriptRoleCard(profile:profile,code:profiles.firstIndex(where:{$0.id==profile.id}).map{String(format:"R%02d",$0+1)} ?? "",editor:editor,model:model,live:livePreview)
                        }.buttonStyle(.plain).help(L("開啟角色相簿"))
                    }
                    VStack(alignment:.leading,spacing:8) {
                        if let i=editor.segmentIndex,let segment=editor.document?.segments[i] {
                            TextEditor(text:Binding(get:{editor.previewLanguage=="en" ? segment.english ?? "":segment.text},set:{value in editor.followPlaybackText=false;editor.updateSegment {if editor.previewLanguage=="en" {$0.english=value} else {$0.text=value};$0.audioTake=nil}})).font(.system(size:16)).frame(maxWidth:.infinity,maxHeight:.infinity)
                            TextField(L("顯示字幕（留空跟配音台詞）"),text:Binding(get:{segment.captionText},set:{value in editor.followPlaybackText=false;editor.updateSegment {$0.captionText=value}})).font(.system(size:15)).textFieldStyle(.roundedBorder)
                        } else {transcriptText(activeTranscriptCues.map {$0.text(editor.previewLanguage)}.filter {!$0.isEmpty}.joined(separator:"\n"))}
                    }.frame(maxWidth:.infinity,maxHeight:.infinity)
                }.frame(maxHeight:.infinity)
            }.padding(12).frame(maxWidth:.infinity,maxHeight:.infinity,alignment:.topLeading)
        }
    }
    func transcriptText(_ text:String)->some View {
        ScrollView {Text(text.isEmpty ? L("此位置暫未有字幕"):text).font(.system(size:16)).foregroundStyle(text.isEmpty ? .secondary:.primary).textSelection(.enabled).frame(maxWidth:.infinity,alignment:.leading)}
    }
    func originalTranscript(compact:Bool=false)->some View {
        let processing=usesProcessingPreview(model,editor,livePreview)
        let sourceTime=processing ? livePreview.seconds+livePreview.offset:editor.originalPlaybackTime
        let offset=processing ? livePreview.offset:editor.offset
        let saved=processing ? livePreview.sourceCaptions:editor.sourceCaptions
        let rows=SourceCaptionClock.active(transcriptOriginals.tracks.isEmpty ? saved.map {PreviewCaption(start:$0.start+offset,end:$0.end+offset,text:$0.text)}:transcriptOriginals.visible,at:sourceTime)
        return VStack(alignment:.leading,spacing:8) {
            HStack {
                Text(L("原片字幕")).font(.system(size:13,weight:.semibold)).lineLimit(1)
                Spacer(minLength:0)
                if !transcriptOriginals.tracks.isEmpty {
                    if compact {
                        Menu {
                            ForEach(transcriptOriginals.tracks) {track in
                                Button {transcriptOriginals.selected=[track.id]} label:{
                                    if transcriptOriginals.selected.contains(track.id) {Label(track.label,systemImage:"checkmark")}
                                    else {Text(track.label)}
                                }
                            }
                        } label:{Image(systemName:"captions.bubble")}.menuStyle(.borderlessButton).frame(width:30)
                        .help(L("原片字幕軌")).accessibilityLabel(L("原片字幕軌"))
                    } else {
                        Picker(L("原片字幕軌"),selection:Binding(get:{transcriptOriginals.selected.sorted().first ?? -999},set:{transcriptOriginals.selected=[$0]})) {
                            ForEach(transcriptOriginals.tracks) {track in Text(track.label).tag(track.id)}
                        }.labelsHidden().frame(maxWidth:160)
                    }
                }
            }.frame(minHeight:30)
            ScrollView {Text(rows.isEmpty ? L("本時段冇原裝字幕"):rows.map(\.text).joined(separator:"\n")).font(.system(size:16)).foregroundStyle(rows.isEmpty ? .secondary:.primary).textSelection(.enabled).frame(maxWidth:.infinity,alignment:.leading)}
        }.frame(maxWidth:.infinity,maxHeight:.infinity,alignment:.topLeading)
    }

}

/// Progress and playback ticks do not change settings. Keep native controls and
/// scroll position mounted until their actual settings or language change.
struct ConversionInspectorSnapshot:Equatable {
    let workflow:WorkflowValues
    let submitted:WorkspaceVoiceSelection?
    let strings:[String]
    let flags:[Bool]
    let limit:Int
    @MainActor init(_ model:AppModel) {
        workflow=WorkflowValues(model)
        submitted=model.submittedVoiceSelection(video:model.projectEditor.selectedRow?.video)
        strings=[model.workspaceProductionMode,model.voiceRenderMode,model.projectEditor.outputDubMode ?? model.dubMode,model.projectEditor.document?.review ?? "",model.dubMode,model.startTimeText,model.subtitleSource,model.cosyModel,model.qwenModel,model.selectedModelID("visual"),UserDefaults.standard.string(forKey:"studioLanguage") ?? "system",UserDefaults.standard.string(forKey:"animeTheme") ?? "studio",UserDefaults.standard.string(forKey:"studioTheme") ?? "system",UserDefaults.standard.string(forKey:"studioDensity") ?? "comfortable"]
        flags=[model.busy,model.aiAutoFix,model.continueOnError,model.batchAutoSubtitles,model.cosyReady,model.gsvReady,model.qwenTTSReady];limit=model.limit
    }
}
struct ProfessionalConversionControls:View,Equatable {
    let model:AppModel
    let snapshot:ConversionInspectorSnapshot
    static func ==(lhs:Self,rhs:Self)->Bool {lhs.model === rhs.model && lhs.snapshot==rhs.snapshot}
    var body:some View {
        VStack(alignment:.leading,spacing:18) {
            Text(L("製作設定")).font(.headline)
            VoiceTrackControls(model:model,languageMode:model.projectEditor.outputDubMode ?? model.dubMode,languageSelection:Binding(get:{model.projectEditor.outputDubMode ?? model.dubMode},set:{value in
                model.selectWorkspaceLanguage(value)
            }),showsModelVersions:false,submitted:snapshot.submitted)
            ProductionModeControl(mode:Binding(get:{snapshot.submitted?.productionMode ?? model.workspaceProductionMode},set:{model.setWorkspaceProductionMode($0)}),locked:model.busy || snapshot.submitted != nil)
            if model.workspaceProductionMode != "fast" {RoleAnalysisControls(model:model,compact:true)}
            OpeningTreatmentControls(detect:Binding(get:{model.workspaceOPDetect},set:{model.setWorkspaceOPDetect($0)}),translate:Binding(get:{model.workspaceOPTranslate},set:{model.setWorkspaceOPTranslate($0)}))
            Divider()
            Text(L("處理範圍")).font(.headline)
            Picker(L("範圍"),selection:binding(\.limit)) {Text(L("60 秒")).tag(60);Text(L("3 分鐘")).tag(180);Text(L("全片")).tag(0)}.pickerStyle(.segmented).labelsHidden()
            HStack {Text(L("起點"));TextField("00:00",text:binding(\.startTimeText)).textFieldStyle(.roundedBorder)}
            Toggle(L("逐片自動選字幕"),isOn:binding(\.batchAutoSubtitles))
            if !model.batchAutoSubtitles {Picker(L("字幕來源"),selection:binding(\.subtitleSource)) {Text(L("畫面 OCR")).tag("burned");Text(L("內置字幕")).tag("embedded");Text(L("外掛字幕")).tag("external");Text(L("日語語音辨識")).tag("none")}}
            Divider()
            if model.workspaceProductionMode != "fast" {
            Text(L("批核與修復")).font(.headline)
            Toggle(L("自動批核字幕並配音"),isOn:binding(\.autoApprove))
            Toggle(L("AI 自動修復所選音軌（跟隨文字模型）"),isOn:Binding(get:{model.projectEditor.document==nil ? model.aiAutoFix:model.projectEditor.productionSelection(model).aiAutoFix},set:{value in model.aiAutoFix=value;if model.projectEditor.document != nil {model.projectEditor.productionSelection(model).aiAutoFix=value}}))
            Text(L("生成後讀取紀錄，決定同稿重錄或使用合格同語言補聲，再驗證並顯示摘要；未解決項目保留於摘要。")).font(.caption).foregroundStyle(.secondary)
            Toggle(L("自動修復；仍失敗就留空該段並繼續"),isOn:binding(\.continueOnError))
            Divider()
            }
            Text(L("輸出位置")).font(.headline)
            Text(model.exportFolder.isEmpty ? L("App 工作資料夾"):model.exportFolder).font(.system(size:13)).lineLimit(2).textSelection(.enabled)
            HStack {Button(L("選擇…"),action:model.chooseExportFolder);Button(L("完整製作預設")) {model.showWorkspaceSettings=true}}
        }.disabled(model.busy || snapshot.submitted != nil)
    }
    func binding<T>(_ key:ReferenceWritableKeyPath<AppModel,T>)->Binding<T> {Binding(get:{model[keyPath:key]},set:{model[keyPath:key]=$0})}
}

struct ProfessionalMonitor:View {
    @AppStorage("studioLanguage") private var interfaceLanguage="system"
    @ObservedObject var model:AppModel
    @ObservedObject var editor:ProjectEditor
    @ObservedObject var live:LiveVideoPreview
    @StateObject private var clock=StudioRefreshClock()
    @ObservedObject var originals:MonitorSubtitles
    @AppStorage("monitorOriginalSubtitles") private var showOriginal=true
    @AppStorage("monitorJapaneseSubtitles") private var showJapanese=false
    @AppStorage("monitorTranslatedSubtitles") private var showTranslation=false
    var originalExternal:String? {editor.config["subtitle"] as? String ?? (model.video?.path==source ? model.subtitle?.path:nil)}
    var originalStream:Int? {editor.config["subtitleStream"] as? Int ?? (model.video?.path==source && model.subtitleStream>=0 ? model.subtitleStream:nil)}
    var sourceTime:Double {seconds+(editing ? (editor.playingVersion==nil ? editor.offset:0):live.offset)}
    var overlayCaptions:[PreviewCaption] {
        guard editor.playingVersion==nil || !editing else{return []}
        var rows=showOriginal ? originals.visible:[]
        if showJapanese {
            if editing {rows += (editor.document?.segments ?? []).filter(\.enabled).map{PreviewCaption(start:$0.start+editor.offset,end:$0.end+editor.offset,text:L("日文辨識")+" · "+$0.original)}}
            else {rows += live.cues.map{PreviewCaption(start:$0.start+live.offset,end:$0.end+live.offset,text:L("日文辨識")+" · "+$0.original)}}
        }
        if showTranslation {
            if editing {rows += (editor.document?.segments ?? []).filter(\.enabled).map{PreviewCaption(start:$0.captionStart+editor.offset,end:$0.captionEnd+editor.offset,text:editor.previewLanguage=="en" ? $0.english ?? "":($0.captionText.isEmpty ? $0.text:$0.captionText))}}
            else {rows += live.cues.map{PreviewCaption(start:$0.start+live.offset,end:$0.end+live.offset,text:$0.text(editor.previewLanguage))}}
        }
        return rows.filter{!$0.text.isEmpty}.sorted{$0.start<$1.start}
    }
    func loadOriginals() {originals.load(video:source,external:originalExternal,preferred:originalStream)}
    func refreshMonitor(restorePosition:Bool=false) {
        let restore=restorePosition && live.savedSession?.video==source
        live.refresh(model,video:source)
        if restore,editing,editor.playingVersion==nil {editor.seek(live.seconds)}
    }
    var subtitleMenu:some View {
        Menu {
            Toggle(L("原片字幕"),isOn:$showOriginal)
            if !originals.tracks.isEmpty {
                ForEach(originals.tracks) {track in
                    Toggle(track.label,isOn:Binding(get:{originals.selected.contains(track.id)},set:{_ in originals.toggle(track.id)}))
                }
            }
            Divider()
            Toggle(L("日文辨識文字"),isOn:$showJapanese)
            Toggle(L("翻譯字幕"),isOn:$showTranslation)
            Text(L("可同時顯示多種字幕；只影響預覽"))
            Text(L("畫面燒入字幕會保留，無法關閉"))
            if originals.loading {Text(L("載入原片字幕…"))}
            if !originals.message.isEmpty {Text(L(originals.message))}
        } label:{Label(L("預覽字幕"),systemImage:"captions.bubble")}
        .disabled(source==nil || (editing && editor.playingVersion != nil))
    }
    var source:String? {editor.selectedRow?.video ?? model.batchItems.first?.video}
    var editing:Bool {!usesProcessingPreview(model,editor,live)}
    var player:CantoPlayer {editing ? editor.player:live.player}
    var seconds:Double {editing ? editor.seconds:live.seconds}
    var duration:Double {editing ? editor.outputDuration:live.duration}
    var body:some View {
        VStack(spacing:0) {
            HStack {
                Label(L("影片預覽"),systemImage:"play.rectangle").lineLimit(1).font(.system(size:13,weight:.semibold))
                Spacer()
                subtitleMenu
                if !editing {Button(action:live.toggleAudio) {Label(L(live.muted ? "開啟原聲":"靜音預覽"),systemImage:live.muted ? "speaker.slash":"speaker.wave.2")}.disabled(source==nil)}
                if editing {Button(L("原片")) {editor.playSource()}}
                if model.subtitleSource=="burned" && !editing {Button(L(model.selectingOCR ? "完成框選":"框選字幕")) {player.pause();model.selectingOCR.toggle()}}
            }.padding(.horizontal,12).frame(height:42).background(StudioPalette.panel)
            GeometryReader {g in
                let ratio=editing ? editor.aspect:model.videoAspect
                let w=min(g.size.width,g.size.height*max(0.1,ratio))
                ZStack {
                    Color.black
                    if source != nil {
                        Group {
                            if !editing,model.selectingOCR {OCRSelectionPlayer(player:player,selecting:true,region:$model.ocrRegion,showsControls:false)}
                            else {CaptionedPlayer(player:player,captions:overlayCaptions,seconds:sourceTime,bottomFraction:editor.document?.captionBottom ?? 0.045,sizeFraction:editor.document?.captionSize ?? 0.043,showsControls:false,topAligned:originals.tracks.isEmpty && (showJapanese || showTranslation))}
                        }.frame(width:w,height:w/max(0.1,ratio))
                    } else {
                        VStack(spacing:18) {Image(systemName:"film.stack").font(.system(size:42));Text(L("匯入影片開始製作")).font(.title2);Text(L("單條或多條影片，共用同一個工作區。")).foregroundStyle(.white.opacity(0.65));Button(L("匯入影片"),action:model.chooseBatch)}.foregroundStyle(.white)
                    }
                }.frame(width:g.size.width,height:g.size.height)
            }
            HStack(spacing:12) {
                Button {if !editing {live.follow=false};if player.rate==0 {player.play()} else {player.pause()}} label:{Image(systemName:"playpause.fill")}.disabled(source==nil).accessibilityLabel(L("播放／暫停"))
                Text(studioTimecode(seconds)).font(.system(size:14,design:.monospaced)).frame(width:100)
                Slider(value:Binding(get:{min(duration,seconds)},set:{value in if editing {editor.seek(value)} else {live.follow=false;live.seek(value)}}),in:0...max(1,duration)).disabled(source==nil)
                Text(studioTimecode(duration)).font(.system(size:13,design:.monospaced)).foregroundStyle(.secondary)
                if !editing {Toggle(L("跟隨處理"),isOn:$live.follow).toggleStyle(.checkbox)}
            }.padding(.horizontal,12).frame(height:48).background(StudioPalette.panel)
            if let error=player.failure {Text(error).foregroundStyle(.orange).padding(8)}
        }.onAppear {loadOriginals();editor.player.volume=Float(editor.previewVolume);live.player.volume=Float(editor.previewVolume);refreshMonitor(restorePosition:true)}.onChange(of:source) {_ in loadOriginals();refreshMonitor(restorePosition:true)}
        .onChange(of:editor.previewVolume) {_ in editor.player.volume=Float(editor.previewVolume);live.player.volume=Float(editor.previewVolume)}
        .onChange(of:originalExternal) {_ in loadOriginals()}.onChange(of:originalStream) {_ in loadOriginals()}
        .onChange(of:live.follow) {follow in if follow {live.resumeFollowing(model,video:source)}}
        .onReceive(clock.preview) {_ in live.refresh(model,video:source)}.onDisappear {live.player.pause();editor.player.pause()}
    }
}
func studioTimecode(_ seconds:Double)->String {
    let value=seconds.isFinite ? max(0,seconds):0
    return String(format:"%02d:%02d:%02d.%01d",Int(value)/3600,(Int(value)/60)%60,Int(value)%60,Int(value*10)%10)
}
