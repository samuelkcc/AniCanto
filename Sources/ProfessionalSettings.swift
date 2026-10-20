import SwiftUI
import AppKit

// Existing callers now navigate inside the shared application window.
@MainActor enum ProfessionalSettingsWindow {
    static func show(model:AppModel,category:String?=nil) {
        model.setupCategory=category ?? "general";model.section = .presets
    }
}
final class ProfessionalSetupOptions:ObservableObject {@Published var category="general"}
struct ProfessionalSettingsView:View {
    @AppStorage("studioLanguage") private var language="system"
    @ObservedObject var model:AppModel
    var startingCategory="general"
    @StateObject private var options=ProfessionalSetupOptions()
    @AppStorage("studioTheme") private var theme="system"
    var body:some View {
        VStack(spacing:0) {
            HStack {Text(L("製作預設")).font(.system(size:24,weight:.semibold));Spacer();Text(L("單片與批量共用")).foregroundStyle(.secondary)}.padding(24)
            Divider()
            HStack(spacing:0) {
                VStack(alignment:.leading,spacing:4) {
                    ForEach([("general","開始與範圍","play.rectangle"),("voices","配音音軌","waveform"),("models","模型選用","shippingbox"),("subtitles","字幕與翻譯","captions.bubble"),("roles","角色與背景聲","person.2"),("output","輸出與批核","square.and.arrow.up")],id:\.0) {key,title,icon in
                        Button {options.category=key} label:{Label(L(title),systemImage:icon).frame(maxWidth:.infinity,alignment:.leading).padding(12).background(options.category==key ? accent.opacity(0.15):.clear,in:RoundedRectangle(cornerRadius:6))}.buttonStyle(.plain)
                    }
                    Spacer()
                    Text(L("個別影片可喺佇列覆寫。已開始嘅工作使用開始時設定。")).font(.system(size:13)).foregroundStyle(.secondary).padding(12)
                }.padding(12).frame(width:240).background(StudioPalette.panel)
                Divider()
                ScrollView {
                    VStack(alignment:.leading,spacing:24) {
                        if options.category=="general" {general}
                        else if options.category=="voices" {voiceModels}
                        else if options.category=="models" {ActiveModelSettings(model:model)}
                        else if options.category=="subtitles" {subtitles}
                        else if options.category=="roles" {roles}
                        else {output}
                    }.padding(28).frame(maxWidth:1000,alignment:.leading).frame(maxWidth:.infinity,alignment:.leading)
                }.disabled(model.busy)
            }
            Divider()
            HStack {Button(L("儲存製作預設"),action:model.saveStudioPreset).disabled(model.busy);if model.presetSavedAt != nil {Text(L("預設已儲存")).foregroundStyle(accent)};Text(L("改動會套用至之後開始嘅影片。")).foregroundStyle(.secondary);Spacer();Text(model.selectedModel).font(.system(size:13)).lineLimit(1)}.padding(16)
        }.background(StudioPalette.base).font(.system(size:15)).controlSize(.regular).buttonStyle(StudioButtonStyle()).tint(accent)
            .onAppear {options.category=startingCategory}.onChange(of:model.setupCategory) {options.category=$0}.environment(\.locale,language == "system" ? appInterfaceLocale:Locale(identifier:language)).preferredColorScheme(theme=="dark" ? .dark:theme=="light" ? .light:nil)
    }
    var general:some View {
        VStack(alignment:.leading,spacing:22) {
            Text(L("開始與範圍")).font(.title2.bold())
            ProductionModeControl(mode:$model.productionMode,locked:model.busy)
            Picker(L("配音語言"),selection:$model.dubMode) {Text(L("廣東話")).tag("yue");Text(L("英文")).tag("en");Text(L("廣東話＋英文")).tag("both")}.pickerStyle(.segmented)
            Picker(L("處理範圍"),selection:$model.limit) {Text(L("60 秒")).tag(60);Text(L("3 分鐘")).tag(180);Text(L("全片")).tag(0);if ![0,60,180].contains(model.limit) {Text(L("自訂")).tag(model.limit)}}.pickerStyle(.segmented)
            HStack {Text(L("開始時間"));TextField("00:00",text:$model.startTimeText).textFieldStyle(.roundedBorder).frame(width:160);Spacer()}
            TranslationSourceControl(source:$model.translationSource)
            Toggle(L("逐片自動選字幕"),isOn:$model.batchAutoSubtitles).disabled(model.translationSource=="audio-only")
            Text(L("先找同名外掛字幕，再找內置字幕，最後用畫面 OCR。個別片源可以覆寫。")).foregroundStyle(.secondary)
            OpeningTreatmentControls(detect:$model.autoSkipOP,translate:$model.translateOPED)
            GroupBox(L("開始流程")) {Text(L("匯入 → 辨識 → 翻譯 → 批核 → 配音 → 輸出。處理中可預覽字幕，完成後可繼續修改及生成版本。")).padding(18).frame(maxWidth:.infinity,alignment:.leading)}
        }
    }
    var voiceModels:some View {
        VStack(alignment:.leading,spacing:22) {
            Text(L("配音音軌")).font(.title2.bold())
            PrimaryVoiceTracks(model:model)
            Divider()
            Text(L("已下載模型版本")).font(.headline)
            ForEach(["cosyvoice3","voxcpm2","wsyue","drama3"],id:\.self) {engine in
                let rows=VoiceModelVariant.all.filter {$0.engine==engine && model.voiceVariantReady($0)}
                let current=model.voiceModelSelection(engine)
                Picker(VoiceEngineChoice.all.first {$0.id==engine}?.title ?? engine,selection:Binding(get:{current},set:{value in model.setVoiceModel(engine,value);model.refresh()})) {
                    if !rows.contains(where:{$0.id==current}) {Text(current+" · "+L("未下載")).tag(current)}
                    ForEach(rows) {row in Text(row.title).tag(row.id)}
                }
            }
            Text(L("下載其他大小或精度，請到模型中心。大模型唔代表口語一定更準確。")).foregroundStyle(.secondary)
            Picker(L("VoxCPM2 運行裝置"),selection:$model.voxcpmDevice) {
                Text(L("Apple GPU（MPS）")).tag("mps");Text(L("CPU（較慢）")).tag("cpu")
            }
            Text(L("WenetSpeech-Yue 只提供廣東話；CPU 離線推論。")).font(.caption).foregroundStyle(.secondary)
            Button(L("開啟模型中心")) {model.section = .environment}
        }
    }
    var subtitles:some View {
        VStack(alignment:.leading,spacing:22) {
            Text(L("字幕與翻譯")).font(.title2.bold())
            TranslationSourceControl(source:$model.translationSource)
            Picker(L("字幕來源"),selection:$model.subtitleSource) {
                Text(L("畫面燒入字幕 · OCR")).tag("burned");Text(L("內置字幕軌 · MKV / MP4")).tag("embedded");Text(L("外掛字幕 · SRT / ASS / VTT")).tag("external");Text(L("冇字幕 · 日語語音辨識")).tag("none")
            }.onChange(of:model.subtitleSource) {_ in model.selectPreviewSubtitle()}
            if model.subtitleSource=="embedded",!model.subtitleTracks.isEmpty {Picker(L("選擇字幕軌"),selection:$model.subtitleStream) {ForEach(model.subtitleTracks) {track in Text(track.label).tag(track.id).disabled(!track.supported)}}}
            if model.subtitleSource=="external" {HStack {Text(model.subtitle?.lastPathComponent ?? L("請加入字幕檔"));Button(L("加入字幕"),action:model.chooseSubtitle)}}
            if model.batchAutoSubtitles {Text(L("佇列已啟用自動選字幕；上方來源只喺關閉自動選擇或個別片設定時使用。")).foregroundStyle(.orange)}
            Divider()
            Toggle(L("使用本機 AI 翻譯"),isOn:$model.translate)
            Picker(L("文字模型"),selection:$model.selectedModel) {ForEach(Array(Set(model.models+[model.selectedModel])).sorted(),id:\.self) {Text($0).tag($0)}}
            Picker(L("字幕字色"),selection:$model.ocrColor) {Text(L("保留原色（預設）")).tag("original");Text(L("白色／淺灰")).tag("white");Text(L("黃色")).tag("yellow")}
            Toggle(L("暫停只出現一個取樣畫面嘅字"),isOn:$model.ocrStable)
            Text(L("喺影片預覽按「框選字幕」，選取要辨識嘅畫面位置。")).foregroundStyle(.secondary)
        }
    }
    var roles:some View {
        VStack(alignment:.leading,spacing:22) {
            Text(L("角色與背景聲")).font(.title2.bold())
            Toggle(L(model.roleAnalysisMode=="independent" ? "自動準備逐句原聲參考":"根據原聲自動配對全部角色"),isOn:$model.autoSpeakers)
            RoleAnalysisControls(model:model)
            VoiceStyleControls(mode:$model.voiceStyleMode)
            Toggle(L("按原聲時長重錄及調整語速"),isOn:$model.autoFit)
            Toggle(L("允許已選引擎互相補聲"),isOn:$model.allowCrossEngineRepair)
            Text(L("只用已選、同角色同語言嘅錄音補缺；唔會自動用日文或未選引擎。")).font(.caption).foregroundStyle(.secondary)
            Toggle(L("分離日語對白，保留音樂／音效"),isOn:$model.separateBackground)
            HStack {Text(L("背景音量"));Slider(value:$model.backgroundGain,in:0...1.5);Text("\(Int(model.backgroundGain*100))%").monospacedDigit().frame(width:60)}
            Toggle(L("配音時自動降低背景聲"),isOn:$model.backgroundDucking).disabled(!model.separateBackground)
            Text(L("減少音樂遮蓋對白；只影響配音混音，日文原聲音軌保持完整。")).font(.caption).foregroundStyle(.secondary)
            if !model.separateBackground {Toggle(L("混入低音量原聲（包括日語對白）"),isOn:$model.mixOriginal)}
            Text(L("讀音字典（每行：原字 = 讀法）")).font(.headline)
            TextEditor(text:$model.pronunciationText).frame(height:180).font(.system(size:15)).border(StudioPalette.border)
            Text(L("新專案預設粵拼修正（GPT V4）")).font(.headline)
            TextEditor(text:$model.cantonesePronunciationText).frame(height:120).font(.system(.body,design:.monospaced)).border(StudioPalette.border)
            Text(L("每行：台詞字詞 = 粵拼。例：銀行 = ngan4 hong4。每個字一個音節，聲調 1–6。現有專案在製作頁修改。")).font(.caption).foregroundStyle(.secondary)
            Text(L("每個引擎使用各自嘅參考設定。個別角色及引擎參考可喺工作區「角色」修改。")).foregroundStyle(.secondary)
        }
    }
    var output:some View {
        VStack(alignment:.leading,spacing:22) {
            Text(L("輸出與批核")).font(.title2.bold())
            Toggle(L("自動批核字幕並配音"),isOn:$model.autoApprove)
            Toggle(L("AI 自動修復所選音軌（跟隨文字模型）"),isOn:$model.aiAutoFix)
            Text(L("生成後讀取紀錄，決定同稿重錄或使用合格同語言補聲，再驗證並顯示摘要；未解決項目保留於摘要。")).font(.caption).foregroundStyle(.secondary)
            Text(L(model.autoApprove ? "自動翻譯 → 配音 → 輸出":"手動校對模式：配音前會暫停")).foregroundStyle(.secondary)
            Toggle(L("自動修復；仍失敗就留空該段並繼續"),isOn:$model.continueOnError)
            CaptionModePicker(title:L("可切換字幕軌"),selection:$model.subtitleOutput,includeAll:true)
            Toggle(L("另外燒入固定字幕"),isOn:$model.burnOutputCaptions)
            if model.burnOutputCaptions {CaptionModePicker(title:L("固定字幕內容"),selection:$model.burnSubtitleMode,includeAll:false)}
            HStack {Text(model.exportFolder.isEmpty ? L("App 工作資料夾"):model.exportFolder).textSelection(.enabled);Spacer();Button(L("選擇輸出位置"),action:model.chooseExportFolder)}
            Text(L("字幕、草稿及配音資料存入 app 專案庫。輸出位置只保留成品 MP4。")).foregroundStyle(.secondary)
        }
    }
}
struct CaptionModePicker:View {
    let title:String
    @Binding var selection:String
    let includeAll:Bool
    var body:some View {Picker(title,selection:$selection) {
        Text(L("廣東話")).tag("yue");Text(L("英文")).tag("english");Text(L("廣東話＋英文雙行")).tag("dual");Text(L("原裝字幕文字")).tag("original");Text(L("原裝 + 廣東話")).tag("original-yue");Text(L("原裝＋英文")).tag("original-english")
        if includeAll {Text(L("三款字幕分開揀")).tag("all");Text(L("全部獨立及雙語組合")).tag("complete");Text(L("關閉")).tag("none")}
    }}
}
