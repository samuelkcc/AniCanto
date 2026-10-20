import SwiftUI

enum WorkflowTopic: String, CaseIterable, Identifiable {
    case translation, voices, output, editor
    var id: String { rawValue }
    var title: String { switch self { case .translation: return "字幕來源與翻譯";case .voices:return "角色聲線與背景聲";case .output:return "輸出進階設定";case .editor:return "編輯工具" } }
    var icon: String { switch self {case .translation:return "text.bubble";case .voices:return "waveform";case .output:return "square.stack.3d.up";case .editor:return "slider.horizontal.3"} }
    var artwork: String { switch self {case .translation,.editor:return "guide-subtitles";case .voices:return "guide-voices";case .output:return "guide-exports"} }
    var hint: String { switch self {
        case .translation:return "先聽清楚，再講得自然。"
        case .voices:return "聲線、節奏，同背景一齊夾好。"
        case .output:return "揀好音軌，準備你嘅成品。"
        case .editor:return "逐句微調，保留你想講嘅意思。"
    } }
}

/// A value snapshot: controls never mutate the live conversion settings until Apply.
struct WorkflowValues: Equatable, Codable {
    var translate: Bool;var model: String;var ocrColor: String;var ocrStable: Bool
    var autoSpeakers: Bool;var autoFit: Bool;var separate: Bool;var gain: Double;var mixOriginal: Bool;var op: Bool
    var translationSource:String?
    var translateOPED:Bool?
    var voiceStyleMode:String?
    var roleAnalysisMode:String?
    var visualRoleAnalysisEnabled:Bool?
    var backgroundDucking:Bool?
    var allowCrossEngineRepair:Bool?
    var aiAutoFix:Bool?
    var autoApprove: Bool;var burn: Bool;var engine: String;var extras: Set<String>;var original: Bool;var subtitles: String;var folder: String
    var pronunciation: String
    var cantonesePronunciation:String?
    var reviewEngine: String;var reviewFit: Bool
    @MainActor init(_ m:AppModel) {
        translationSource=m.translationSource
        translateOPED=m.translateOPED
        voiceStyleMode=m.voiceStyleMode
        aiAutoFix=m.aiAutoFix
        pronunciation=m.pronunciationText
        cantonesePronunciation=m.cantonesePronunciationText
        translate=m.translate;model=m.selectedModel;ocrColor=m.ocrColor;ocrStable=m.ocrStable
        autoSpeakers=m.autoSpeakers;autoFit=m.autoFit;separate=m.separateBackground;gain=m.backgroundGain;mixOriginal=m.mixOriginal;op=m.autoSkipOP;roleAnalysisMode=m.roleAnalysisMode;visualRoleAnalysisEnabled=m.visualRoleAnalysisEnabled;backgroundDucking=m.backgroundDucking;allowCrossEngineRepair=m.allowCrossEngineRepair
        autoApprove=m.autoApprove;burn=m.burnOutputCaptions;engine=m.ttsBackend;extras=m.extraEngines;original=m.includeOriginal;subtitles=m.subtitleOutput;folder=m.exportFolder
        reviewEngine=m.reviewBackend;reviewFit=m.reviewAutoFit
    }
    @MainActor func apply(to m:AppModel,editor:Bool) {
        if editor {m.reviewBackend=VoiceEngineChoice.active(reviewEngine);m.ttsBackend=VoiceEngineChoice.active(reviewEngine);m.reviewAutoFit=reviewFit;return}
        m.translationSource=translationSource ?? "audio-and-subtitles"
        m.translateOPED=translateOPED ?? false
        m.voiceStyleMode="clone"
        if let aiAutoFix {m.aiAutoFix=aiAutoFix}
        m.pronunciationText=pronunciation
        m.cantonesePronunciationText=cantonesePronunciation ?? ""
        m.translate=translate;m.selectedModel=model;if m.ocrColor != ocrColor {m.ocrColor=ocrColor};m.ocrStable=ocrStable
        m.autoSpeakers=autoSpeakers;m.autoFit=autoFit;m.separateBackground=separate;m.backgroundGain=gain;m.mixOriginal=mixOriginal;m.autoSkipOP=op;m.visualRoleAnalysisEnabled=visualRoleAnalysisEnabled ?? false;m.roleAnalysisMode=roleAnalysisMode=="independent" ? "independent":m.visualRoleAnalysisEnabled ? "audiovisual":"audio";m.backgroundDucking=backgroundDucking ?? false;m.allowCrossEngineRepair=allowCrossEngineRepair ?? false
        m.autoApprove=autoApprove;m.burnOutputCaptions=burn;m.ttsBackend=VoiceEngineChoice.active(engine);m.extraEngines=extras.subtracting([m.ttsBackend,"qwen-tts"]);m.includeOriginal=original;m.subtitleOutput=subtitles;m.exportFolder=folder
    }
}
@MainActor final class WorkflowDraft: ObservableObject, Identifiable {
    let id=UUID()
    let initial:WorkflowValues
    let editor:Bool
    @Published var values:WorkflowValues
    @Published var topic:WorkflowTopic
    @Published var afterApply="none"
    init(model:AppModel,topic:WorkflowTopic) {
        let values=WorkflowValues(model);self.initial=values;self.values=values;self.topic=topic;self.editor=topic == .editor
    }
    var changed:Bool { values != initial || afterApply != "none" }
    func chooseFolder() {
        let panel=NSOpenPanel();panel.canChooseFiles=false;panel.canChooseDirectories=true;panel.canCreateDirectories=true
        if !values.folder.isEmpty {panel.directoryURL=URL(fileURLWithPath:values.folder)}
        if panel.runModal() == .OK,let url=panel.url {values.folder=url.path}
    }
}

struct AdvancedSettingsView: View {
    @ObservedObject var model:AppModel
    @ObservedObject var draft:WorkflowDraft
    private var topics:[WorkflowTopic] {draft.editor ? [.editor] : [.translation,.voices,.output]}
    var body:some View {
        VStack(spacing:0) {
            HStack {
                Label(L("轉換設定"),systemImage:"slider.horizontal.3").font(.title2.bold())
                Text(L("ANICANTO / SETUP")).font(.system(size:10,weight:.semibold,design:.monospaced)).foregroundStyle(.secondary)
                Spacer()
                Button {model.advancedSettings=nil} label:{Image(systemName:"xmark")}.help("取消")
            }.padding(22).background(FrameChrome())
            Divider()
            HStack(spacing:0) {
                VStack(alignment:.leading,spacing:10) {
                    ForEach(topics) {topic in
                        Button {draft.topic=topic} label:{Label(L(topic.title),systemImage:topic.icon).font(.system(size:13,weight:.semibold)).frame(maxWidth:.infinity,alignment:.leading).padding(12).background(draft.topic == topic ? accent.opacity(0.16) : .clear,in:RoundedRectangle(cornerRadius:10))}.buttonStyle(.plain)
                    }
                    Spacer(minLength:4)
                    ZStack(alignment:.bottom) {
                        VStack(alignment:.leading,spacing:6) {
                            Label(L("CANTO / DIRECTOR"),systemImage:draft.topic.icon).font(.system(size:9,weight:.bold,design:.monospaced)).foregroundStyle(accent)
                            Text(L(draft.topic.hint)).font(.system(size:15,weight:.semibold,design:.rounded))
                        }.frame(maxWidth:.infinity,alignment:.leading).padding(15).background(surface.opacity(0.96),in:RoundedRectangle(cornerRadius:12)).overlay(RoundedRectangle(cornerRadius:12).stroke(accent.opacity(0.3)))
                    }
                }.padding(18).frame(width:260).background(FrameChrome(sidebar:true))
                ScrollView {
                    VStack(alignment:.leading,spacing:20) {
                        Label(L(draft.topic.title),systemImage:draft.topic.icon).font(.title2.bold())
                        switch draft.topic {
                        case .translation:translation
                        case .voices:voices
                        case .output:output
                        case .editor:editor
                        }
                    }.padding(26).frame(maxWidth:.infinity,alignment:.leading)
                }.background(surface)
            }
            Divider()
            HStack {
                Text(L(draft.changed ? "有未套用嘅改動" : "修改後按「套用」先會生效")).font(.caption).foregroundStyle(draft.changed ? Color.orange : .secondary)
                Spacer()
                Button(L("取消")) {model.advancedSettings=nil}.keyboardShortcut(.cancelAction).accessibilityIdentifier("settings-cancel")
                Button(L(draft.afterApply == "none" ? "套用" : "套用並執行")) {
                    guard !model.busy else {return}
                    draft.values.apply(to:model,editor:draft.editor)
                    model.advancedSettings=nil
                    switch draft.afterApply {
                    case "op":model.detectOP()
                    case "separate":model.previewSeparation()
                    case "ocr":model.previewOCR()
                    case "roles":model.section = .voices
                    case "rebuild":model.rebuildDialogue()
                    case "assign":model.autoAssignReview()
                    default:break
                    }
                }.buttonStyle(.borderedProminent).keyboardShortcut(.defaultAction).disabled(model.busy).accessibilityIdentifier("settings-apply")
            }.padding(18).background(surface)
        }.frame(width:min(1020,(NSScreen.main?.visibleFrame.width ?? 1200)-80),height:min(700,(NSScreen.main?.visibleFrame.height ?? 900)-80)).background(AnimeBackdrop()).tint(accent).interactiveDismissDisabled(draft.changed).onChange(of:draft.topic) { _ in draft.afterApply="none" }
    }
    private var translation:some View {
        VStack(alignment:.leading,spacing:18) {
            Toggle(L("用本機 AI 改成香港口語"),isOn:$draft.values.translate)
            Picker(L("文字模型"),selection:$draft.values.model) {ForEach(Array(Set(model.models+[draft.values.model])).sorted(),id:\.self) {Text($0).tag($0)}}
            Text(L("按原片日語聲音分句同定時；中文字幕只作意思／人名參考。首次會部署日語原聲辨識模型。")).font(.caption).foregroundStyle(.secondary)
            Divider()
            Text(L("畫面字幕辨識")).font(.headline)
            Picker(L("字幕字色"),selection:$draft.values.ocrColor) {Text(L("保留原色（預設）")).tag("original");Text(L("白色／淺灰")).tag("white");Text(L("黃色")).tag("yellow")}
            Toggle(L("暫停只出現一個取樣畫面嘅字"),isOn:$draft.values.ocrStable)
            Text(L("用影片下方「框選字幕範圍」，直接拖拉方框。只辨識框內畫面，黑邊唔會計入範圍。")).font(.caption).foregroundStyle(.secondary)
            if model.video != nil {Toggle(L("套用後預覽 OCR"),isOn:action("ocr"))}
        }
    }
    private var voices:some View {
        VStack(alignment:.leading,spacing:18) {
            VoiceStyleControls(mode:Binding(get:{draft.values.voiceStyleMode ?? "clone"},set:{draft.values.voiceStyleMode=$0}))
            Toggle(L("根據原聲自動配對全部角色"),isOn:$draft.values.autoSpeakers)
            Text(L("讀音字典（每行：原字 = 讀法）")).font(.headline)
            TextEditor(text:$draft.values.pronunciation).font(.body).frame(height:90).border(Color.secondary.opacity(0.3))
            Text(L("只改配音讀法，字幕保留原字。留空就用引擎原本讀音；讀法請先試聽。")).font(.caption).foregroundStyle(.secondary)
            Toggle(L("按原聲時長重錄及調整語速"),isOn:$draft.values.autoFit)
            OpeningTreatmentControls(detect:$draft.values.op,translate:Binding(get:{draft.values.translateOPED ?? false},set:{draft.values.translateOPED=$0}))
            Divider()
            Toggle(L("分離日語對白，保留音樂／音效"),isOn:$draft.values.separate)
            HStack {Text(L("背景音量"));Slider(value:$draft.values.gain,in:0...1.5);Text("\(Int(draft.values.gain*100))%").monospacedDigit().frame(width:45)}
            if !draft.values.separate {Toggle(L("混入低音量原聲（包括日語對白）"),isOn:$draft.values.mixOriginal)}
            Text(L("主引擎會成為預設音軌。可加入其他引擎比較；共用譯稿同背景，逐個生成，時間會隨引擎數目增加。")).font(.caption).foregroundStyle(.secondary)
            Picker(L("套用後動作"),selection:$draft.afterApply) {
                Text(L("只儲存設定")).tag("none");Text(L("查看自動配對／試聽")).tag("roles")
                if model.video != nil {Text(L("分析片頭 OP／片尾 ED")).tag("op")}
                if model.video != nil && model.separatorReady {Text(L("先試分離所選片段")).tag("separate")}
            }
        }
    }
    private var output:some View {
        VStack(alignment:.leading,spacing:18) {
            Text(L("配音音軌、日語原聲、字幕語言同輸出位置，請喺主畫面設定。")).font(.caption).foregroundStyle(.secondary)
            Toggle(L("輸出前手動校對"),isOn:Binding(get:{!draft.values.autoApprove},set:{draft.values.autoApprove = !$0}))
            Text(L("預設自動完成；只有啟用手動校對先會喺配音前停低。")).font(.caption).foregroundStyle(.secondary)
            Text(L("英文字幕係 AI 意譯，口語或人名可能譯錯；學習或分享前請覆核。")).font(.caption).foregroundStyle(.secondary)
            Button(L("關閉並管理模型")) {model.advancedSettings=nil;model.section = .environment}.font(.caption)
            Text(L("離開設定會放棄未套用嘅改動。")).font(.caption2).foregroundStyle(.secondary)
        }
    }
    private var editor:some View {
        VStack(alignment:.leading,spacing:18) {
            if model.reviewUsesGSV {Picker(L("配音引擎"),selection:$draft.values.reviewEngine) {ForEach(VoiceEngineChoice.all) {Text($0.title).tag($0.id)}}}
            Toggle(L("按實測時長調整語速（保留完整台詞）"),isOn:$draft.values.reviewFit)
            Picker(L("套用後動作"),selection:$draft.afterApply) {
                Text(L("只儲存設定")).tag("none");Text(L("按日語原聲重建稿")).tag("rebuild")
                if model.reviewUsesGSV {Text(L("自動配對全部角色")).tag("assign")}
            }
            Text(L("修改台詞會即時更新預覽；成品聲音需要重新配音。")).font(.caption).foregroundStyle(.secondary)
        }
    }
    private func action(_ value:String)->Binding<Bool> {Binding(get:{draft.afterApply==value},set:{draft.afterApply = $0 ? value : "none"})}
}
