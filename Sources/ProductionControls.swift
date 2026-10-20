import SwiftUI
import AVKit

struct ProductionPreferences:Codable,Equatable {
    var review:String
    var aiAutoFix:Bool
    var operation:String
    var engines:[String]
    var languages:[String]
    var regenerate:Bool
    var includeOriginal:Bool
    var scriptMode:String
    var productionMode:String? = nil
    var reanalyzeRoles:Bool? = nil
}
@MainActor final class ProductionSelection:ObservableObject {
    @Published var productionMode="normal" {didSet {changed()}}
    @Published var aiAutoFix=false {didSet {changed()}}
    @Published var operation="voice" {didSet {changed()}}
    @Published var engines=Set<String>() {didSet {changed()}}
    @Published var languages=Set<String>() {didSet {changed()}}
    @Published var regenerate=false {didSet {changed()}}
    @Published var includeOriginal=true {didSet {changed()}}
    @Published var scriptMode="missing" {didSet {changed()}}
    @Published var reanalyzeRoles=false {didSet {changed()}}
    @Published var initializedReview=""
    private var storage:URL?
    private var loading=false
    var onChange:(()->Void)?
    var onError:((Error)->Void)?
    var preferences:ProductionPreferences {ProductionPreferences(review:initializedReview,aiAutoFix:aiAutoFix,operation:operation,engines:engines.sorted(),languages:languages.sorted(),regenerate:regenerate,includeOriginal:includeOriginal,scriptMode:scriptMode,productionMode:productionMode,reanalyzeRoles:reanalyzeRoles)}
    func configure(review:String,defaults:ProductionPreferences,writable:Bool) {
        loading=true
        let file=URL(fileURLWithPath:review).deletingLastPathComponent().appendingPathComponent("production-settings.json")
        let saved=(try? Data(contentsOf:file)).flatMap {try? JSONDecoder().decode(ProductionPreferences.self,from:$0)}
        let value=saved?.review==review ? saved!:defaults
        initializedReview=review;aiAutoFix=value.aiAutoFix
        operation=["voice","subtitles","samples"].contains(value.operation) ? value.operation:"voice"
        engines=Set(value.engines.map(VoiceEngineChoice.active).filter {id in VoiceEngineChoice.all.contains {$0.id==id}})
        languages=Set(value.languages.filter {["yue","en"].contains($0)})
        regenerate=value.regenerate;includeOriginal=value.includeOriginal
        scriptMode=value.scriptMode=="all" ? "all":"missing"
        productionMode=["fast","normal","standard"].contains(value.productionMode ?? "") ? value.productionMode!:"normal"
        reanalyzeRoles=value.reanalyzeRoles ?? false
        storage=writable ? file:nil;loading=false
    }
    private func changed() {
        guard !loading else{return}
        onChange?()
        guard let storage else{return}
        do {try JSONEncoder().encode(preferences).write(to:storage,options:.atomic)}
        catch {onError?(error)}
    }
}
final class ProductionMessages:ObservableObject {@Published var error=""}

@MainActor struct ProductionControls:View {
    @ObservedObject var model:AppModel
    @ObservedObject var editor:ProjectEditor
    @ObservedObject var options:ProjectWorkspaceOptions
    @ObservedObject private var choices:ProductionSelection
    init(model:AppModel,editor:ProjectEditor,options:ProjectWorkspaceOptions,selection:ProductionSelection?=nil) {
        self.model=model;self.editor=editor;self.options=options
        _choices=ObservedObject(wrappedValue:selection ?? editor.productionSelection(model))
    }
    var orderedLanguages:[String] {["yue","en"].filter {choices.languages.contains($0)}}
    var orderedEngines:[String] {VoiceEngineChoice.all.map(\.id).filter {choices.engines.contains($0)}}
    var trackCount:Int {VoiceEngineChoice.all.filter {choices.engines.contains($0.id)}.reduce(0) {$0+$1.languages.filter {choices.languages.contains($0)}.count}}
    var body:some View {
        VStack(alignment:.leading,spacing:16) {
            Text(L("重新製作")).font(.title3.bold())
            ProductionModeControl(mode:$choices.productionMode,locked:model.busy)
            Text(L("沿用已保存原文、角色卡及時間；字幕與配音可分開更新。")).font(.caption).foregroundStyle(.secondary)
            Picker(L("製作項目"),selection:$choices.operation) {
                Text(L("配音")).tag("voice");Text(L("字幕")).tag("subtitles");Text(L("試音")).tag("samples")
            }.pickerStyle(.segmented)
            if choices.operation != "samples" {
                GroupBox(L(choices.operation=="subtitles" ? "字幕語言":"音軌語言")) {
                    VStack(alignment:.leading,spacing:8) {
                        languageToggle("yue","廣東話");languageToggle("en","英文")
                    }.frame(maxWidth:.infinity,alignment:.leading).padding(6)
                }
            }
            if choices.operation=="subtitles" {
                Picker(L("字幕處理"),selection:$choices.scriptMode) {
                    Text(L("只補缺少字幕")).tag("missing");Text(L("全部重新翻譯")).tag("all")
                }.pickerStyle(.radioGroup)
                Text(L("由已保存原文重新翻譯；原裝中文字幕、字幕時間及角色配對保留。先比較新草稿，再套用。")).font(.caption).foregroundStyle(.secondary)
            } else {
                VoiceStyleControls(mode:Binding(get:{editor.voiceStyleMode},set:{value in editor.update {$0.voiceStyleMode=value}}))
                GroupBox(L("配音引擎")) {
                    VStack(alignment:.leading,spacing:10) {
                        ForEach(VoiceEngineChoice.all) {choice in
                            Toggle(choice.title,isOn:Binding(get:{choices.engines.contains(choice.id)},set:{v in if v {choices.engines.insert(choice.id)} else {choices.engines.remove(choice.id)}})).toggleStyle(.checkbox)
                            if choices.engines.contains(choice.id) && !model.engineReady(choice.id) {Text(L("請先在模型中心部署所選引擎。")).font(.caption).foregroundStyle(.orange)}
                            if choice.id=="drama3" {Text(L("Drama 3 本機 MLX 模型；廣東話音質請先逐句試聽。")).font(.caption).foregroundStyle(.secondary)}
                            if choice.id=="wsyue" {Text(L("WenetSpeech-Yue 只提供廣東話；CPU 離線推論。")).font(.caption).foregroundStyle(.secondary)}
                        }
                    }.frame(maxWidth:.infinity,alignment:.leading).padding(6)
                }
                if choices.operation=="voice" {
                    if choices.productionMode != "fast" {
                    Toggle(L("匯出前重新分析人物（Qwen 35B）"),isOn:$choices.reanalyzeRoles).toggleStyle(.checkbox)
                    Text(L("先按原聲及連續畫面重新整理人物卡，再由 Qwen 覆核疑難配對與參考；保留字幕、時間及手動角色設定。結果存成新版本，完成後顯示摘要。")).font(.caption).foregroundStyle(.secondary)
                    if choices.reanalyzeRoles {Text(L("提交時會取代本片尚未執行的整片配音匯出，保留舊提交與音檔。")).font(.caption).foregroundStyle(.secondary)}
                    }
                    Toggle(L("所選音軌全部重新配音"),isOn:$choices.regenerate).toggleStyle(.checkbox)
                    Text(L(choices.regenerate ? "建立新錄音版本，所選音軌不沿用已有 take。":"沿用符合目前台詞、角色及引擎版本的音檔；只生成欠缺音檔。")).font(.caption).foregroundStyle(.secondary)
                    if choices.languages.contains("en") {Text(L("欠缺英文台詞時先補英文稿；如要核對翻譯，請先使用字幕頁。")).font(.caption).foregroundStyle(.secondary)}
                    Text(String(format:L("將製作 %d 條配音軌"),trackCount)).font(.headline)
                    Toggle(L("保留原裝日文音軌"),isOn:$choices.includeOriginal).toggleStyle(.checkbox)
                    if choices.productionMode != "fast" {
                    Toggle(L("AI 自動修復所選音軌（跟隨文字模型）"),isOn:$choices.aiAutoFix).toggleStyle(.checkbox)
                    Text(L("生成後讀取紀錄，決定同稿重錄或使用合格同語言補聲，再驗證並顯示摘要；未解決項目保留於摘要。")).font(.caption).foregroundStyle(.secondary)
                    }
                    Text(L("按每個引擎支援的所選語言生成；WenetSpeech-Yue 不會建立英文音軌。")).font(.caption).foregroundStyle(.secondary)
                    ForEach(orderedLanguages,id:\.self) {lang in
                        Text(L(lang=="en" ? "英文":"廣東話")+" · "+VoiceEngineChoice.all.filter {choices.engines.contains($0.id) && $0.languages.contains(lang)}.map(\.title).joined(separator:" / ")).font(.caption)
                    }
                } else {
                    Text(L("抽取最多 20 句、跨角色的廣東話試音，逐句覆聽；不合片、不替換成品。")).font(.caption).foregroundStyle(.secondary)
                }
            }
            Button(L(model.busy || model.queuePaused ? "保存並排隊":choices.operation=="subtitles" ? "建立字幕草稿":choices.operation=="samples" ? "建立廣東話試音組":choices.reanalyzeRoles ? "重新分析人物並製作新版":(choices.regenerate ? "全部所選配音重新生成並合片":"補回缺少配音並合片")),action:submit)
                .buttonStyle(StudioButtonStyle(prominent:true))
                .disabled(editor.readOnlyPreview || editor.document==nil || (choices.operation != "samples" && choices.languages.isEmpty) || (choices.operation=="voice" && trackCount==0) || (choices.operation != "subtitles" && (choices.engines.isEmpty || choices.engines.contains { !model.engineReady($0) })))
            if model.queuePaused {Text(L("工作佇列已暫停；提交後按右上角「繼續處理」啟動。")).font(.caption).foregroundStyle(.secondary)}
            else if model.busy {Text(L("目前工作正在處理；新增工作會排在其後。")).font(.caption).foregroundStyle(.secondary)}
            if choices.operation != "subtitles" {pronunciation}
            if choices.operation=="voice" {
                GroupBox(L("輸出字幕 · 可多選")) {
                    VStack(alignment:.leading,spacing:8) {
                        ForEach([("yue","廣東話字幕"),("english","英文字幕"),("original","原片字幕")],id:\.0) {key,title in
                            Toggle(L(title),isOn:Binding(get:{editor.outputSubtitleModes.contains(key)},set:{editor.setOutputSubtitle(key,$0)})).toggleStyle(.checkbox)
                        }
                    }.frame(maxWidth:.infinity,alignment:.leading).padding(6)
                }
            }

            if !editor.scriptVersions.isEmpty {
                Divider();Text(L("字幕草稿待核對")).font(.headline)
                ForEach(editor.scriptVersions.prefix(3)) {v in
                    Button {options.subtitleProposal=v} label:{Label(v.created,systemImage:"text.badge.checkmark")}
                }
            }
            if !editor.sampleVersions.isEmpty {
                Divider();Text(L("廣東話試音組")).font(.headline)
                ForEach(editor.sampleVersions.prefix(3)) {v in
                    Button {options.voiceSampleVersion=v} label:{Label(v.created,systemImage:"waveform")}
                }
            }
            Text(L("新版本會出現在成品頁；舊成品保留。")).font(.caption).foregroundStyle(.secondary)
            if let error=editor.error {Text(error).font(.caption).foregroundStyle(.red).textSelection(.enabled)}
        }.onAppear(perform:initialize).onChange(of:editor.document?.review) {_ in initialize()}
    }
    func languageToggle(_ language:String,_ title:String)->some View {
        Toggle(L(title),isOn:Binding(get:{choices.languages.contains(language)},set:{v in if v {choices.languages.insert(language)} else {choices.languages.remove(language)}})).toggleStyle(.checkbox)
    }
    var pronunciation:some View {
        DisclosureGroup(L("廣東話讀音與參考")) {
            VStack(alignment:.leading,spacing:10) {
                Text(L("GPT 粵拼修正（每個字一個音節，聲調 1–6）")).font(.headline)
                TextEditor(text:Binding(get:{editor.document?.cantonesePronunciationText ?? editor.config["cantonesePronunciationText"] as? String ?? model.cantonesePronunciationText},set:{value in editor.update {$0.cantonesePronunciationText=value}}))
                    .font(.system(.body,design:.monospaced)).frame(height:120).border(StudioPalette.border)
                Text("銀行 = ngan4 hong4").font(.caption.monospaced()).textSelection(.enabled)
                Text(L("只改新生成 GPT 廣東話的音素輸入；字幕原文保持不變。其他引擎沿用自己的讀音方式。")).font(.caption).foregroundStyle(.secondary)
                Button(L(editor.isIndependentVoiceMapping ? "逐句配音參考":"角色參考與試聽")) {RoleManagerWindow.present(model:model,editor:editor)}
                    .disabled(editor.profiles.isEmpty)
                Text(L(editor.isIndependentVoiceMapping ? "每句可更換自己的參考聲或修改原文；短句參考同聲調需要試聽。":"可在角色卡匯入經試聽確認的 3–10 秒廣東話參考。音素正確或覆聽文字一致，仍不代表聲調自然。")).font(.caption).foregroundStyle(.secondary)
            }.padding(.top,8)
        }
    }
    func initialize() {
        guard let review=editor.document?.review,choices.initializedReview != review else{return}
        choices.configure(review:review,defaults:editor.productionDefaults(model),writable:!editor.readOnlyPreview)
    }
    func submit() {
        if choices.operation=="subtitles" {
            model.submitEditor(audioSettings:["subtitlesOnly":true,"scriptLanguages":orderedLanguages,"scriptRevisionMode":choices.scriptMode])
        } else {
            var settings:[String:Any]=["selectedEngines":orderedEngines,"defaultAudioEngine":orderedEngines[0],"dubLanguages":choices.operation=="samples" ? ["yue"]:orderedLanguages,"audioOnlyRerun":true,"includeOriginal":choices.includeOriginal]
            settings["productionMode"]=choices.productionMode
            settings["aiAutoFix"]=choices.operation=="voice" && choices.aiAutoFix
            settings["aiRepairModel"]=model.selectedModel
            settings["reanalyzeRoles"]=choices.operation=="voice" && choices.reanalyzeRoles
            if choices.operation=="voice" && choices.reanalyzeRoles {
                settings["visualModel"]=model.selectedModelID("visual")
                settings["roleDecisionModel"]=model.selectedModelID("visual")
                settings["fillMissingVoiceScripts"]=true
            }
            if choices.operation=="samples" {settings["voiceSamplesOnly"]=true;settings["audioRerunToken"]=UUID().uuidString}
            else if choices.regenerate {settings["audioRerunToken"]=UUID().uuidString}
            model.submitEditor(audioSettings:ProductionModePolicy.applying(to:settings))
        }
    }
}

extension ProjectEditor {
    func productionDefaults(_ model:AppModel)->ProductionPreferences {
        let review=document?.review ?? ""
        // Seed older projects from their most recent whole-project voice request,
        // excluding auditions and single-track repairs.
        let pending=model.editorTasks.reversed().lazy.filter {$0.review==review}.compactMap {task -> [String:Any]? in
            guard let data=try? Data(contentsOf:URL(fileURLWithPath:task.submission)),let row=try? JSONSerialization.jsonObject(with:data) as? [String:Any],row["previewOnly"] as? Bool != true,row["previewSegment"]==nil,row["previewEngine"]==nil,let settings=row["settings"] as? [String:Any],settings["audioOnlyRerun"] as? Bool==true,settings["voiceSamplesOnly"] as? Bool != true,settings["repairTrack"]==nil else{return nil}
            return settings
        }.first ?? [:]
        return ProductionPreferences(review:review,aiAutoFix:pending["aiAutoFix"] as? Bool ?? config["aiAutoFix"] as? Bool ?? model.aiAutoFix,operation:"voice",engines:pending["selectedEngines"] as? [String] ?? config["selectedEngines"] as? [String] ?? model.selectedEngines,languages:pending["dubLanguages"] as? [String] ?? document?.dubLanguages ?? config["dubLanguages"] as? [String] ?? ["yue"],regenerate:pending["audioRerunToken"] != nil,includeOriginal:pending["includeOriginal"] as? Bool ?? config["includeOriginal"] as? Bool ?? true,scriptMode:"missing",productionMode:pending["productionMode"] as? String ?? config["productionMode"] as? String ?? model.productionMode,reanalyzeRoles:pending["reanalyzeRoles"] as? Bool ?? false)
    }
    func productionSelection(_ model:AppModel)->ProductionSelection {
        guard let review=document?.review else{return ProductionSelection()}
        if let existing=productionSelections[review] {return existing}
        let selection=ProductionSelection()
        selection.configure(review:review,defaults:productionDefaults(model),writable:!readOnlyPreview)
        selection.onChange={ [weak self,weak model,weak selection] in
            guard let self,let model,let selection,self.document?.review==review else{return}
            self.objectWillChange.send()
            model.workspaceEngineSyncing=true
            defer {model.workspaceEngineSyncing=false}
            if !selection.engines.isEmpty {
                let primary=selection.engines.contains(model.ttsBackend) ? model.ttsBackend:selection.engines.sorted()[0]
                model.ttsBackend=primary;model.extraEngines=selection.engines.subtracting([primary])
            }
            model.includeOriginal=selection.includeOriginal;model.aiAutoFix=selection.aiAutoFix;model.productionMode=selection.productionMode
            let languages=["yue","en"].filter {selection.languages.contains($0)}
            if !languages.isEmpty,self.document?.dubLanguages != languages {self.update {$0.dubLanguages=languages}}
        }
        selection.onError={ [weak self] in self?.error=$0.localizedDescription }
        productionSelections[review]=selection
        return selection
    }
}

extension ProjectEditor {
    var scriptVersions:[EditVersion] {versions.filter {$0.status=="script-ready" || $0.status=="script-partial"}}
    var sampleVersions:[EditVersion] {versions.filter {$0.status=="voice-samples"}}
    func subtitleProposal(_ version:EditVersion)->EditDocument? {
        guard let data=try? Data(contentsOf:version.folder.appendingPathComponent("subtitle-draft.json")) else{return nil}
        return try? JSONDecoder().decode(EditDocument.self,from:data)
    }
    func subtitleLanguages(_ version:EditVersion)->[String] {
        guard let data=try? Data(contentsOf:version.folder.appendingPathComponent("version.json")),let json=try? JSONSerialization.jsonObject(with:data) as? [String:Any] else{return []}
        return json["scriptLanguages"] as? [String] ?? []
    }
    func applySubtitleProposal(_ version:EditVersion) throws {
        guard !readOnlyPreview,let current=document,let proposal=subtitleProposal(version),proposal.review==current.review else {throw AppFailure(message:L("字幕草稿不屬於目前專案。"))}
        let data=try Data(contentsOf:version.folder.appendingPathComponent("version.json"))
        let record=try JSONSerialization.jsonObject(with:data) as! [String:Any]
        guard let path=record["submission"] as? String else {throw AppFailure(message:L("字幕草稿來源遺失。"))}
        let original=try JSONDecoder().decode(EditDocument.self,from:Data(contentsOf:URL(fileURLWithPath:path)))
        let languages=subtitleLanguages(version)
        guard Set(current.segments.map(\.id))==Set(original.segments.map(\.id)),Set(current.segments.map(\.id))==Set(proposal.segments.map(\.id)) else {throw AppFailure(message:L("對白結構已修改，請重新建立字幕草稿。"))}
        let before=Dictionary(uniqueKeysWithValues:original.segments.map {($0.id,$0)})
        guard current.segments.allSatisfy({s in (!languages.contains("yue") || (s.text==before[s.id]?.text && s.captionText==before[s.id]?.captionText)) && (!languages.contains("en") || s.english==before[s.id]?.english)}) else {throw AppFailure(message:L("台詞已修改，請重新建立草稿，避免覆蓋新修改。"))}
        let generated=Dictionary(uniqueKeysWithValues:proposal.segments.map {($0.id,$0)})
        update {doc in
            for i in doc.segments.indices {
                guard let new=generated[doc.segments[i].id],doc.segments[i].enabled else{continue}
                if languages.contains("yue"),!new.text.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty {
                    if doc.segments[i].text != new.text {doc.segments[i].audioTake=nil}
                    doc.segments[i].text=new.text;doc.segments[i].captionText=new.captionText
                }
                if languages.contains("en"),let text=new.english,!text.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty {
                    if doc.segments[i].english != text {doc.segments[i].audioTake=nil}
                    doc.segments[i].english=text
                }
            }
            if languages.contains("en") {doc.subtitleOutput="separate"}
        }
        try save()
        var applied=record;applied["status"]="script-applied";applied["applied"]=ISO8601DateFormatter().string(from:Date())
        try JSONSerialization.data(withJSONObject:applied,options:[.prettyPrinted,.sortedKeys]).write(to:version.folder.appendingPathComponent("version.json"),options:.atomic)
        loadVersions()
    }
}

struct SubtitleProposalView:View {
    @ObservedObject var editor:ProjectEditor
    let version:EditVersion
    @Environment(\.dismiss) private var dismiss
    @StateObject private var messages=ProductionMessages()
    func rowTitle(_ row:EditSegment)->String {
        let role=editor.profiles.first(where:{$0.id==row.speakerId})
        let name=role.map {localizedRoleName($0.name)} ?? row.speakerId
        return studioTimecode(row.captionStart)+" · "+name
    }
    var body:some View {
        VStack(alignment:.leading,spacing:14) {
            HStack {Text(L("比較字幕草稿")).font(.title2.bold());Spacer();Button(L("關閉")) {dismiss()}}
            Text(L("左邊目前台詞，右邊新草稿。套用只更新所選語言，保留時間與角色；可以撤銷。")).font(.caption).foregroundStyle(.secondary)
            if let proposal=editor.subtitleProposal(version) {
                ScrollView {LazyVStack(alignment:.leading,spacing:12) {
                    ForEach(proposal.segments.filter(\.enabled)) {new in
                        if let old=editor.document?.segments.first(where:{$0.id==new.id}) {
                            Text(rowTitle(old)).font(.caption).foregroundStyle(.secondary)
                            ForEach(editor.subtitleLanguages(version),id:\.self) {language in
                                HStack(alignment:.top,spacing:16) {
                                    Text(language=="en" ? old.english ?? "":old.text).frame(maxWidth:.infinity,alignment:.leading)
                                    Text(language=="en" ? new.english ?? "":new.text).frame(maxWidth:.infinity,alignment:.leading)
                                }.textSelection(.enabled)
                            }
                            Divider()
                        }
                    }
                }}
                if !messages.error.isEmpty {Text(messages.error).foregroundStyle(.red)}
                HStack {
                    Button(L("字幕檔案")) {NSWorkspace.shared.activateFileViewerSelecting([version.folder])}
                    Spacer();Button(L("套用所選語言草稿")) {do {try editor.applySubtitleProposal(version);dismiss()} catch {messages.error=error.localizedDescription}}.buttonStyle(StudioButtonStyle(prominent:true))
                }
            } else {Text(L("字幕草稿來源遺失。"))}
        }.padding(22).frame(width:820,height:600).background(StudioPalette.panel)
    }
}

struct VoiceSamplesView:View {
    @ObservedObject var editor:ProjectEditor
    let version:EditVersion
    @Environment(\.dismiss) private var dismiss
    var rows:[[String:Any]] {
        guard let data=try? Data(contentsOf:version.folder.appendingPathComponent("voice-samples.json")),let object=try? JSONSerialization.jsonObject(with:data) as? [String:Any] else{return []}
        return object["rows"] as? [[String:Any]] ?? []
    }
    var errors:[String:String] {
        guard let data=try? Data(contentsOf:version.folder.appendingPathComponent("voice-samples.json")),let object=try? JSONSerialization.jsonObject(with:data) as? [String:Any] else{return [:]}
        return object["errors"] as? [String:String] ?? [:]
    }
    var body:some View {
        VStack(alignment:.leading,spacing:14) {
            HStack {Text(L(rows.contains {$0["candidate"] != nil} ? "A／B 試音比較":"試音組")).font(.title2.bold());Spacer();Button(L("關閉")) {editor.audio.pause();dismiss()}}
            Text(L("覆聽文字只供核對；請聽字詞、聲調與角色聲線。試音不會自動套用到成品。")).font(.caption).foregroundStyle(.secondary)
            ForEach(errors.keys.sorted(),id:\.self) {key in Text(key+"："+(errors[key] ?? "")).font(.caption).foregroundStyle(.orange)}
            ScrollView {LazyVStack(alignment:.leading,spacing:12) {
                ForEach(Array(rows.enumerated()),id:\.offset) {_,row in
                    let check=row["speechCheck"] as? [String:Any] ?? [:]
                    HStack {
                        Text(((row["candidate"] as? String).map {$0+" · "} ?? "") + (row["engineTitle"] as? String ?? "")+" · "+((row["voiceStyleMode"] as? String).map {L($0=="clone" ? "模仿聲音":"自然聲")} ?? (row["role"] as? String ?? ""))).font(.headline)
                        Spacer();Button(L("播放")) {if let path=row["audio"] as? String {editor.player.pause();editor.audio.replaceCurrentItem(with:AVPlayerItem(url:URL(fileURLWithPath:path)));editor.audio.play()}}.disabled(row["audio"]==nil)
                    }
                    if let error=row["error"] as? String {
                        Text(error).foregroundStyle(.orange).font(.caption)
                        if let path=row["diagnosticAudio"] as? String {Button(L("聽未通過檢查嘅試音")) {editor.player.pause();editor.audio.replaceCurrentItem(with:AVPlayerItem(url:URL(fileURLWithPath:path)));editor.audio.play()}}
                    }
                    Text(row["text"] as? String ?? "").textSelection(.enabled)
                    Text(L("覆聽")+"："+(check["heard"] as? String ?? L("未完成"))).font(.caption).foregroundStyle(.secondary).textSelection(.enabled)
                    if check["requiresReview"] as? Bool ?? true {Label(L("需要試聽覆核"),systemImage:"exclamationmark.triangle").font(.caption).foregroundStyle(.orange)}
                    Divider()
                }
            }}
        }.padding(22).frame(width:720,height:580).background(StudioPalette.panel)
    }
}
