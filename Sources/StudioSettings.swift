import SwiftUI
import Metal

func gsvModelTitle(_ version:String)->String {version=="v2ProPlus" ? "V2 Pro Plus":version.uppercased()}

struct VoiceEngineChoice: Identifiable, Decodable {
    let id: String
    let title: String
    let memory: String
    let download: String
    let kind: String
    static func active(_ id:String)->String {id == "qwen-tts" ? "cosyvoice3":id == "gpt-sovits-v3" ? "gpt-sovits":id}
    static func requiresReference(_ id:String)->Bool {all.contains {$0.id==id} || ["gpt-sovits-v3","qwen-tts"].contains(id)}
    static let gpt = Self(id:"gpt-sovits", title:"GPT-SoVITS V4", memory:"16 GB+", download:"1.82 GB", kind:"gsv")
    var gsvVersion:String? {id=="gpt-sovits-v2" ? "v2ProPlus":id=="gpt-sovits-v3" ? "v3":id=="gpt-sovits" ? "v4":nil}
    var shortTitle:String {if id=="gpt-sovits-v2" {return "V2 Pro+"};return gsvVersion.map {"GPT "+$0.uppercased()} ?? (id=="voxcpm2" ? "VoxCPM2":id=="wsyue" ? "WS-Yue":id=="drama3" ? "Drama 3":"Cosy 3")}
    var languages:[String] {StudioContract.rows.first {$0.id==id}?.languages ?? ["yue","en"]}
    static let all:[Self] = StudioContract.rows.map {Self(id:$0.id,title:$0.title,memory:$0.memory,download:$0.download,kind:$0.kind)}
}

extension AppModel {
    var selectedEngines: [String] { let primary=VoiceEngineChoice.active(ttsBackend); return [primary] + extraEngines.filter { id in id != primary && VoiceEngineChoice.all.contains(where:{$0.id==id}) }.sorted() }
    func voiceModelSelection(_ id:String)->String {switch id {case "gpt-sovits-v2":return "v2ProPlus";case "gpt-sovits":return "v4";case "gpt-sovits-v3":return "v3";case "drama3":return drama3Model;case "voxcpm2":return voxcpmModel;case "wsyue":return wsyueModel;case "qwen-tts":return qwenModel;default:return cosyModel}}
    func setVoiceModel(_ id:String,_ value:String) {switch id {case "gpt-sovits-v2","gpt-sovits","gpt-sovits-v3":break;case "drama3":drama3Model=value;case "voxcpm2":voxcpmModel=value;case "wsyue":wsyueModel=value;case "qwen-tts":qwenModel=value;default:cosyModel=value}}
    func engineReady(_ id: String,language:String?=nil) -> Bool {
        if let language,let choice=VoiceEngineChoice.all.first(where:{$0.id==id}),!choice.languages.contains(language) {return false}
        return id.hasPrefix("gpt-sovits") ? engine.gsvVersionReady(VoiceEngineChoice.all.first {$0.id==id}?.gsvVersion ?? "v4") : VoiceModelVariant.all.first(where:{$0.id == voiceModelSelection(id)}).map(voiceVariantReady) ?? false
    }
    var outputSettings: [String:Any] { ["translationSource":translationSource,"productionMode":productionMode,"fallbackToRoleVoice":true,"requireCompleteDubbing":true,"cantoneseLocale":"yue-HK","autoSkipOP":autoSkipOP,"translateOPED":translateOPED,"voxcpmModel":voxcpmModel,"wsyueModel":wsyueModel,"drama3Model":drama3Model,"voxcpmDevice":voxcpmDevice,"aiAutoFix":aiAutoFix,"aiRepairModel":selectedModel,"voiceStyleMode":"clone","gsvSampleSteps":voiceRenderMode=="balanced" ? 16:32,"maxNaturalCandidates":0,"speechModel":engine.selectedVariant("speech",default:"whisper-large-v3"),"referenceSpeechModel":engine.selectedVariant("referenceSpeech",default:"whisper-small"),"asrModel":engine.selectedVariant("asr",default:"asr-1.7b-bf16"),"dubLanguages":dubLanguages,"defaultDubLanguage":dubLanguages[0],"qwenModel":qwenModel,"qwenReferenceMode":qwenReferenceMode,"gsvReferenceMode":gsvReferenceMode,"cosyModel":cosyModel,"pronunciationText":pronunciationText,"cantonesePronunciationText":cantonesePronunciationText, "selectedEngines":selectedEngines, "defaultAudioEngine":ttsBackend, "includeOriginal":includeOriginal, "subtitleOutput":subtitleOutput, "burnSubtitleMode":burnSubtitleMode, "exportFolder":exportFolder] }
    func chooseExportFolder() {
        let panel = NSOpenPanel(); panel.canChooseDirectories = true; panel.canChooseFiles = false; panel.canCreateDirectories = true
        if !exportFolder.isEmpty { panel.directoryURL = URL(fileURLWithPath:exportFolder) }
        if panel.runModal() == .OK, let folder = panel.url { exportFolder = folder.path }
    }
    func removeEngine(_ choice: VoiceEngineChoice) {
        guard !busy else { return }
        let alert = NSAlert(); alert.messageText = "移除 \(choice.title)？"; alert.informativeText = "只移除呢個 App 下載嘅模型同就緒記錄；已生成影片、角色參考同內置程式庫會保留。GPT-SoVITS 內置權重只停用，唔會修改 App 簽署。"; alert.addButton(withTitle:"移除"); alert.addButton(withTitle:"取消")
        guard alert.runModal() == .alertFirstButtonReturn else { return }
        do {
            let fm = FileManager.default
            for suffix in [choice.gsvVersion.map {"gsv-\($0)-ready.json"} ?? "\(choice.kind)-ready.json"] + (choice.gsvVersion == nil ? ["models/\(choice.id)"]:[]) {
                let url = engine.root.appendingPathComponent(suffix)
                if fm.fileExists(atPath:url.path) { try fm.removeItem(at:url) }
            }
            extraEngines.remove(choice.id); refresh()
        } catch { self.error = error.localizedDescription }
    }
    func removeTextModel(_ name: String) {
        guard !busy else { return }
        let alert = NSAlert(); alert.messageText = "移除 \(name)？"; alert.informativeText = "之後可以重新下載；唔會刪除影片或配音稿。"; alert.addButton(withTitle:"移除"); alert.addButton(withTitle:"取消")
        guard alert.runModal() == .alertFirstButtonReturn else { return }
        let e = engine
        task("移除文字模型") { if name.hasPrefix("mlx:") { try e.removeMLXText(name); return }; try e.startServer(); _ = try e.request("/api/delete", timeout:120, body:["model":name], method:"DELETE") }
    }
}

final class PlayerSelection: ObservableObject {
    @Published var audio: Int32 = -1
    @Published var subtitle: Int32 = -1
}

struct PlayerTrackControls: View {
    let player: CantoPlayer
    @StateObject private var selection = PlayerSelection()
    var body: some View {
        TimelineView(.periodic(from:.now,by:1)) { _ in
            HStack {
                Picker(L("播放音軌"), selection:$selection.audio) {
                    ForEach(player.trackDescriptions(audio:true), id:\.id) { row in Text(row.name).tag(row.id) }
                }.onChange(of:selection.audio) { player.selectTrack($0,audio:true) }
                Picker(L("播放字幕"), selection:$selection.subtitle) {
                    Text(L("關閉")).tag(Int32(-1))
                    ForEach(player.trackDescriptions(audio:false).filter { $0.id >= 0 }, id:\.id) { row in Text(row.name).tag(row.id) }
                }.onChange(of:selection.subtitle) { player.selectTrack($0,audio:false) }
            }.onChange(of:player.trackDescriptions(audio:true).map(\.id)) { _ in selection.audio = player.selectedTrack(audio:true); selection.subtitle = player.selectedTrack(audio:false) }.onAppear { selection.audio = player.selectedTrack(audio:true); selection.subtitle = player.selectedTrack(audio:false) }
        }.font(.caption)
    }
}

extension ContentView {
    var outputSettingsView: some View { OutputOptions(m:m) }
    var modelManager: some View {
        VStack(alignment:.leading,spacing:16) {
            Label(L("電腦容量與模型管理"),systemImage:"memorychip").font(.title2.bold())
            Text("\(ProcessInfo.processInfo.physicalMemory / 1_073_741_824) GB unified memory · \(MTLCreateSystemDefaultDevice()?.name ?? "CPU")").font(.headline)
            if let values = try? m.engine.root.resourceValues(forKeys:[.volumeAvailableCapacityForImportantUsageKey]), let free = values.volumeAvailableCapacityForImportantUsage {
                Text(L("可用儲存空間")+": "+ByteCountFormatter.string(fromByteCount:free,countStyle:.file))
            }
            Text(L("容量參考：8 GB 建議先試短片及 4B 文字模型；16 GB 以 4B 開始；32 GB+ 可試 14B。模型逐個載入，仍要預留系統、影片及背景分離用量；唔係速度或記憶體保證。")).font(.caption).foregroundStyle(.secondary)
            Divider()
            Text(L("文字模型 · 用戶自行選擇下載")).font(.headline)
            ModelLibrary(model:m,category:"text",role:"text")
            Picker(L("預設文字模型"),selection:$m.selectedModel) {
                ForEach(Array(Set(m.models + [m.selectedModel])).sorted(),id:\.self) { Text($0).tag($0) }
            }
            HStack {
                TextField(L("Ollama 模型名稱，例如 qwen3:4b"),text:$m.customTextModel)
                Button(L("下載")) {
                    let name = m.customTextModel.trimmingCharacters(in:.whitespacesAndNewlines)
                    guard name.range(of:#"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,120}$"#,options:.regularExpression) != nil else { m.error = "模型名稱格式無效。"; return }
                    let e = m.engine; m.task("下載文字模型") { try e.pullModel(name) }
                }.disabled(m.customTextModel.isEmpty)
            }
            Text(L("Qwen 3.5／其他版本可以輸入 Ollama tag 下載，但需由伺服器支援；未驗證嘅版本唔會標成推薦。Qwen 文字模型同 Qwen3-TTS 語音模型係分開嘅。")).font(.caption).foregroundStyle(.secondary)
            ForEach(m.models,id:\.self) { name in
                HStack { Text(name).font(.caption.monospaced()); Spacer(); Button(L("設為預設")) { m.selectedModel = name }; Button(L("測試")) {
                    let e = m.engine
                    m.task("測試文字模型") { try e.startTextModel(name); let response = try e.request("/api/generate",timeout:180,body:["model":name,"prompt":"用香港廣東話打個招呼，只回一句。","stream":false,"think":false,"options":["num_predict":64]]); guard let object = try JSONSerialization.jsonObject(with:response) as? [String:Any], let text = object["response"] as? String, !text.isEmpty else { throw AppFailure(message:"模型測試未回傳文字。") }; e.event("完成",text,1) }
                }; Button(L("移除…"),role:.destructive) { m.removeTextModel(name) } }
            }
        }.card().disabled(m.busy)
    }
    var settingsView: some View { StudioPreferences() }
}

struct StudioPreferences: View {
    @EnvironmentObject var model: AppModel
    @AppStorage("studioLanguage") private var language = "system"
    @Environment(\.locale) private var locale
    @AppStorage("studioTheme") private var appearance = "system"
    @AppStorage("animeTheme") private var anime = "studio"
    @AppStorage("randomAnimeTheme") private var random = false
    @AppStorage("randomThemes") private var randomThemes = "energy,ocean,ninja,retro,forest,future"
    @AppStorage("hardwareGuide") private var hardware = "auto"
    @AppStorage("companionMotion") private var companionMotion = true
    var body: some View {
        VStack(alignment:.leading,spacing:22) {
            VStack(alignment:.leading,spacing:14) {
                Text(L("介面與助手")).font(.title2.bold())
                Picker("Language",selection:$language) { Text("System").tag("system"); Text(L("香港繁體中文")).tag("zh-HK"); Text("English").tag("en") }
                Picker(L("外觀"),selection:$appearance) { Text(L("跟隨系統")).tag("system"); Text(L("淺色")).tag("light"); Text(L("深色")).tag("dark") }
                Picker(L("桌面角色"),selection:$anime) {ForEach(StudioThemeChoice.all) {Text(L($0.title)).tag($0.id)}}
                Toggle(L("角色動態效果"),isOn:$companionMotion)
                Text(L("角色會跟工作狀態轉換表情；關閉動態或啟用系統「減少動態效果」會停止呼吸同擺動。背景視窗會暫停動畫。")).font(.caption).foregroundStyle(.secondary)
                Toggle(L("每次啟動隨機助手"),isOn:$random)
                if random {
                    Text(L("隨機助手範圍")).font(.caption)
                    LazyVGrid(columns:[GridItem(.adaptive(minimum:150))],alignment:.leading) {
                        ForEach(["energy","ocean","ninja","retro","forest","future"],id:\.self) { key in
                            Toggle(["energy":"熱血冒險","ocean":"海上旅程","ninja":"夜行忍者","retro":"80 年代動畫","forest":"森林手繪","future":"未來日常"][key].map { L($0) } ?? key,isOn:Binding(get:{randomThemes.split(separator:",").contains(Substring(key))},set:{ enabled in
                                var values=Set(randomThemes.split(separator:",").map(String.init)); if enabled { values.insert(key) } else if values.count>1 { values.remove(key) }; randomThemes=values.sorted().joined(separator:",")
                            }))
                        }
                    }
                }
                Text(L("助手喺啟動時揀一次，轉換途中唔會跳換。人物係原創。")).font(.caption).foregroundStyle(.secondary)
            }.card()
            Button(L("About AniCanto · 授權與程式庫")) { model.showAbout=true }.buttonStyle(.borderedProminent)
        }
    }
}

func localizedRoleName(_ name:String)->String {
    if name.hasPrefix("第 "),name.hasSuffix(" 句原聲"),let number=Int(name.dropFirst(2).dropLast(4)) {return String(format:L("第 %d 句原聲"),number)}
    if name.hasPrefix("自動角色 "),let number=Int(name.dropFirst(5)) {return String(format:L("自動角色 %d"),number)}
    return L(name)
}
func L(_ key: String) -> String {
    let selected = UserDefaults.standard.string(forKey:"studioLanguage") ?? "system"
    let language = selected == "system" ? (Locale.preferredLanguages.first?.hasPrefix("en") == true ? "en" : "zh-HK") : selected
    guard let path = Bundle.main.path(forResource:language,ofType:"lproj"), let bundle = Bundle(path:path) else { return key }
    return bundle.localizedString(forKey:key,value:key,table:nil)
}

struct HardwarePresetView: View {
    @ObservedObject var model: AppModel
    @AppStorage("hardwarePreset") private var preset = "auto"
    private var small: Bool { preset == "8" || preset == "16" || (preset == "auto" && ProcessInfo.processInfo.physicalMemory < 32 * 1_073_741_824) }
    var body: some View {
        VStack(alignment:.leading,spacing:8) {
            Picker(L("模型預設建議"),selection:$preset) {
                Text("Auto · This Mac").tag("auto")
                Text(L("8 GB · 4B 文字、短片試用")).tag("8")
                Text(L("16 GB · 4B 文字、單引擎")).tag("16")
                Text(L("32 GB+ · 14B 文字、多音軌")).tag("32")
            }
            Button(L("套用文字模型建議（唔會自動下載）")) { model.selectedModel = small ? "qwen3:4b" : "qwen3:14b" }
        }
    }
}

struct OutputOptions: View {
    @ObservedObject var m: AppModel
    var body: some View {
        VStack(alignment:.leading,spacing:14) {
            Label(L("04  音軌、字幕與輸出"),systemImage:"square.stack.3d.up").font(.headline)
            Text(L("主引擎會成為預設音軌。可加入其他引擎比較；共用譯稿同背景，逐個生成，時間會隨引擎數目增加。")).font(.caption).foregroundStyle(.secondary)
            ForEach(VoiceEngineChoice.all) { choice in
                HStack {
                    Toggle(choice.title, isOn:Binding(get:{m.selectedEngines.contains(choice.id)},set:{ enabled in
                        if enabled { m.extraEngines.insert(choice.id) } else { m.extraEngines.remove(choice.id) }
                    })).disabled(choice.id == m.ttsBackend || !m.engineReady(choice.id))
                    Spacer()
                    if choice.id == m.ttsBackend { Text(L("預設音軌")).font(.caption).foregroundStyle(accent) }
                    else if m.engineReady(choice.id) { Button(L("設為預設")) { m.extraEngines.insert(m.ttsBackend); m.ttsBackend = choice.id; m.reviewBackend = choice.id } }
                    else { Button(L("下載模型")) { m.section = .environment } }
                }
            }
            Toggle(L("加入日語原聲音軌"),isOn:$m.includeOriginal)
            Text(L("按每個引擎支援的所選語言生成；WenetSpeech-Yue 不會建立英文音軌。")).font(.caption).foregroundStyle(.secondary)
            Toggle(L("AI 自動修復所選音軌（跟隨文字模型）"),isOn:$m.aiAutoFix)
            Text(L("生成後讀取紀錄，決定同稿重錄或使用合格同語言補聲，再驗證並顯示摘要；未解決項目保留於摘要。")).font(.caption).foregroundStyle(.secondary)
            Picker(L("輸出字幕"),selection:$m.subtitleOutput) {
                Text(L("廣東話")).tag("yue"); Text("English").tag("english"); Text(L("廣東話 + English 雙行")).tag("dual"); Text(L("三款字幕分開揀")).tag("all");Text(L("原裝字幕文字")).tag("original");Text(L("原裝 + 廣東話")).tag("original-yue");Text(L("原裝 + English")).tag("original-english");Text(L("全部獨立及雙語組合")).tag("complete"); Text(L("無字幕")).tag("none")
            }
            Text(L("英文字幕係 AI 意譯，口語或人名可能譯錯；學習或分享前請覆核。")).font(.caption).foregroundStyle(.orange)
            Text(L("英文按最終廣東話稿翻譯，需要已下載嘅文字模型。每個配音引擎有自己嘅字幕時間；播放器唔一定會自動跟音軌換字幕。")).font(.caption).foregroundStyle(.secondary)
            HStack {
                Image(systemName:"folder")
                Text(m.exportFolder.isEmpty ? L("App 工作資料夾（預設）") : m.exportFolder).font(.caption).textSelection(.enabled).lineLimit(2)
                Spacer(); Button(L("選擇輸出資料夾"),action:m.chooseExportFolder)
                if !m.exportFolder.isEmpty { Button(L("重設")) { m.exportFolder = "" } }
            }
            Text(L("檔名：原檔名-AniCanto.mp4；同名自動加編號。工作副本保留，方便續做或加入另一條音軌。")).font(.caption).foregroundStyle(.secondary)
        }.card().disabled(m.busy)
    }
}

/// Translate presentation text without changing the original backend diagnostics.
func localizedProgressDetail(_ text:String)->String {
    let selected=UserDefaults.standard.string(forKey:"studioLanguage") ?? "system"
    let english=selected == "en" || (selected == "system" && Locale.preferredLanguages.first?.hasPrefix("en") == true)
    guard english else {return text}
    if text.hasPrefix("Qwen TTS 已停用；新配音使用 ") {return text.replacingOccurrences(of:"Qwen TTS 已停用；新配音使用 ",with:"Qwen TTS retired; new dubbing uses ").replacingOccurrences(of:"。舊音軌及已下載模型檔案保留。",with:". Existing tracks and downloaded files are retained.")}
    let exact=L(text)
    if exact != text {return exact}
    if text.contains(" · ") {
        let translated=text.components(separatedBy:" · ").map(localizedProgressDetail).joined(separator:" · ")
        if translated != text {return translated}
    }
    let patterns:[(String,String)]=[
        (#"^(yue|en) · (\d+)–(\d+)/(\d+)；直接翻譯，跳過二次校稿。$"#,"$1 · $2–$3/$4: translating directly; editorial review skipped."),
        (#"^(\d+)–(\d+)/(\d+)；直接翻譯，跳過二次校稿。$"#,"$1–$2/$3: translating directly; editorial review skipped."),
        (#"^已生成 (\d+)/(\d+) 段.*配音。?$"#,"Generated $1/$2 dialogue takes."),
        (#"^(\d+) 段按原字幕時段或非對白尾音排除；冇中文字幕嘅全片使用日語辨識。$"#,"Excluded $1 segments outside source captions or non-dialogue tails. Films without Chinese captions use Japanese recognition."),
        (#"^硬件編碼未能使用，改用軟件編碼一次：(.*)$"#,"Hardware encoding unavailable; retrying once with software: $1"),
        (#"^([^·]+) · (yue|en)：(\d+) 段已補償細聲；(\d+) 段達到增益上限或有訊號提示。.*$"#,"$1 · $2: boosted $3 quiet takes; $4 gain-limit or signal warnings. Language and content are checked separately."),
        (#"^([^·]+) · (.*)：音量補償 ([+\-\d.]+) dB；有效聲音 ([\d.]+) 秒。.*$"#,"$1 · $2: reference gain $3 dB; $4 seconds of active audio. Background and speaker purity require audition."),
        (#"^建立角色畫面：([\d]+)/([\d]+) 段。$"#,"Collecting character frames: $1/$2 intervals."),
        (#"^全片角色相片比對：([\d]+)/([\d]+) 組；結果已保存。$"#,"Comparing episode portraits: $1/$2 pairs; results saved."),
        (#"^頭像品質核對：已檢查 ([\d]+) 張；只保留獨立、可辨識頭像。$"#,"Portrait quality: inspected $1 crops; retaining recognizable single heads."),
        (#"^畫面核對 (\d+)/(\d+) 段；已保存進度。$"#,"Visual review $1/$2 segments; progress saved."),
        (#"^已核對 (\d+)/(\d+) 段畫面；(\d+) 段角色配對有聲音與畫面共同支持。$"#,"Reviewed $1/$2 visual segments; $3 role assignments supported by audio and video."),
        (#"^已覆核 (\d+)/(\d+) 段遺漏候選。$"#,"Reviewed $1/$2 possible missing passages."),
        (#"^覆核原聲遺漏片段 ([\d.]+)–([\d.]+) 秒。$"#,"Checking possible missing source speech at $1–$2 seconds."),
        (#"^已辨識 ([\d.]+) / ([\d.]+) 秒日語。$"#,"Transcribed $1 / $2 seconds of Japanese speech."),
        (#"^已辨識 ([\d.]+) / ([\d.]+) 秒。$"#,"Transcribed $1 / $2 seconds."),
        (#"^音軌\s*(\d+)\s*/\s*(\d+)(.*)$"#,"Audio track $1 / $2$3"),
        (#"^分析原聲聲紋：第 (\d+)/(\d+) 句。$"#,"Analyzing source voices: line $1/$2."),
        (#"^.*第 (\d+) 至 (\d+) 句.*$"#,"Processing dialogue lines $1–$2."),
        (#"^.*校稿第 (\d+) 句（(\d+)/(\d+)）$"#,"Synthesizing dialogue line $1 ($2/$3).")
    ]
    for (pattern,replacement) in patterns {
        if let regex=try? NSRegularExpression(pattern:pattern),regex.firstMatch(in:text,range:NSRange(text.startIndex...,in:text)) != nil {
            return regex.stringByReplacingMatches(in:text,range:NSRange(text.startIndex...,in:text),withTemplate:replacement)
        }
    }
    // Technical errors remain verbatim for diagnosis, rather than guessing a translation.
    return text
}
