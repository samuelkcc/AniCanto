import SwiftUI

/// Global production choices only; source paths, project drafts and in-flight work stay separate.
struct StudioPreset:Codable {
    var schema=1
    var saved:Date
    var workflow:WorkflowValues
    var dubMode:String,subtitleSource:String,burnSubtitleMode:String,startTime:String
    var limit:Int
    var batchAutoSubtitles:Bool,continueOnError:Bool
    var productionMode:String?
    var aiAutoFix:Bool?
    var voxcpmDevice:String?
    var region:OCRRegion
    var qwenReferenceMode:String,gsvReferenceMode:String,gsvDevice:String
    @MainActor init(_ m:AppModel) {
        saved=Date();workflow=WorkflowValues(m);dubMode=m.dubMode;subtitleSource=m.subtitleSource;burnSubtitleMode=m.burnSubtitleMode;startTime=m.startTimeText;limit=m.limit
        productionMode=m.productionMode
        aiAutoFix=m.aiAutoFix
        voxcpmDevice=m.voxcpmDevice
        batchAutoSubtitles=m.batchAutoSubtitles;continueOnError=m.continueOnError;region=m.ocrRegion;qwenReferenceMode=m.qwenReferenceMode;gsvReferenceMode=m.gsvReferenceMode;gsvDevice=m.gsvDevice
    }
    @MainActor func apply(_ m:AppModel) {
        workflow.apply(to:m,editor:false);m.dubMode=dubMode;m.subtitleSource=subtitleSource;m.burnSubtitleMode=burnSubtitleMode;m.startTimeText=startTime;m.limit=limit
        if let productionMode {m.productionMode=productionMode}
        if let aiAutoFix {m.aiAutoFix=aiAutoFix}
        if let voxcpmDevice {m.voxcpmDevice=voxcpmDevice}
        m.batchAutoSubtitles=batchAutoSubtitles;m.continueOnError=continueOnError;m.ocrRegion=region;m.qwenReferenceMode=qwenReferenceMode;m.gsvReferenceMode=gsvReferenceMode;m.gsvDevice=gsvDevice
    }
}
extension AppModel {
    func persistModelChoice(_ role:String,_ id:String) {
        do {try engine.selectVariant(role,id)} catch {self.error=L("未能儲存模型選擇")+": "+error.localizedDescription}
    }
    func restoreStudioChoices() {
        let latestTranslationSource=UserDefaults.standard.string(forKey:"translationSource")
        let latestProductionMode=UserDefaults.standard.string(forKey:"productionMode")
        let latestDubMode=UserDefaults.standard.string(forKey:"dubMode")
        let shared=UserDefaults.standard.bool(forKey:"sharedWorkspaceVoiceSelection")
        let latestEngine=UserDefaults.standard.string(forKey:"ttsBackend")
        let latestExtras=UserDefaults.standard.stringArray(forKey:"workspaceExtraEngines")
        let latestOriginal=UserDefaults.standard.object(forKey:"workspaceIncludeOriginal") as? Bool
        let choices=((try? Data(contentsOf:engine.root.appendingPathComponent("model-selections.json"))).flatMap {try? JSONDecoder().decode([String:String].self,from:$0)}) ?? [:]
        let path=engine.root.appendingPathComponent("studio-preset.json")
        if FileManager.default.fileExists(atPath:path.path) {
            do {let preset=try JSONDecoder().decode(StudioPreset.self,from:Data(contentsOf:path));guard preset.schema==1 else {throw AppFailure(message:L("製作預設版本未支援"))};preset.apply(self);presetSavedAt=preset.saved}
            catch {self.error=L("未能載入製作預設")+": "+error.localizedDescription}
        }
        if let latestTranslationSource {translationSource=latestTranslationSource}
        if let latestProductionMode {productionMode=latestProductionMode}
        if let latestDubMode,["yue","en","both"].contains(latestDubMode) {dubMode=latestDubMode}
        if shared {
            if let latestEngine {ttsBackend=VoiceEngineChoice.active(latestEngine);reviewBackend=ttsBackend}
            if let latestExtras {extraEngines=Set(latestExtras)}
            if let latestOriginal {includeOriginal=latestOriginal}
        }
        // The latest explicit model selection takes precedence over a previously saved workflow.
        if let id=choices["text"] {selectedModel=id}
        if let id=choices["cosyvoice3"] {cosyModel=id}
        if let id=choices["voxcpm2"] {voxcpmModel=id}
        if let id=choices["wsyue"] {wsyueModel=id}
        if let id=choices["drama3"] {drama3Model=id}
        if let id=choices["qwen-tts"] {qwenModel=id}
        ttsBackend=VoiceEngineChoice.active(ttsBackend);reviewBackend=VoiceEngineChoice.active(reviewBackend);extraEngines.remove("qwen-tts")
        UserDefaults.standard.set(ttsBackend,forKey:"ttsBackend")
        do {try engine.selectVariants(["text":selectedModel,"cosyvoice3":cosyModel])} catch {self.error=L("未能儲存模型選擇")+": "+error.localizedDescription}
    }
    func saveStudioPreset() {
        do {let preset=StudioPreset(self);try JSONEncoder().encode(preset).write(to:engine.root.appendingPathComponent("studio-preset.json"),options:.atomic);presetSavedAt=preset.saved}
        catch {self.error=L("未能儲存製作預設")+": "+error.localizedDescription}
    }
    func selectedModelID(_ role:String)->String {
        switch role {case "text":return selectedModel;case "visual":return engine.selectedVariant(role,default:selectedModel.hasPrefix("mlx:") ? selectedModel:Engine.mlxModel);case "cosyvoice3":return cosyModel;case "voxcpm2":return voxcpmModel;case "wsyue":return wsyueModel;case "drama3":return drama3Model;case "qwen-tts":return qwenModel;default:return engine.selectedVariant(role,default:role=="asr" ? "asr-1.7b-bf16":role=="referenceSpeech" ? "whisper-small":"whisper-large-v3")}
    }
    func useModel(_ role:String,_ id:String) {
        guard role != "qwen-tts" else {return}
        switch role {case "text":selectedModel=id;case "cosyvoice3":cosyModel=id;case "voxcpm2":voxcpmModel=id;case "wsyue":wsyueModel=id;case "drama3":drama3Model=id;case "qwen-tts":qwenModel=id;default:persistModelChoice(role,id)}
        refresh();modelSelectionRevision+=1
    }
    func rolesUsing(_ id:String)->[String] {ModelUsageRole.all.filter {selectedModelID($0.id)==id}.map(\.title)}
    func modelRemovalReason(_ row:ModelOption)->String? {
        if busy {return L("處理期間暫時不能移除模型")}
        if !FileManager.default.fileExists(atPath:engine.root.appendingPathComponent(row.relativeFolder).path) {return L("本機未有此模型檔案")}
        return nil
    }
    func trashModel(_ row:ModelOption) {
        guard modelRemovalReason(row)==nil else{return}
        let roles=ModelUsageRole.all.filter {selectedModelID($0.id)==row.id}
        let alert=NSAlert();alert.messageText=L("移到垃圾桶")+" · "+row.title
        alert.informativeText=roles.isEmpty ? L("可以重新下載；影片、字幕及其他模型會保留。") : L("此模型正在選用。移除後需要重新選擇模型，程式不會自動改用其他版本。")
        alert.addButton(withTitle:L("移到垃圾桶"));alert.addButton(withTitle:L("取消"))
        guard alert.runModal() == .alertFirstButtonReturn else{return}
        do {try engine.trashModelFiles(row);for role in roles {useModel(role.id,"")};refresh();modelSelectionRevision+=1}
        catch {self.error=error.localizedDescription}
    }
}
struct ModelUsageRole:Identifiable {
    let id:String,title:String,category:String
    static let all=[Self(id:"text",title:"文字翻譯",category:"text"),Self(id:"visual",title:"畫面角色分析",category:"text"),Self(id:"cosyvoice3",title:"CosyVoice",category:"voice"),Self(id:"voxcpm2",title:"VoxCPM2",category:"voice"),Self(id:"wsyue",title:"WenetSpeech-Yue",category:"voice"),Self(id:"drama3",title:"Drama 3",category:"voice"),Self(id:"speech",title:"日語主辨識",category:"speech"),Self(id:"referenceSpeech",title:"角色參考辨識",category:"speech"),Self(id:"asr",title:"獨立覆聽",category:"asr")]
    func matches(_ row:ModelOption)->Bool {row.category==category && (category != "voice" || row.engine==id)}
}
struct ActiveModelSettings:View {
    @ObservedObject var model:AppModel
    var body:some View {
        VStack(alignment:.leading,spacing:18) {
            Text(L("模型選用")).font(.title2.bold())
            Text(L("只列出已下載版本；選擇會立即儲存。未下載或已移除的版本會清楚標示。")).foregroundStyle(.secondary)
            ForEach(ModelUsageRole.all) {role in
                let current=model.selectedModelID(role.id)
                let rows=ModelOption.all.filter {role.matches($0) && $0.ready(model.engine.root)}
                VStack(alignment:.leading,spacing:5) {
                    Picker(L(role.title),selection:Binding(get:{model.selectedModelID(role.id)},set:{model.useModel(role.id,$0)})) {
                        Text(L("未選用")).tag("")
                        if !current.isEmpty && !rows.contains(where:{$0.id==current}) {Text(current+" · "+L("未下載")).tag(current)}
                        ForEach(rows) {row in Text(row.title+" · "+L("已下載")).tag(row.id)}
                    }
                    if current.isEmpty || !rows.contains(where:{$0.id==current}) {Text(L("請先下載並選用所需版本。")).font(.caption).foregroundStyle(.orange)}
                }
            }
            Button(L("開啟模型中心")) {model.section = .environment}
        }.disabled(model.busy)
    }
}
extension Engine {
    func trashModelFiles(_ row:ModelOption) throws {
        let folder=root.appendingPathComponent(row.relativeFolder).standardizedFileURL
        guard row.relativeFolder.hasPrefix("models/"),folder.path.hasPrefix(root.standardizedFileURL.path+"/models/"),folder.resolvingSymlinksInPath()==folder else {throw AppFailure(message:L("模型路徑無效"))}
        if row.category=="text" {releaseTextModels()}
        try FileManager.default.trashItem(at:folder,resultingItemURL:nil)
        for path in ["model-ready/"+row.id.replacingOccurrences(of:":",with:"-")+".json","voice-model-ready/"+row.id+".json"] {
            let marker=root.appendingPathComponent(path);if FileManager.default.fileExists(atPath:marker.path) {try FileManager.default.removeItem(at:marker)}
        }
    }
}
