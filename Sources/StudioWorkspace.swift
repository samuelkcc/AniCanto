import SwiftUI

extension ContentView {
    var essentialSettings: some View {
        VStack(alignment:.leading,spacing:12) {
            Label(LocalizedStringKey(m.section == .batch ? "全局轉換設定" : "轉換設定"),systemImage:"slider.horizontal.3").font(.headline)
            PrimaryVoiceTracks(model:m)
            TranslationSourceControl(source:$m.translationSource)
            Text(L("處理範圍")).font(.caption).foregroundStyle(.secondary)
            Picker(L("處理範圍"),selection:$m.limit) {
                Text(L("60 秒")).tag(60);Text(L("3 分鐘")).tag(180);Text(L("全片")).tag(0)
            }.pickerStyle(.segmented).labelsHidden()
            HStack {
                Text(L("開始時間")).font(.caption)
                TextField(L("00:00"),text:$m.startTimeText).textFieldStyle(.roundedBorder).frame(width:85)
                Spacer()
                Button { m.useCurrentStart() } label: { Image(systemName:"scope") }.help("用原片目前位置").disabled(m.video == nil || m.showingOutput)
            }
            Picker(L("字幕來源"),selection:$m.subtitleSource) {
                Text(L("畫面燒入字幕 · OCR")).tag("burned")
                Text(L("內置字幕軌 · MKV / MP4")).tag("embedded")
                Text(L("外掛字幕 · SRT / ASS / VTT")).tag("external")
                Text(L("冇字幕 · 日語語音辨識")).tag("none")
            }.disabled(m.section == .batch && m.batchAutoSubtitles).onChange(of:m.subtitleSource) { _ in m.selectPreviewSubtitle() }
            if m.subtitleSource == "embedded" && m.section != .batch {
                if m.subtitleTracks.isEmpty { Text(L("呢段影片冇內置字幕軌。")).font(.caption).foregroundStyle(.orange) }
                else {
                    Picker(L("選擇字幕軌"),selection:$m.subtitleStream) {
                        ForEach(m.subtitleTracks) { track in Text(track.label).tag(track.id).disabled(!track.supported) }
                    }.onChange(of:m.subtitleStream) { _ in m.selectPreviewSubtitle() }
                }
            }
            if m.subtitleSource == "external" && m.section != .batch {
                HStack { Text(m.subtitle?.lastPathComponent ?? "請加入字幕檔").font(.caption).lineLimit(1);Spacer();Button(L("加入字幕"),action:m.chooseSubtitle) }
            }
            Picker(L("可切換字幕軌"),selection:$m.subtitleOutput) {
                Text(L("廣東話")).tag("yue");Text(L("英文")).tag("english");Text(L("廣東話＋英文雙行")).tag("dual");Text(L("三款字幕分開揀")).tag("all");Text(L("原裝字幕文字")).tag("original");Text(L("原裝 + 廣東話")).tag("original-yue");Text(L("原裝＋英文")).tag("original-english");Text(L("全部獨立及雙語組合")).tag("complete");Text(L("關閉")).tag("none")
            }
            Toggle(L("另外燒入固定字幕"),isOn:$m.burnOutputCaptions).font(.caption)
            if m.burnOutputCaptions {
                Picker(L("固定字幕內容"),selection:$m.burnSubtitleMode) {
                    Text(L("廣東話")).tag("yue");Text(L("英文")).tag("english");Text(L("廣東話＋英文雙行")).tag("dual");Text(L("原裝字幕文字")).tag("original");Text(L("原裝 + 廣東話")).tag("original-yue");Text(L("原裝＋英文")).tag("original-english")
                }
                Text(L("固定字幕不能關閉；跟預設配音音軌時間。可切換字幕預設關閉，避免疊字。")).font(.caption2).foregroundStyle(.secondary)
            }
            if m.subtitleSource == "burned" {
                Text(L("原片字幕已印喺畫面，無法關閉。OCR 只讀字；新增字幕唔會移除或自動遮蓋原字。")).font(.caption2).foregroundStyle(.orange)
            }
            Divider()
            OpeningTreatmentControls(detect:$m.autoSkipOP,translate:$m.translateOPED).font(.caption)
            Toggle(L("自動修復；仍失敗就留空該段並繼續"),isOn:$m.continueOnError)
            Text(L("生成故障會列入待修正清單；內容與語言警告保留供覆核。")).font(.caption2).foregroundStyle(.secondary)
            Toggle(L("自動批核字幕並配音"),isOn:$m.autoApprove)
            Text(LocalizedStringKey(m.autoApprove ? "自動翻譯 → 配音 → 輸出" : "手動校對模式：配音前會暫停")).font(.caption).foregroundStyle(m.autoApprove ? Color.secondary : Color.orange)
            HStack {
                VStack(alignment:.leading,spacing:3) {
                    Text(L("輸出位置")).font(.caption).foregroundStyle(.secondary)
                    Text(m.exportFolder.isEmpty ? L("App 工作資料夾") : m.exportFolder).font(.caption).lineLimit(1).truncationMode(.middle).help(m.exportFolder)
                }
                Spacer();Button(L("選擇…"),action:m.chooseExportFolder)
            }
            workflowAdvanced
            Text(m.selectedModel + " · " + String(m.selectedEngines.count * m.dubLanguages.count) + " " + L("條輸出音軌")).font(.caption2).foregroundStyle(.secondary)
        }.card().disabled(m.busy)
    }
}

struct PrimaryVoiceTracks:View {
    @ObservedObject var model:AppModel
    var body:some View {VoiceTrackControls(model:model)}
}

struct VoiceTrackControls: View {
    let model: AppModel
    // Keep the selected value in the view identity. A model reference alone can
    // leave a native segmented control displaying the previous project value.
    let languageMode:String
    let showsModelVersions:Bool
    let submitted:WorkspaceVoiceSelection?
    let languageSelection:Binding<String>
    @MainActor init(model:AppModel,languageMode:String?=nil,languageSelection:Binding<String>?=nil,showsModelVersions:Bool=true,submitted:WorkspaceVoiceSelection?=nil) {
        self.model=model;self.showsModelVersions=showsModelVersions;self.submitted=submitted;self.languageMode=submitted?.languageMode ?? languageMode ?? model.dubMode
        self.languageSelection=languageSelection ?? Binding(get:{model.dubMode},set:{model.dubMode=$0})
    }
    var body: some View {
        let selected=submitted ?? model.workspaceVoiceSelection
        VStack(alignment:.leading,spacing:7) {
            Picker(L("配音語言"),selection:Binding(get:{languageMode},set:{languageSelection.wrappedValue=$0})) {Text(L("廣東話")).tag("yue");Text(L("英文")).tag("en");Text(L("廣東話＋英文")).tag("both")}.pickerStyle(.segmented).labelsHidden()
            Text(L("配音音軌 · 可多選")).font(.system(size:13)).foregroundStyle(.secondary)
            ForEach(VoiceEngineChoice.all) { choice in
                HStack(spacing:6) {
                    Toggle(choice.title,isOn:Binding(get:{selected.engines.contains(choice.id)},set:{enabled in
                        if enabled {model.extraEngines.insert(choice.id)} else {model.extraEngines.remove(choice.id)}
                        if model.projectEditor.document != nil {let state=model.projectEditor.productionSelection(model);if enabled {state.engines.insert(choice.id)} else {state.engines.remove(choice.id)}}
                    })).disabled(submitted != nil || choice.id == selected.primary || !model.engineReady(choice.id))
                    Spacer(minLength:2)
                    if choice.id == selected.primary {
                        Text(L("預設音軌")).font(.system(size:12)).foregroundStyle(accent)
                    } else if model.engineReady(choice.id) {
                        Button(L("設為預設")) {
                            model.extraEngines.insert(model.ttsBackend)
                            model.extraEngines.remove(choice.id)
                            model.ttsBackend=choice.id;model.reviewBackend=choice.id
                            if model.projectEditor.document != nil {model.projectEditor.productionSelection(model).engines.insert(choice.id)}
                        }.font(.system(size:14)).buttonStyle(StudioButtonStyle())
                    } else {
                        Button(L("下載模型")) {model.section = .environment}.font(.system(size:14)).buttonStyle(StudioButtonStyle())
                    }
                }
                if showsModelVersions {Text(model.voiceModelTitle(choice.id)).font(.system(size:12)).foregroundStyle(.secondary).lineLimit(2)}
            }
            Picker(L("配音製作模式"),selection:binding(\.voiceRenderMode)) {Text(L("精細（預設）")).tag("detail");Text(L("均衡（較快）")).tag("balanced")}.pickerStyle(.menu)
            Text(L("均衡減少 V4 聲音運算及時間重錄；兩種模式都保留完整台詞、48 kHz 及覆聽。清晰度仍需比較。")).font(.caption).foregroundStyle(.secondary)
            Toggle(L("加入日語原聲音軌"),isOn:Binding(get:{selected.includeOriginal},set:{model.setWorkspaceOriginal($0)}))
            if showsModelVersions {Text(L("多個配音引擎會逐個生成；日語原聲直接保留。")).font(.system(size:12)).foregroundStyle(.secondary)}
        }.font(.system(size:14))
    }
    func binding<T>(_ key:ReferenceWritableKeyPath<AppModel,T>)->Binding<T> {Binding(get:{model[keyPath:key]},set:{model[keyPath:key]=$0})}
}

/// Sheets resolve the app's chosen language explicitly, including when macOS
/// creates their presentation host outside the parent view's locale environment.
var appInterfaceLocale: Locale {
    let selected=UserDefaults.standard.string(forKey:"studioLanguage") ?? "system"
    return Locale(identifier:selected == "system" ? (Locale.preferredLanguages.first?.hasPrefix("en") == true ? "en":"zh-HK") : selected)
}
func workspaceSheetSize() -> CGSize {
    let available=(NSApp.mainWindow?.screen ?? NSScreen.main)?.visibleFrame.size ?? CGSize(width:1440,height:900)
    return CGSize(width:min(1220,max(720,available.width-60)),height:min(740,max(540,available.height-60)))
}

struct ConversionQueueSheet: View {
    @ObservedObject var model:AppModel
    var close:()->Void
    var size=workspaceSheetSize()
    var body:some View {
        VStack(spacing:0) {
            HStack {
                Label(L("影片佇列"),systemImage:"list.bullet.rectangle").font(.headline)
                Spacer()
                Button(L("加入影片…"),action:model.chooseBatch).disabled(model.busy)
                Button(L("完成"),action:close).keyboardShortcut(.defaultAction)
            }.padding(20)
            Divider()
            ScrollView {BatchQueueView(m:model).padding(20)}
        }.frame(width:size.width,height:size.height).background(StudioPalette.panel).environment(\.locale,appInterfaceLocale).font(.system(size:15)).buttonStyle(StudioButtonStyle())
    }
}

struct GlobalConversionSettingsSheet: View {
    @ObservedObject var model:AppModel
    var size=workspaceSheetSize()
    var body:some View {
        VStack(spacing:0) {
            HStack {
                Label(L("全局轉換設定"),systemImage:"slider.horizontal.3").font(.title2.bold())
                Spacer()
                Button(L("完成")) {model.showWorkspaceSettings=false}.keyboardShortcut(.defaultAction)
            }.padding(20)
            Divider()
            HStack(alignment:.top,spacing:20) {
                settingsColumn {voiceAndRange}
                settingsColumn {subtitlesAndOutput}
            }.padding(20).disabled(model.busy)
            Divider()
            HStack {
                Text(L("新增影片預設沿用以下設定；個別影片可喺佇列覆寫。")).font(.caption).foregroundStyle(.secondary)
                Spacer()
                Text(model.selectedModel).font(.caption2).foregroundStyle(.secondary).lineLimit(1)
            }.padding(.horizontal,20).padding(.vertical,12)
        }.frame(width:size.width,height:size.height).background(StudioPalette.panel).environment(\.locale,appInterfaceLocale).font(.system(size:15)).buttonStyle(StudioButtonStyle())
    }
    private func settingsColumn<Content:View>(@ViewBuilder content:()->Content)->some View {
        ViewThatFits(in:.vertical) {
            content().fixedSize(horizontal:false,vertical:true)
            ScrollView {content()}
        }.frame(maxWidth:.infinity,maxHeight:.infinity,alignment:.topLeading)
    }
    private var voiceAndRange:some View {
        VStack(alignment:.leading,spacing:16) {
            Label(L("配音與處理範圍"),systemImage:"waveform").font(.headline)
            PrimaryVoiceTracks(model:model)
            Divider()
            Picker(L("處理範圍"),selection:$model.limit) {
                Text(L("60 秒")).tag(60);Text(L("3 分鐘")).tag(180);Text(L("全片")).tag(0)
            }.pickerStyle(.segmented)
            HStack {
                Text(L("開始時間"))
                TextField("00:00",text:$model.startTimeText).textFieldStyle(.roundedBorder).frame(width:85)
                Button {model.useCurrentStart()} label:{Image(systemName:"scope")}
                    .help(L("用原片目前位置")).disabled(model.video == nil || model.showingOutput)
                Spacer()
            }
            TranslationSourceControl(source:Binding(get:{model.workspaceTranslationSource},set:{model.setWorkspaceTranslationSource($0)}))
            OpeningTreatmentControls(detect:$model.autoSkipOP,translate:$model.translateOPED)
            Divider()
            Text(L("進階設定分類")).font(.headline)
            Text(L("翻譯、角色聲線與背景聲、輸出選項分開設定。")).font(.caption).foregroundStyle(.secondary)
            HStack(spacing:8) {
                ForEach([WorkflowTopic.translation,.voices,.output]) {topic in
                    Button {
                        model.showWorkspaceSettings=false
                        DispatchQueue.main.asyncAfter(deadline:.now()+0.25) {model.advancedSettings=WorkflowDraft(model:model,topic:topic)}
                    } label:{VStack(spacing:5) {Image(systemName:topic.icon);Text(L(topic.title)).font(.caption).lineLimit(2)}.frame(maxWidth:.infinity)}
                    .buttonStyle(.bordered)
                }
            }
        }.font(.system(size:13)).padding(18).background(surface,in:RoundedRectangle(cornerRadius:12))
    }
    private var subtitlesAndOutput:some View {
        VStack(alignment:.leading,spacing:13) {
            Label(L("字幕、輸出與批核"),systemImage:"captions.bubble").font(.headline)
            Picker(L("字幕來源"),selection:$model.subtitleSource) {
                Text(L("畫面燒入字幕 · OCR")).tag("burned")
                Text(L("內置字幕軌 · MKV / MP4")).tag("embedded")
                Text(L("外掛字幕 · SRT / ASS / VTT")).tag("external")
                Text(L("冇字幕 · 日語語音辨識")).tag("none")
            }.onChange(of:model.subtitleSource) {_ in model.selectPreviewSubtitle()}
            if model.subtitleSource=="embedded" {
                if model.subtitleTracks.isEmpty {Text(L("呢段影片冇內置字幕軌。")).font(.caption).foregroundStyle(.orange)}
                else {Picker(L("選擇字幕軌"),selection:$model.subtitleStream) {ForEach(model.subtitleTracks) {track in Text(track.label).tag(track.id).disabled(!track.supported)}}.onChange(of:model.subtitleStream) {_ in model.selectPreviewSubtitle()}}
            }
            if model.subtitleSource=="external" {
                HStack {Text(model.subtitle?.lastPathComponent ?? L("請加入字幕檔")).lineLimit(1);Spacer();Button(L("加入字幕"),action:model.chooseSubtitle)}
            }
            captionPicker(L("可切換字幕軌"),selection:$model.subtitleOutput,includeAll:true)
            Toggle(L("另外燒入固定字幕"),isOn:$model.burnOutputCaptions)
            if model.burnOutputCaptions {
                captionPicker(L("固定字幕內容"),selection:$model.burnSubtitleMode,includeAll:false)
                Text(L("固定字幕不能關閉；跟預設配音音軌時間。可切換字幕預設關閉，避免疊字。")).font(.caption2).foregroundStyle(.secondary)
            }
            if model.subtitleSource=="burned" {Text(L("原片字幕已印喺畫面，無法關閉。OCR 只讀字；新增字幕唔會移除或自動遮蓋原字。")).font(.caption2).foregroundStyle(.orange)}
            Divider()
            Toggle(L("自動修復；仍失敗就留空該段並繼續"),isOn:$model.continueOnError)
            Text(L("生成故障會列入待修正清單；內容與語言警告保留供覆核。")).font(.caption2).foregroundStyle(.secondary)
            Toggle(L("自動批核字幕並配音"),isOn:$model.autoApprove)
            Text(L(model.autoApprove ? "自動翻譯 → 配音 → 輸出":"手動校對模式：配音前會暫停")).font(.caption).foregroundStyle(model.autoApprove ? Color.secondary:Color.orange)
            Divider()
            HStack {
                VStack(alignment:.leading,spacing:4) {
                    Text(L("輸出位置")).foregroundStyle(.secondary)
                    Text(model.exportFolder.isEmpty ? L("App 工作資料夾"):model.exportFolder).font(.caption).lineLimit(1).truncationMode(.middle).help(model.exportFolder)
                }
                Spacer();Button(L("選擇…"),action:model.chooseExportFolder)
            }
            Text(String(model.selectedEngines.count*model.dubLanguages.count)+" "+L("條輸出音軌")).font(.caption2).foregroundStyle(.secondary)
        }.font(.system(size:13)).padding(18).background(surface,in:RoundedRectangle(cornerRadius:12))
    }
    private func captionPicker(_ title:String,selection:Binding<String>,includeAll:Bool)->some View {
        Picker(title,selection:selection) {
            Text(L("廣東話")).tag("yue");Text(L("英文")).tag("english");Text(L("廣東話＋英文雙行")).tag("dual")
            Text(L("原裝字幕文字")).tag("original");Text(L("原裝 + 廣東話")).tag("original-yue");Text(L("原裝＋英文")).tag("original-english")
            if includeAll {Text(L("三款字幕分開揀")).tag("all");Text(L("全部獨立及雙語組合")).tag("complete");Text(L("關閉")).tag("none")}
        }
    }
}
