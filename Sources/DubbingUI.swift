import SwiftUI
import AVKit
import UniformTypeIdentifiers

struct EngineVoiceReference:Codable,Equatable {
    var reference=""
    var promptText=""
    var enabled=false
    var language:String?=nil
    var range:[Double]?=nil
    init(reference:String="",promptText:String="",enabled:Bool=false,language:String?=nil,range:[Double]?=nil) {
        self.reference=reference;self.promptText=promptText;self.enabled=enabled;self.language=language;self.range=range
    }
    private enum CodingKeys:String,CodingKey {case reference,promptText,enabled,language,range}
    init(from decoder:Decoder) throws {
        let values=try decoder.container(keyedBy:CodingKeys.self)
        reference=try values.decodeIfPresent(String.self,forKey:.reference) ?? ""
        promptText=try values.decodeIfPresent(String.self,forKey:.promptText) ?? ""
        // Automatically sampled alternatives have no manual-enable setting.
        enabled=try values.decodeIfPresent(Bool.self,forKey:.enabled) ?? false
        language=try values.decodeIfPresent(String.self,forKey:.language)
        range=try values.decodeIfPresent([Double].self,forKey:.range)
    }
    var ready:Bool {!promptText.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty && FileManager.default.fileExists(atPath:reference)}
}
struct VoiceProfile: Codable, Identifiable, Equatable {
    var id = UUID().uuidString
    var name: String
    var reference = ""
    var promptText = ""
    var language = "ja"
    var engineReferences:[String:EngineVoiceReference]?=nil
    var naturalVoices:[String:String]?=nil
    var shortReference:Bool?=nil
    var mixedReference:Bool?=nil
    var referenceRanges:[[Double]]?=nil
    var transcriptSource:String?=nil
    var originalReference:String?=nil
    var avatar:String?=nil
    var visualId:String?=nil
    var appearance:String?=nil
    var referenceCandidates:[EngineVoiceReference]?=nil
    var sourceFrame:String?=nil
    var avatarTime:Double?=nil
    var portraits:[RolePortrait]?=nil
    var referenceQuality:RoleReferenceQuality?=nil
    var identityStatus:String?=nil
    var identityLabel:String {
        switch identityStatus {
        case "independent":return L("本句獨立原聲參考")
        case "audiovisual":return L("聲音與畫面支持")
        case "acoustic":return L("只按聲音配對")
        case "provisional":return L("待確認聲線")
        default:return L("身份未確認")
        }
    }
    func referenceFor(_ engine:String,_ target:String)->String {let own=engineReferences?[engine+":"+target];return own?.enabled==true ? own!.reference:reference}
    var ready: Bool { !promptText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && FileManager.default.fileExists(atPath: reference) }
}
struct RolePortrait:Codable,Identifiable,Equatable {
    var avatar:String
    var sourceFrame:String
    var time:Double
    var id:String {avatar}
}
struct RoleReferenceQuality:Codable,Equatable {
    var score:Double?
    var activeFraction:Double?
    var noiseFloorDB:Double?
    var warnings:[String]?
}
struct VoiceTiming: Decodable {
    var start: Double
    var end: Double
    var seconds: Double
    var slot: Double
    var needsReview: Bool
    var sourceEndError: Double?
    var requiresTimingReview: Bool?
    var phraseAligned: Bool?
    var audio: String
}

extension AppModel {
    var currentVoiceIndices: [Int] {
        let assigned = Set(scriptCues.compactMap(\.speakerId))
        return voiceProfiles.indices.filter { assigned.contains(voiceProfiles[$0].id) }
    }
    var reviewVoices:[VoiceProfile] {reviewVoiceProfiles+voiceProfiles.filter {p in !reviewVoiceProfiles.contains {$0.id==p.id}}}
    var currentVoiceProfiles:[VoiceProfile] {let assigned=Set(scriptCues.compactMap(\.speakerId));return reviewVoices.filter {assigned.contains($0.id)}}
    var usesCloning: Bool { VoiceEngineChoice.requiresReference(ttsBackend) }
    var selectedTTSReady: Bool { selectedEngines.allSatisfy { engineReady($0) } }
    var profilesJSON: Any { (try? JSONSerialization.jsonObject(with: JSONEncoder().encode(voiceProfiles))) ?? [] }
    var effectiveRoleAnalysisMode:String {RoleAnalysisPolicy.mode(selected:roleAnalysisMode,visualEnabled:visualRoleAnalysisEnabled,interfaceMode:UserDefaults.standard.string(forKey:"studioInterfaceMode") ?? "simple")}
    var dubbingSettings: [String:Any] {
        ["fallbackToRoleVoice":true,"requireCompleteDubbing":true,"cantoneseLocale":"yue-HK","voiceStyleMode":voiceStyleMode,"allowCrossEngineRepair":allowCrossEngineRepair,"roleAnalysisMode":effectiveRoleAnalysisMode,"visualRoleAnalysisEnabled":effectiveRoleAnalysisMode=="audiovisual","visualModel":selectedModelID("visual"),"continueOnError":continueOnError,"independentReferences":true,"qwenModel":qwenModel,"qwenReferenceMode":qwenReferenceMode,"gsvReferenceMode":gsvReferenceMode,"cosyModel":cosyModel,"targetLanguage":dubMode == "en" ? "en":"yue","ttsBackend":ttsBackend, "voiceProfiles":profilesJSON, "defaultSpeaker":voiceProfiles.count == 1 ? voiceProfiles[0].id : "", "gsvDevice":gsvDevice, "separateBackground":separateBackground || (autoSpeakers && usesCloning), "backgroundGain":backgroundGain,"backgroundDucking":backgroundDucking, "autoSpeakers":autoSpeakers && usesCloning, "autoSkipOP":autoSkipOP,"translateOPED":translateOPED]
    }
    func persistProfiles() {
        do { try JSONEncoder().encode(voiceProfiles).write(to: engine.root.appendingPathComponent("voice-profiles.json"), options: .atomic) }
        catch { self.error = "儲存角色聲線失敗：\(error.localizedDescription)"; detail = self.error! }
    }
    func loadProfiles() {
        let url = engine.root.appendingPathComponent("voice-profiles.json")
        if let data = try? Data(contentsOf: url), let saved = try? JSONDecoder().decode([VoiceProfile].self, from: data) { voiceProfiles = saved }
    }
    func loadTimings() {
        timingRows = []
        guard let reviewURL else { return }
        let url = reviewURL.deletingLastPathComponent().appendingPathComponent("timing.json")
        if let data = try? Data(contentsOf: url), let rows = try? JSONDecoder().decode([VoiceTiming].self, from: data) { timingRows = rows }
    }
    func validateDubbing() -> Bool {
        var message: String?
        if !exportFolder.isEmpty && (!FileManager.default.fileExists(atPath:exportFolder) || !FileManager.default.isWritableFile(atPath:exportFolder)) { message = "輸出資料夾唔存在或冇寫入權限，請重新選擇。" }
        if needsEnglishSubtitles && !models.contains(selectedModel) { message = "英文字幕需要先下載所選文字模型。" }
        if separateBackground && !separatorReady { message = "請先喺環境頁下載背景分離模型。" }
        if usesCloning {
            if !selectedTTSReady { message = "請先喺環境頁部署所選配音引擎。" }
            else if productionMode != "fast" && !autoSpeakers && (voiceProfiles.isEmpty || !voiceProfiles.contains(where: { $0.ready })) { message = "請加入角色聲線，或者開啟自動配對角色。" }
            else if productionMode != "fast" && !autoSpeakers && autoApprove && voiceProfiles.count > 1 { message = "手動角色模式請先校稿，或者開啟自動配對角色。" }
        }
        if let message { error = message; detail = message; stage = "需要設定"; return false }
        return true
    }
    func audition(_ url: URL, label: String) {
        player.pause(); audioPlayer.pause()
        audioPlayer.replaceCurrentItem(with: AVPlayerItem(url: url)); audioPreviewLabel = label; audioPlayer.play()
    }
    func baseAudioConfig() -> [String:Any] {
        ["storage":engine.root.path,"ffmpeg":engine.ffmpeg.path,"ffprobe":engine.ffprobe.path]
    }
    func previewSeparation() {
        guard let video, let start = startSeconds, start < sourceDuration else { error = "請先選擇影片同有效開始時間。"; detail = error!; return }
        var cfg = baseAudioConfig()
        cfg.merge(["video":video.path,"startOffset":start,"duration":min(sourceDuration-start,limit == 0 ? sourceDuration-start : Double(limit))]) { _,new in new }
        let e=engine, data=try! JSONSerialization.data(withJSONObject:cfg)
        player.pause(); audioPlayer.pause()
        task("分離背景") { try e.worker("preview-separation", config: try JSONSerialization.jsonObject(with:data) as! [String:Any]) }
    }
    func extractReference(_ id: String) {
        guard let video else { error = "請先喺工作區匯入影片。"; detail = error!; return }
        let parts=referenceStart.split(separator:":"); var start=0.0
        for part in parts { guard let n=Double(part), n.isFinite, n>=0 else { error="參考開始時間無效。";detail=error!;return }; start=start*60+n }
        guard !parts.isEmpty, start+referenceSeconds <= sourceDuration else { error="參考片段超出影片範圍。";detail=error!;return }
        var cfg=baseAudioConfig()
        cfg.merge(["video":video.path,"startOffset":start,"referenceDuration":referenceSeconds,"profileId":id]) { _,new in new }
        let e=engine, data=try! JSONSerialization.data(withJSONObject:cfg)
        player.pause();audioPlayer.pause()
        task("抽取角色參考") { try e.worker("prepare-reference",config:try JSONSerialization.jsonObject(with:data) as! [String:Any]) }
    }
    func importReference(_ id: String) {
        let panel=NSOpenPanel();panel.allowedContentTypes=[.wav];panel.allowsMultipleSelection=false
        guard panel.runModal() == .OK, let url=panel.url else { return }
        var cfg=baseAudioConfig();cfg.merge(["referenceInput":url.path,"profileId":id]) { _,new in new }
        let e=engine,data=try! JSONSerialization.data(withJSONObject:cfg)
        task("匯入角色參考") { try e.worker("import-reference",config:try JSONSerialization.jsonObject(with:data) as! [String:Any]) }
    }
    func shortenCue(_ index: Int) {
        guard scriptCues.indices.contains(index) else { return }
        let cue=scriptCues[index]
        var cfg: [String:Any] = ["port":engine.port,"model":selectedModel,"index":index,"cue":try! JSONSerialization.jsonObject(with:JSONEncoder().encode(cue))]
        cfg["measuredSeconds"] = timingRows.first(where: { $0.start == cue.start && $0.end == cue.end })?.seconds
        let e=engine,data=try! JSONSerialization.data(withJSONObject:cfg)
        task("按時長改短台詞") { try e.worker("shorten-cue",config:try JSONSerialization.jsonObject(with:data) as! [String:Any]) }
    }
    func previewVoice(_ id: String, compare: Bool = false) {
        var cfg=baseAudioConfig();cfg.merge(dubbingSettings) { _,new in new };cfg["defaultSpeaker"]=id;cfg["previewText"]=auditionText;cfg["compareVoices"]=compare;cfg["targetLanguage"]=voicePreviewLanguage
        if compare { comparisonGSV = nil; comparisonCosy = nil }
        let e=engine,data=try! JSONSerialization.data(withJSONObject:cfg)
        player.pause();audioPlayer.pause()
        task("角色配音試聽") { try e.worker("preview-voice",config:try JSONSerialization.jsonObject(with:data) as! [String:Any]) }
    }
}

extension ContentView {
    var backgroundButtons: some View {
        HStack {
            if let url=m.backgroundAudio { Button(L("聽背景")) { m.audition(url,label:"分離後背景音樂／音效") } }
            if let url=m.dialogueAudio { Button(L("聽分離對白")) { m.audition(url,label:"分離後日語對白") } }
            if !m.audioPreviewLabel.isEmpty { Button(L("停止試聽")) { m.audioPlayer.pause() } }
        }
    }
    var voicesView: some View {
        VStack(alignment:.leading,spacing:18) {
            Text(L("自動角色配對")).font(.title2.bold())
            Text(L("分析影片時會自動分辨聲線、抽取原聲參考，再配對每句對白。呢頁只係查看同試聽結果，正常轉換毋須手動設定。")).foregroundStyle(.secondary)
            if m.currentVoiceProfiles.isEmpty {
                VStack(alignment:.leading,spacing:12) {
                    Label(L("未有目前影片嘅配對結果"),systemImage:"person.wave.2").font(.headline)
                    Text(L("喺工作區匯入影片並開始翻譯，角色會自動出現。已有草稿可以喺「輸出與紀錄」繼續校稿。")).foregroundStyle(.secondary)
                    HStack {
                        Button(L("去轉換工作區")) { m.section = .studio }
                        Button(L("開啟已有草稿")) { m.section = .history }
                        if m.reviewURL != nil && !m.scriptCues.isEmpty {
                            Button(L("自動配對呢份稿")) { m.autoAssignReview() }.disabled(m.busy)
                        }
                    }
                }.card()
            } else {
                HStack {
                    VStack(alignment:.leading,spacing:6) {
                        Text(m.scriptVideo).font(.headline)
                        Text("\(m.currentVoiceProfiles.count) 個聲線分組 · \(m.scriptCues.filter { $0.included && $0.speakerId != nil }.count) 句已配對對白").foregroundStyle(.secondary)
                    }
                    Spacer()
                    Button(L("返回校稿")) { m.section = .script }
                }.card()
                ForEach(m.currentVoiceProfiles) { profile in matchedVoiceCard(profile) }
                Text(L("角色名稱只係聲音分組標籤。短答、重疊講話或角色變聲可能配錯；有需要先展開「進階修正」。")).font(.caption).foregroundStyle(.secondary)
            }
            if !m.audioPreviewLabel.isEmpty {
                HStack { Text("試聽：\(m.audioPreviewLabel)");Spacer();Button(L("停止試聽")) { m.audioPlayer.pause() } }.card()
            }
            DisclosureGroup(L("進階設定：手動聲線及引擎比較")) {
                manualVoicesView.padding(.top,12)
            }.card()
        }
    }
    func matchedVoiceCard(_ profile:VoiceProfile) -> some View {
        let cues = m.scriptCues.filter { $0.included && $0.speakerId == profile.id }
        let warningCount = cues.filter { !($0.speakerNote ?? "").isEmpty }.count
        let timing = m.timingRows.first { row in cues.contains { $0.start == row.start && $0.end == row.end } }
        return VStack(alignment:.leading,spacing:12) {
            HStack {
                Label(profile.name,systemImage:"waveform").font(.headline)
                Spacer()
                Text("\(cues.count) 句對白").foregroundStyle(.secondary)
            }
            if warningCount > 0 { Text("\(warningCount) 句聲音較短或配對未確定，可喺校稿頁對照片段。").font(.caption).foregroundStyle(.orange) }
            HStack {
                Button(L("聽角色原聲")) { m.audition(URL(fileURLWithPath:profile.reference),label:profile.name+" 原聲") }.disabled(!FileManager.default.fileExists(atPath:profile.reference))
                if let timing {
                    Button(L("聽已生成配音")) { m.audition(URL(fileURLWithPath:timing.audio),label:profile.name+" 上次配音") }
                } else { Text(L("批准配音後可喺度試聽結果")).font(.caption).foregroundStyle(.secondary) }
                if let cue = cues.first {
                    Button(L("睇對應片段")) { m.section = .script; m.seekCue(cue,play:true) }
                }
            }.disabled(m.busy)
            if let index=m.voiceProfiles.firstIndex(where:{$0.id==profile.id}) {DisclosureGroup(L("進階修正")) {voiceCard(index).padding(.top,8)}}
        }.card()
    }
    var manualVoicesView: some View {
        VStack(alignment:.leading,spacing:18) {
            Text(L("只喺要換聲線、修正配錯或比較引擎時使用。儲存過嘅其他聲線唔會自動套落目前影片。")).foregroundStyle(.secondary)
            Toggle(L("新轉換根據原聲自動配對全部角色"), isOn: $m.autoSpeakers).disabled(m.busy)
            Toggle(L("校稿角色選單顯示其他已保存聲線（手動換聲用）"),isOn:$m.showSavedVoiceChoices).disabled(m.busy)
            if m.reviewURL != nil { Button(L("重新自動配對目前稿件")) { m.autoAssignReview() }.disabled(m.busy) }
            if !m.selectedTTSReady || !m.separatorReady { Button(L("到環境頁下載模型")) { m.section = .environment } }
            if m.video != nil {
                AspectPlayerFrame(aspect:m.videoAspect,maxHeight:m.largePreview ? 460 : 260) { NativePlayer(player:m.player) }
                HStack {
                    TextField(L("參考開始時間（分:秒）"),text:$m.referenceStart).textFieldStyle(.roundedBorder).frame(width:180)
                    Button(L("用原片目前位置")) { m.referenceStart=String(format:"%02d:%05.2f",Int(m.playbackSeconds)/60,m.playbackSeconds.truncatingRemainder(dividingBy:60)) }.disabled(m.showingOutput)
                    Stepper("\(Int(m.referenceSeconds)) 秒",value:$m.referenceSeconds,in:3...10,step:1)
                }.disabled(m.busy)
            }
            Picker(L("配音引擎"), selection: $m.ttsBackend) {
                ForEach(VoiceEngineChoice.all) {Text($0.title).tag($0.id)}
            }.disabled(m.busy)
            if m.ttsBackend.hasPrefix("gpt-sovits") {
            Picker(L("配音裝置"),selection:$m.gsvDevice) { Text("Apple Silicon GPU · MPS").tag("mps");Text(L("CPU · 相容模式，較慢")).tag("cpu") }.frame(width:400).disabled(m.busy)
            } else { Text(L("CosyVoice 3 使用 Apple Silicon GPU · MLX，全本機生成。")).font(.caption).foregroundStyle(.secondary) }
            if let a = m.comparisonGSV, let b = m.comparisonCosy {
                HStack {
                    Text(L("同稿比較"))
                    Button(L("聽 GPT-SoVITS")) { m.audition(a, label: "GPT-SoVITS 比較試聽") }
                    Button(L("聽 CosyVoice 3")) { m.audition(b, label: "CosyVoice 3 比較試聽") }
                    Button(L("停止")) { m.audioPlayer.pause() }
                }.card()
            }
            Picker(L("試聽語言"),selection:$m.voicePreviewLanguage) {Text(L("廣東話")).tag("yue");Text(L("英文")).tag("en")}.pickerStyle(.segmented)
            TextField(L("試聽台詞"),text:$m.auditionText,axis:.vertical).textFieldStyle(.roundedBorder).disabled(m.busy)
            Button(L("加入角色")) { m.voiceProfiles.append(VoiceProfile(name:"角色 \(m.voiceProfiles.count+1)")) }.disabled(m.busy)
            DisclosureGroup(L("所有已保存聲線（包括其他影片／測試）")) {
                ForEach(m.voiceProfiles.indices,id:\.self) { index in voiceCard(index) }
            }
            Text(L("參考日語原文唔係中文字幕翻譯。抽取時如已部署 Whisper，會自動填入辨識草稿，仍要核對。聲線相似度、情緒同廣東話發音需要試聽確認。")).font(.caption).foregroundStyle(.secondary)
        }
    }
    func voiceCard(_ index: Int) -> some View {
        VStack(alignment:.leading,spacing:12) {
            TextField(L("角色名稱"),text:$m.voiceProfiles[index].name).textFieldStyle(.roundedBorder)
            HStack {
                Button(L("由影片抽取並分離")) { m.extractReference(m.voiceProfiles[index].id) }.disabled(m.video == nil || !m.separatorReady)
                Button(L("匯入乾淨 WAV")) { m.importReference(m.voiceProfiles[index].id) }
                if !m.voiceProfiles[index].reference.isEmpty { Button(L("聽參考原聲")) { m.audition(URL(fileURLWithPath:m.voiceProfiles[index].reference),label:m.voiceProfiles[index].name+" 參考原聲") } }
            }
            Text(m.voiceProfiles[index].reference.isEmpty ? "未設定參考聲音" : URL(fileURLWithPath:m.voiceProfiles[index].reference).lastPathComponent).font(.caption).foregroundStyle(.secondary)
            Picker(L("參考錄音語言"),selection:$m.voiceProfiles[index].language) { Text(L("日語")).tag("ja");Text(L("廣東話")).tag("yue");Text(L("英文")).tag("en") }.frame(width:300)
            TextField(L("參考錄音實際講嘅原文"),text:$m.voiceProfiles[index].promptText,axis:.vertical).textFieldStyle(.roundedBorder).lineLimit(2...5)
            Button(L("生成呢個角色嘅試聽")) { m.previewVoice(m.voiceProfiles[index].id) }.disabled(!m.selectedTTSReady || !m.voiceProfiles[index].ready || m.auditionText.isEmpty)
            Button(L("兩個引擎同稿比較")) { m.previewVoice(m.voiceProfiles[index].id, compare: true) }.disabled(!m.gsvReady || !m.cosyReady || !m.voiceProfiles[index].ready || m.auditionText.isEmpty)
        }.card().disabled(m.busy)
    }
}
