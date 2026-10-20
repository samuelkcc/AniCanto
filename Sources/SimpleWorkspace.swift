import SwiftUI
import AVKit

struct StudioInterfaceSwitch:View {
    @AppStorage("studioInterfaceMode") private var mode="simple"
    var body:some View {
        Menu {
            Button {mode="simple"} label:{Label(L(mode=="simple" ? "基本模式（目前）":"切換至基本模式"),systemImage:mode=="simple" ? "checkmark":"sparkles")}
            Button {mode="professional"} label:{Label(L(mode=="professional" ? "專家模式（目前）":"切換至專家模式"),systemImage:mode=="professional" ? "checkmark":"slider.horizontal.3")}
        } label:{
            Label {Text(String(format:L("目前：%@"),L(mode=="simple" ? "基本模式":"專家模式")))} icon:{StudioToolbarIcon(name:mode=="simple" ? "sparkles":"slider.horizontal.3")}
        }
        .fixedSize().menuStyle(.borderlessButton)
        .padding(.horizontal,10).frame(minHeight:StudioMetrics.buttonHeight)
        .background(Color.primary.opacity(0.055),in:RoundedRectangle(cornerRadius:5))
        .overlay(RoundedRectangle(cornerRadius:5).stroke(StudioPalette.border,lineWidth:0.5))
        .help(L("選擇介面模式；已提交工作不變。"))
        .accessibilityLabel(L("介面模式")+": "+L(mode=="simple" ? "基本模式":"專家模式"))
        .accessibilityHint(L("開啟選單以切換模式"))
        .accessibilityIdentifier("studio.mode-switch")
    }
}
struct SimpleStudioHeader:View {
    @AppStorage("studioLanguage") private var interfaceLanguage="system"
    @ObservedObject var model:AppModel
    var body:some View {StudioAppBar(model:model,basic:true)}

}

struct SimpleProductionPlan:Equatable {
    var engine:String
    var languageMode="yue"
    var includeOriginal=true
    var autoSkipOP=true
    var translateOPED=false
    var aiAutoFix=true
    var productionMode="normal"
    var subtitles:Set<String>=["yue"]
    var originalStreams:[Int]=[]
    var languages:[String] {languageMode=="both" ? ["yue","en"]:[languageMode]}
    func settings()->[String:Any] {
        ProductionModePolicy.applying(to:["productionMode":productionMode,"fallbackToRoleVoice":true,"requireCompleteDubbing":true,"cantoneseLocale":"yue-HK","autoSkipOP":autoSkipOP,"translateOPED":translateOPED,"interfaceMode":"simple","roleAnalysisMode":"audio","visualRoleAnalysisEnabled":false,"selectedEngines":[engine],"ttsBackend":engine,"defaultAudioEngine":engine,
         "dubLanguages":languages,"targetLanguage":languages[0],"defaultDubLanguage":languages[0],"includeOriginal":includeOriginal,
         "subtitleOutput":"none","subtitleModes":["original","yue","english"].filter{subtitles.contains($0)},
         "originalSubtitleStreams":subtitles.contains("original") ? originalStreams:[],"burnOutputCaptions":false,
         "autoApprove":true,"autoSpeakers":true,"translate":true,"speechTiming":true,"autoFit":true,
         "aiAutoFix":aiAutoFix,"continueOnError":true,"fillMissingVoiceScripts":true,
         "separateBackground":true,"independentReferences":true,"voiceStyleMode":"clone"])
    }
    func validate() throws {
        guard let choice=VoiceEngineChoice.all.first(where:{$0.id==engine}),!languages.isEmpty,languages.allSatisfy(choice.languages.contains),subtitles.isSubset(of:["original","yue","english"]) else {throw AppFailure(message:L("所選引擎不支援呢個配音語言。"))}
    }
}
extension AppModel {
    /// Freeze shared defaults per request; switching UI cannot mutate a submitted conversion.
    func submitSimple(_ plan:SimpleProductionPlan,row:ProjectRow,startImmediately:Bool=true) {
        guard !busy else{return}
        do {
            try plan.validate()
            guard engineReady(plan.engine) else{throw AppFailure(message:L("請先在模型中心部署所選引擎。"))}
            guard exportFolder.isEmpty || FileManager.default.isWritableFile(atPath:exportFolder) else{throw AppFailure(message:L("輸出資料夾唔存在或冇寫入權限，請重新選擇。"))}
            var settings=plan.settings()
            if let review=row.review {
                if projectEditor.document?.review != review.path {projectEditor.open(row)}
                guard projectEditor.document?.review==review.path else{return}
                settings["audioOnlyRerun"]=true
                let before=editorTasks.count
                submitEditor(audioSettings:settings,startImmediately:false)
                if startImmediately,editorTasks.count>before {resumeProcessing()}
            } else {
                guard let item=batchItems.first(where:{$0.id==row.id}) else{return}
                var cfg=conversionConfig(URL(fileURLWithPath:row.video),start:0)
                cfg.merge(settings) {_,new in new};cfg["limit"]=0;cfg["startOffset"]=0
                cfg["batchAutoSubtitles"]=true;cfg["subtitleSource"]="burned";cfg["subtitle"]=NSNull();cfg["ocr"]=false
                cfg["videos"]=[["id":item.id,"video":item.video]]
                let scheduled=normalizeBatchRequests()
                if !scheduled.contains(item.id) {pendingBatchRequests.append(try JSONSerialization.data(withJSONObject:cfg));persistBatchRequests()}
                if startImmediately {resumeProcessing()}
            }
        } catch {self.error=error.localizedDescription}
    }
}

final class SimplePreviewOptions:ObservableObject {
    @Published var showSettings=false
    @Published var matchCaptions=true
    @Published var captionModes=Set<String>()
    @Published var auditionLanguage="ja"
    @Published var exportOriginals:Set<Int>?
}

struct SimpleVoicePlaybackOption:Identifiable {
    let engine:VoiceEngineChoice,language:String
    var id:String {engine.id+":"+language}
    @MainActor static func choices(takes:[ProcessingVoiceTake],seconds:Double,selected:String,languages:[String])->[Self] {
        let current=takes.filter {$0.start<=seconds && seconds<$0.end && languages.contains($0.language)}
        let ready=Set(current.map(\.engine))
        return VoiceEngineChoice.all.filter {$0.id==selected || ready.contains($0.id)}.sorted {a,b in
            if ready.contains(a.id) != ready.contains(b.id) {return ready.contains(a.id)}
            return a.id<b.id
        }.flatMap {engine in engine.languages.filter {language in languages.contains(language) && (engine.id==selected || current.contains {$0.engine==engine.id && $0.language==language})}.map {Self(engine:engine,language:$0)}}
    }
}

struct SimpleWorkspace:View {
    @AppStorage("studioLanguage") private var interfaceLanguage="system"
    @ObservedObject var model:AppModel
    @ObservedObject var editor:ProjectEditor
    @ObservedObject var live:LiveVideoPreview
    init(model:AppModel,editor:ProjectEditor,preview:LiveVideoPreview?=nil) {
        self.model=model;self.editor=editor;_live=ObservedObject(wrappedValue:preview ?? model.workspacePreview)
    }
    @StateObject private var originals=MonitorSubtitles()
    @StateObject private var clock=StudioRefreshClock()
    @StateObject private var options=SimplePreviewOptions()
    @AppStorage("simpleSubtitleModes") private var subtitleModes="yue"
    var source:String? {editor.selectedRow?.video}
    var current:LiveSubtitleCue? {live.cues.first {$0.start<=live.seconds && live.seconds<$0.end}}
    var submitted:WorkspaceVoiceSelection? {model.submittedVoiceSelection(video:source)}
    var selectedEngine:String {submitted?.primary ?? model.workspaceVoiceSelection.primary}
    var originalsLoading:Bool {originals.loading && selectedModes.contains("original")}
    var selectedModes:Set<String> {editor.document==nil ? Set(subtitleModes.split(separator:",").map(String.init)):editor.outputSubtitleModes}

    var draftLanguage:String {editor.outputDubMode ?? model.dubMode}
    var plan:SimpleProductionPlan {SimpleProductionPlan(engine:selectedEngine,languageMode:submitted?.languageMode ?? draftLanguage,includeOriginal:submitted?.includeOriginal ?? model.workspaceVoiceSelection.includeOriginal,autoSkipOP:model.workspaceOPDetect,translateOPED:model.workspaceOPTranslate,aiAutoFix:true,productionMode:submitted?.productionMode ?? model.workspaceProductionMode,subtitles:selectedModes,originalStreams:editor.document?.originalSubtitleStreams ?? (options.exportOriginals ?? originals.selected).sorted())}
    var pendingHere:Bool {model.hasSavedRequest(video:source)}
    var canResume:Bool {model.hasSavedWork}
    var captionRows:[PreviewCaption] {
        var modes=options.captionModes
        if options.matchCaptions {modes.insert(options.auditionLanguage=="ja" ? "original":options.auditionLanguage=="en" ? "english":"yue")}
        var rows=modes.contains("original") ? originals.visible:[]
        let languages=["yue","en"].filter {modes.contains($0=="en" ? "english":"yue")}
        if !languages.isEmpty {
            let engine=live.auditionTake?.engine ?? selectedEngine
            rows += BasicPreviewCaptions.rows(cues:live.cues,takes:live.takes,engine:engine,languages:languages,offset:live.offset)
        }
        return rows.sorted {$0.start<$1.start}
    }
    var body:some View {
        GeometryReader {geometry in
            if geometry.size.width >= 1180 {
                HStack(alignment:.top,spacing:0) {
                    episodeShelf.frame(width:248)
                    Divider()
                    ScrollView {
                        VStack(alignment:.leading,spacing:20) {
                            previewHeading
                            monitor.frame(height:max(260,min(geometry.size.height*0.47,550)))
                            productionProgress
                            playback
                            outputFeedback
                        }.padding(24)
                    }.frame(maxWidth:.infinity)
                    Divider()
                    productionSidebar.frame(width:300)
                }
            } else {
                ScrollView {
                    VStack(alignment:.leading,spacing:20) {
                        previewHeading
                        monitor.frame(height:max(260,min(geometry.size.width*0.50,480)))
                        productionProgress
                        playback
                        quickSetup
                        startProductionButton
                        batchList
                        outputFeedback
                    }.padding(20)
                }
            }
        }.onAppear {if selectedEngine=="wsyue" && submitted==nil {model.dubMode="yue"};refreshProjects();refreshPreview()}
        .onReceive(clock.preview) {_ in if !model.simpleCleanupBusy {refreshPreview()}}
        .onReceive(clock.projects) {_ in if !model.simpleCleanupBusy {refreshProjects()}}
        .onChange(of:model.busy) {_ in refreshProjects();refreshPreview()}
        .onChange(of:editor.selected) {_ in options.exportOriginals=nil;live.stopInspection();options.auditionLanguage="ja";refreshPreview()}
        .onChange(of:originals.tracks.map(\.id)) {_ in if options.exportOriginals==nil {options.exportOriginals=originals.selected}}
        .onChange(of:draftLanguage) {value in live.stopInspection();options.auditionLanguage="ja";if value=="both" {setSubtitle("yue",true);setSubtitle("english",true)} else {setSubtitle(value=="en" ? "english":"yue",true)}}
        .onChange(of:live.requestedLanguages) {value in if options.auditionLanguage != "ja",let value,!value.contains(options.auditionLanguage) {live.stopInspection();options.auditionLanguage="ja"}}
        .onChange(of:model.ttsBackend) {_ in if selectedEngine=="wsyue" && submitted==nil {model.dubMode="yue"}}
        .onChange(of:live.follow) {value in if value {live.resumeFollowing(model,video:source)}}
        .onDisappear {live.stopInspection();editor.audio.pause()}
        .accessibilityIdentifier("basic-workspace-"+interfaceLanguage)
    }
    var toolbar:some View {
        HStack(spacing:12) {
            Menu {
                ForEach(editor.projects) {row in Button(row.name) {editor.open(row);refreshPreview()}}
                Divider();Button(L("匯入影片…"),action:importVideos).disabled(model.busy || model.simpleQueuePreparing)
            } label:{Label(editor.selectedRow?.name ?? L("揀一條影片"),systemImage:"film.stack")}.lineLimit(2).multilineTextAlignment(.leading).frame(maxWidth:.infinity,minHeight:44,alignment:.leading)
            Button(action:importVideos) {Image(systemName:"plus")}.help(L("匯入影片")).disabled(model.busy || model.simpleQueuePreparing)
            Button {options.showSettings.toggle()} label:{Label(L("製作設定"),systemImage:"slider.horizontal.3")}
                .popover(isPresented:$options.showSettings) {settings.padding(22).frame(width:390)}
            if model.busy {
                Button(action:model.pauseProcessing) {Label(L(model.pauseRequested ? "正在暫停…":"暫停並保存"),systemImage:"pause.fill")}.disabled(!model.canPauseProcessing || model.pauseRequested)
            } else {
                Button {if canResume {model.resumeWorkspaceProcessing()} else if let row=editor.selectedRow {model.submitSimple(plan,row:row)}} label:{Label(L(canResume ? "繼續處理":editor.document==nil ? "開始自動製作":"製作新版"),systemImage:"play.fill")}
                    .buttonStyle(StudioButtonStyle(prominent:true)).disabled(model.simpleQueuePreparing || model.pauseStopping || (!canResume && (source==nil || !model.engineReady(selectedEngine) || (originals.loading && selectedModes.contains("original")))))
            }
        }
    }
    var monitor:some View {
        VStack(spacing:0) {
            GeometryReader {g in
                ZStack {
                    Color.black
                    if source != nil {
                        CaptionedPlayer(player:live.player,captions:captionRows,seconds:live.seconds+live.offset,bottomFraction:0.055,sizeFraction:0.043,showsControls:false)
                            .frame(width:min(g.size.width,g.size.height*max(0.1,editor.aspect)),height:min(g.size.height,g.size.width/max(0.1,editor.aspect)))
                    } else {
                        VStack(spacing:16) {Image(systemName:"film.stack").font(.system(size:42));Text(L("放入影片，交畀 AniCanto")).font(.title2.bold());Text(L(plan.productionMode=="fast" ? "自動翻譯 → 配音 → 輸出":"自動翻譯、配音、修復同匯出")).foregroundStyle(.white.opacity(0.65));Button(L("匯入影片"),action:importVideos)}.foregroundStyle(.white)
                    }
                }.frame(width:g.size.width,height:g.size.height)
            }
            HStack(spacing:12) {
                Button {
                    if live.auditionTake != nil {live.stopInspection()}
                    else {live.follow=false;if live.player.rate==0 {live.player.play()} else {live.player.pause()}}
                } label:{Image(systemName:live.player.rate==0 ? "play.fill":"pause.fill")}.disabled(source==nil).accessibilityLabel(L("播放／暫停原片"))
                Text(studioTimecode(live.seconds)).font(.system(.caption,design:.monospaced)).frame(width:94)
                Slider(value:Binding(get:{min(live.duration,max(0,live.seconds))},set:{live.follow=false;live.seek($0)}),in:0...max(1,live.duration)).disabled(source==nil).accessibilityLabel(L("影片位置"))
                Text(studioTimecode(live.duration)).font(.system(.caption,design:.monospaced)).foregroundStyle(.secondary)
                Toggle(L("跟隨處理"),isOn:$live.follow).toggleStyle(.checkbox)
                subtitleMenu
            }.padding(12).background(StudioPalette.panel)
        }.clipShape(RoundedRectangle(cornerRadius:16)).overlay(RoundedRectangle(cornerRadius:16).stroke(StudioPalette.border,lineWidth:1))
    }
    var subtitleMenu:some View {
        Menu {
            Toggle(L("字幕跟隨試聽語言"),isOn:$options.matchCaptions)
            Toggle(L("廣東話字幕"),isOn:captionBinding("yue"));Toggle(L("英文字幕"),isOn:captionBinding("english"));Toggle(L("原片字幕"),isOn:captionBinding("original"))
            if !originals.tracks.isEmpty {Divider();ForEach(originals.tracks) {track in Toggle(track.label,isOn:Binding(get:{originals.selected.contains(track.id)},set:{value in if value {originals.selected.insert(track.id);options.captionModes.insert("original")} else {originals.selected.remove(track.id)}}))}}
            Divider();Button(L("關閉預覽字幕")) {options.matchCaptions=false;options.captionModes=[]}
        } label:{Image(systemName:"captions.bubble")}.help(L("預覽字幕 · 可多選"))
    }
    var playbackLanguages:[String] {submitted?.languages ?? (model.busy ? live.requestedLanguages:nil) ?? plan.languages}
    var displayedLanguage:String {playbackLanguages.count>1 ? "both":playbackLanguages.first ?? "yue"}
    var playbackChoices:[SimpleVoicePlaybackOption] {SimpleVoicePlaybackOption.choices(takes:live.takes,seconds:live.seconds,selected:selectedEngine,languages:playbackLanguages)}
    var latestTake:ProcessingVoiceTake? {let matching=live.takes.filter {playbackLanguages.contains($0.language)};return matching.filter {$0.engine==selectedEngine}.max {$0.start<$1.start} ?? matching.max {$0.start<$1.start}}
    var playback:some View {
        VStack(alignment:.leading,spacing:12) {
            HStack {Label(L("本段試聽"),systemImage:"headphones").font(.headline);Spacer();Text(current.map{studioTimecode($0.start)+" – "+studioTimecode($0.end)} ?? L("拖動影片，揀想聽嘅位置")).font(.caption).foregroundStyle(.secondary)}
            Text(live.auditionTake?.text ?? current.map{$0.text(options.auditionLanguage=="en" ? "en":"yue").isEmpty ? $0.original:$0.text(options.auditionLanguage=="en" ? "en":"yue")} ?? L("完成嘅配音會即時出現，可以邊轉換邊試聽。")).font(.system(size:19,weight:.medium)).frame(maxWidth:.infinity,alignment:.leading).textSelection(.enabled)
            LazyVGrid(columns:[GridItem(.adaptive(minimum:210),spacing:10)],spacing:10) {
                Button {options.auditionLanguage="ja";if let cue=current {live.playInterval(cue.start,cue.end)} else {live.playInterval(live.seconds,min(live.seconds+10,live.duration))}} label:{Label(L("日文原聲"),systemImage:"play.fill").frame(maxWidth:.infinity)}.disabled(source==nil)
                ForEach(playbackChoices) {choice in
                    let take=live.take(choice.engine.id,language:choice.language)
                    Button {if let take {editor.audio.pause();options.auditionLanguage=choice.language;live.playTake(take)}} label:{Label(choice.engine.shortTitle+" · "+L(choice.language=="en" ? "英文":"廣東話")+(take==nil ? " · "+L("等待生成"):""),systemImage:take==nil ? "clock":"play.fill").frame(maxWidth:.infinity)}
                        .disabled(take==nil).help(L("播放已完成配音；轉換會繼續"))
                }
            }
            if !live.takes.isEmpty {
                HStack {
                    Text(L("已完成嘅錄音可以即時試聽；最終修復及合片會繼續。")).font(.caption).foregroundStyle(.secondary)
                    Spacer()
                    if !live.takes.contains(where:{$0.start<=live.seconds && live.seconds<$0.end}),let latest=latestTake {
                        Button(L("試聽最近完成")) {options.auditionLanguage=latest.language;live.playTake(latest)}.font(.caption)
                    }
                }
            }
        }.padding(18).background(StudioPalette.panel,in:RoundedRectangle(cornerRadius:16))
    }
    var quickSetup:some View {
        VStack(alignment:.leading,spacing:22) {
            ProductionModeControl(mode:Binding(get:{submitted?.productionMode ?? model.workspaceProductionMode},set:{model.setWorkspaceProductionMode($0)}),locked:model.busy || submitted != nil)
            StudioSectionTitle(number:"01",title:"配音聲音",detail:"只揀一個引擎，其他交畀工作室。")
            Picker(L("配音引擎"),selection:Binding(get:{selectedEngine},set:{model.selectSimpleEngine($0)})) {
                ForEach(VoiceEngineChoice.all) {choice in Text(choice.title+(model.engineReady(choice.id) ? "":" · "+L("未部署"))).tag(choice.id)}
            }.labelsHidden().frame(maxWidth:.infinity)
            VStack(alignment:.leading,spacing:10) {
                Text(L("配音語言")).font(.subheadline.weight(.semibold))
                Picker(L("配音語言"),selection:Binding(get:{displayedLanguage},set:{model.selectWorkspaceLanguage($0)})) {
                    Text(L("廣東話")).tag("yue");Text(L("英文")).tag("en").disabled(selectedEngine=="wsyue");Text(L("雙語")).tag("both").disabled(selectedEngine=="wsyue")
                }.labelsHidden().pickerStyle(.segmented)
                Toggle(L("保留日文原聲音軌"),isOn:Binding(get:{submitted?.includeOriginal ?? model.workspaceVoiceSelection.includeOriginal},set:{model.setWorkspaceOriginal($0)})).toggleStyle(.checkbox)
            }
            Divider()
            StudioSectionTitle(number:"02",title:"輸出字幕",detail:"可多選，播放時隨時切換。")
            VStack(alignment:.leading,spacing:12) {
                ForEach([("yue","廣東話字幕"),("english","英文字幕"),("original","原片字幕")],id:\.0) {key,title in
                    Toggle(L(title),isOn:Binding(get:{selectedModes.contains(key)},set:{setSubtitle(key,$0)})).toggleStyle(.checkbox)
                }
                if selectedModes.contains("original"),!originals.tracks.isEmpty {
                    DisclosureGroup(L("選擇原片字幕軌")) {
                        ForEach(originals.tracks) {track in
                            Toggle(track.label,isOn:Binding(get:{(options.exportOriginals ?? originals.selected).contains(track.id)},set:{value in
                                var streams=options.exportOriginals ?? originals.selected
                                if value {streams.insert(track.id)} else {streams.remove(track.id)}
                                options.exportOriginals=streams
                                if editor.document != nil {editor.update {$0.originalSubtitleStreams=streams.sorted()}}
                                if streams.isEmpty {setSubtitle("original",false)}
                            })).font(.caption).toggleStyle(.checkbox)
                        }
                    }.font(.caption)
                }
            }
            Divider()
            DisclosureGroup(L("片頭、片尾及更多設定")) {
                OpeningTreatmentControls(detect:Binding(get:{model.workspaceOPDetect},set:{model.setWorkspaceOPDetect($0)}),translate:Binding(get:{model.workspaceOPTranslate},set:{model.setWorkspaceOPTranslate($0)})).padding(.top,10)
            }
            if !model.engineReady(selectedEngine) {
                Button(L("前往模型中心")) {UserDefaults.standard.set("professional",forKey:"studioInterfaceMode");model.section = .environment}
            }
        }.disabled(model.busy || pendingHere || model.simpleQueuePreparing)
    }
    var settings:some View {
        VStack(alignment:.leading,spacing:16) {
            Text(L("簡單製作設定")).font(.title3.bold())
            VStack(alignment:.leading,spacing:14) {
                Picker(L("配音引擎"),selection:Binding(get:{selectedEngine},set:{model.selectSimpleEngine($0)})) {ForEach(VoiceEngineChoice.all) {choice in Text(choice.title+(model.engineReady(choice.id) ? "":" · "+L("未部署"))).tag(choice.id)}}
                OpeningTreatmentControls(detect:Binding(get:{model.workspaceOPDetect},set:{model.setWorkspaceOPDetect($0)}),translate:Binding(get:{model.workspaceOPTranslate},set:{model.setWorkspaceOPTranslate($0)}))
                Toggle(L("保留日文原聲音軌"),isOn:Binding(get:{submitted?.includeOriginal ?? model.workspaceVoiceSelection.includeOriginal},set:{model.setWorkspaceOriginal($0)}))
                Divider();Text(L("輸出字幕 · 可多選")).font(.headline)
                ForEach([("yue","廣東話字幕"),("english","英文字幕"),("original","原片字幕")],id:\.0) {key,title in Toggle(L(title),isOn:Binding(get:{selectedModes.contains(key)},set:{setSubtitle(key,$0)}))}
                if selectedModes.contains("original"),!originals.tracks.isEmpty {ForEach(originals.tracks) {track in Toggle(track.label,isOn:Binding(get:{(options.exportOriginals ?? originals.selected).contains(track.id)},set:{value in var streams=options.exportOriginals ?? originals.selected;if value {streams.insert(track.id)} else {streams.remove(track.id)};options.exportOriginals=streams;if editor.document != nil {editor.update {$0.originalSubtitleStreams=streams.sorted()}};if streams.isEmpty {setSubtitle("original",false)}})).font(.caption)}}
            }.toggleStyle(.checkbox).disabled(model.busy || pendingHere || model.simpleQueuePreparing)
            Text(L("字幕可以喺播放器開關及切換，唔會燒入畫面。")).font(.caption).foregroundStyle(.secondary)
            Text(L("角色配對、字幕批核、Qwen 修復及合片自動處理。")).font(.caption).foregroundStyle(.secondary)
            if pendingHere || model.busy {Text(L("已保存工作會沿用提交時設定；切換介面唔會改動排程。")).font(.caption).foregroundStyle(.secondary)}
            if !model.engineReady(selectedEngine) {Button(L("前往模型中心")) {UserDefaults.standard.set("professional",forKey:"studioInterfaceMode");model.section = .environment}}
        }
    }
    @ViewBuilder var result:some View {
        if let version=editor.versions.first(where:{$0.output != nil && ["complete","partial"].contains($0.status)}),let url=version.output {
            HStack {Label(L("成品已保存"),systemImage:"checkmark.circle.fill").foregroundStyle(.green);Spacer();Button(L("播放成品")) {NSWorkspace.shared.open(url)};Button(L("顯示檔案")) {NSWorkspace.shared.activateFileViewerSelecting([url])}}
        }
    }
    func captionBinding(_ key:String)->Binding<Bool> {Binding(get:{options.captionModes.contains(key)},set:{value in if value {options.captionModes.insert(key)} else {options.captionModes.remove(key)};options.matchCaptions=false})}
    func setSubtitle(_ key:String,_ value:Bool) {var modes=selectedModes;if value {modes.insert(key)} else {modes.remove(key)};let sorted=["original","yue","english"].filter{modes.contains($0)};subtitleModes=sorted.joined(separator:",");if editor.document != nil {editor.update {$0.subtitleModes=sorted}}}
    func importVideos() {let ids=Set(model.batchItems.map(\.id));model.chooseBatch();editor.refresh(model);if let row=editor.projects.first(where:{!ids.contains($0.id)}) {editor.open(row)};refreshPreview()}
    func refreshProjects() {guard !model.simpleCleanupBusy else{return};model.refresh();editor.refresh(model);model.selectWorkspaceProject()}
    func removeSimpleVideo(_ item:BatchItem) {
        model.removeSimpleVideo(item) {
            live.resetForRemoval()
            await originals.cancelAndClear()
        }
    }
    func refreshPreview() {
        guard !model.simpleCleanupBusy else{return}
        let folder=editor.selectedRow?.review?.deletingLastPathComponent().path ?? editor.selectedRow?.previewJob?.path
        live.refresh(model,video:source,preferredJob:folder)
        originals.load(video:source,external:editor.config["subtitle"] as? String,preferred:editor.config["subtitleStream"] as? Int)
    }
}

struct SimpleProcessingProgress:View {
    @AppStorage("studioLanguage") private var interfaceLanguage="system"
    @ObservedObject var model:AppModel
    var ready:Int
    var languages:[String]=["yue"]
    var incomplete=false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    private var value:Double? {model.displayProgress.flatMap {$0.isFinite ? min(1,max(0,$0)):nil}}
    var body:some View {
        VStack(alignment:.leading,spacing:6) {
            let exported=model.displayJourney?.complete==true
            let status=SimpleProgressStatus(stage:model.stage,detail:model.detail,busy:model.busy,paused:!exported && model.queuePaused && model.hasSavedWork,error:model.error ?? (!model.busy && incomplete && !exported ? L("配音製作未完成；成功錄音及處理進度已保存。"):nil),languages:languages,exported:exported,needsReview:model.displayJourney?.qualityStatus=="needs-review")
            HStack(alignment:.top,spacing:16) {
                VStack(alignment:.leading,spacing:5) {
                    Text(status.title).font(.headline)
                    if !status.detail.isEmpty {Text(L(status.detail)).font(.callout).foregroundStyle(.secondary).fixedSize(horizontal:false,vertical:true)}
                }.frame(maxWidth:.infinity,alignment:.leading)
                VStack(alignment:.trailing,spacing:4) {
                    if let value,model.busy || !incomplete || exported {Text(String(format:"%.0f%%",value*100)).font(.title3.bold().monospacedDigit())}
                    ProductionTimeStatus(model:model,compact:true)
                }.frame(minWidth:200,idealWidth:280,maxWidth:300,alignment:.trailing)
            }
            ClayProgressTrack(value:value,running:model.busy,reduceMotion:reduceMotion,completed:!model.busy && exported,compact:true)
            ProductionMilestones(journey:model.displayJourney,playful:true)
            HStack {Text(L("配音一完成，就可以喺下面試聽。"));Spacer();if ready>0 {Text(String(format:L("%d 段配音可試聽"),ready))}}
                .font(.caption).foregroundStyle(.secondary)
        }.padding(14).background(accent.opacity(0.055),in:RoundedRectangle(cornerRadius:16))
        .accessibilityElement(children:.combine).accessibilityValue(value.map{String(format:"%.0f%%",$0*100)} ?? L("處理中…"))
    }
}
