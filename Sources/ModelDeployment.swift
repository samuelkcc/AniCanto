import SwiftUI
import Metal

struct ModelOption:Decodable,Identifiable {
    let id:String,category:String,engine:String,title:String,repo:String,revision:String,precision:String
    let bytes:Int64
    let parameterB:Double
    let estimatedMemoryGB:Double
    let legacy:String?
    let retired:Bool?
    let files:[VoiceModelVariant.ModelFile]
    static let all:[Self] = {
        guard let p=Bundle.main.url(forResource:"model-options",withExtension:"json"),let d=try? Data(contentsOf:p) else{return []}
        return (try? JSONDecoder().decode([Self].self,from:d)) ?? []
    }()
    var relativeFolder:String {legacy ?? (category=="voice" ? "models/voice-variants/":"models/variants/")+id.replacingOccurrences(of:":",with:"-")}
    var deployable:Bool {retired != true && !files.isEmpty && bytes>0}
    func ready(_ root:URL)->Bool {deployable && files.allSatisfy {f in
        let p=root.appendingPathComponent(relativeFolder).appendingPathComponent(f.path)
        guard let n=(try? FileManager.default.attributesOfItem(atPath:p.path)[.size]) as? NSNumber else{return false}
        return f.size == nil || n.int64Value==f.size
    }}
    var memoryWarning:Bool {estimatedMemoryGB>ModelHardware.modelBudgetGB}
    var requirements:String {String(format:L("估計模型運行 %.1f GB；連系統預留約 %.1f GB"),estimatedMemoryGB,estimatedMemoryGB+ModelHardware.reserveGB)}
}
enum ModelHardware {
    static var memoryGB:Double {Double(ProcessInfo.processInfo.physicalMemory)/1_073_741_824}
    static var reserveGB:Double {max(8,memoryGB*0.15)}
    static var gpuBudgetGB:Double {MTLCreateSystemDefaultDevice().map{Double($0.recommendedMaxWorkingSetSize)/1_073_741_824} ?? memoryGB}
    static var modelBudgetGB:Double {min(memoryGB-reserveGB,gpuBudgetGB)}
    static func suggestion(category:String,engine:String?=nil,tier:Int,memoryGB:Double=ModelHardware.memoryGB)->ModelOption? {
        let rows=ModelOption.all.filter{$0.engine != "qwen-tts" && $0.deployable && $0.category==category && (engine==nil || $0.engine==engine)}
        let reserve=max(8,memoryGB*0.15)
        let gpuLimit=abs(memoryGB-ModelHardware.memoryGB)<0.01 ? ModelHardware.gpuBudgetGB:memoryGB*0.75
        let limit=min(memoryGB-reserve,gpuLimit)*(tier==0 ? 0.6:tier==1 ? 0.8:1)
        let cap:Double=tier==0 ? (category=="text" ? 4:category=="speech" ? 0.244:0.6):Double.greatestFiniteMagnitude
        let candidates=rows.filter{$0.parameterB<=cap && $0.estimatedMemoryGB<=limit && (tier==2 || $0.precision.contains("4bit") || $0.engine=="whisper")}
        return candidates.sorted{
            if $0.parameterB != $1.parameterB {return $0.parameterB>$1.parameterB}
            return tier==2 ? $0.bytes>$1.bytes:$0.bytes<$1.bytes
        }.first
    }
}
extension Engine {
    func selectedVariant(_ role:String,default fallback:String)->String {
        guard let d=try? Data(contentsOf:root.appendingPathComponent("model-selections.json")),let r=try? JSONSerialization.jsonObject(with:d) as? [String:String] else{return fallback}
        return r[role] ?? fallback
    }
    func selectVariant(_ role:String,_ id:String) throws {
        try selectVariants([role:id])
    }
    func selectVariants(_ changes:[String:String]) throws {
        modelSelectionLock.lock();defer {modelSelectionLock.unlock()}
        let p=root.appendingPathComponent("model-selections.json")
        var rows=((try? Data(contentsOf:p)).flatMap{try? JSONSerialization.jsonObject(with:$0) as? [String:String]}) ?? [:]
        rows.merge(changes) {_,new in new};try JSONSerialization.data(withJSONObject:rows,options:.prettyPrinted).write(to:p,options:.atomic)
    }
    func deployOption(_ option:ModelOption) throws {
        guard option.engine != "qwen-tts" else {throw AppFailure(message:L("Qwen TTS 已停用；請選擇 CosyVoice 或 GPT-SoVITS。"))}
        guard option.retired != true else {throw AppFailure(message:"This model is retired and cannot be downloaded.")}
        switch option.category {
        case "text":try pullModel(option.id)
        case "voice":try installDubbing(VoiceEngineChoice.all.first {$0.id==option.engine}?.kind ?? "cosy",variant:option.id)
        case "asr":try installDubbing("asr",variant:option.id)
        case "speech":try worker("download-speech",config:["storage":root.path,"speechModel":option.id])
        default:throw AppFailure(message:"未支援此模型部署方式。")
        }
    }
}
struct ModelRequirement:View {
    let option:ModelOption
    var body:some View {
        VStack(alignment:.leading,spacing:4) {
            Text(L("下載量")+" · "+ByteCountFormatter.string(fromByteCount:option.bytes,countStyle:.file)+" · "+option.precision).font(.system(size:14))
            Text(option.requirements).font(.caption).foregroundStyle(option.memoryWarning ? .orange:.secondary)
            Text(String(format:L("本機建議模型預算約 %.1f GB（綜合 RAM、系統預留同 Metal 建議上限）。"),ModelHardware.modelBudgetGB)).font(.system(size:13)).foregroundStyle(.secondary)
            if option.memoryWarning {Label(L("超出本機建議記憶體：可能大量使用 swap、變慢或無法載入。可改揀較小模型。"),systemImage:"exclamationmark.triangle.fill").font(.system(size:13)).foregroundStyle(.orange)}
            if option.category=="text" && option.parameterB<=2 {Text(L("低容量文字模型較容易漏意或誤譯，建議逐段批核台詞。")).font(.system(size:13)).foregroundStyle(.orange)}
            Text(L("Apple Silicon · macOS 14+ · 首次下載需要網絡。記憶體係估算，會受片長、上下文同其他程式影響。")).font(.system(size:13)).foregroundStyle(.secondary)
        }
    }
}
struct ModelChoicePicker:View {
    let title:String
    let rows:[ModelOption]
    @Binding var selection:String
    var body:some View {
        Picker(title,selection:$selection) {ForEach(rows.sorted{$0.bytes<$1.bytes}) {r in Text(r.title).tag(r.id)}}
        if let r=rows.first(where:{$0.id==selection}) {ModelRequirement(option:r)}
    }
}
final class ModelLibraryDraft:ObservableObject {
    @Published var selected=""
    @Published var installedOnly=false
}
final class DeploymentDraft:ObservableObject {
    @Published var loaded=false
    @Published var tier=1.0
    @Published var text=""
    @Published var cosy=""
    @Published var qwen=""
    @Published var speech=""
    @Published var asr=""
    @Published var includeQwen=false
    @Published var includeGPT=true
    @Published var includeSeparation=true
    @Published var includeSpeakers=true
    var snapshot:DeploymentPlan {DeploymentPlan(tier:tier,text:text,cosy:cosy,qwen:qwen,speech:speech,asr:asr,includeQwen:false,includeGPT:includeGPT,includeSeparation:includeSeparation,includeSpeakers:includeSpeakers)}
    func apply(_ p:DeploymentPlan) {tier=p.tier;text=p.text;cosy=p.cosy;qwen=p.qwen;speech=p.speech;asr=p.asr;includeQwen=false;includeGPT=p.includeGPT;includeSeparation=p.includeSeparation;includeSpeakers=p.includeSpeakers}
}
struct DeploymentPlan:Codable,Equatable {
    var tier:Double
    var text:String,cosy:String,qwen:String,speech:String,asr:String
    var includeQwen:Bool,includeGPT:Bool,includeSeparation:Bool,includeSpeakers:Bool
    func save(_ root:URL) throws {try JSONEncoder().encode(self).write(to:root.appendingPathComponent("deployment-plan.json"),options:.atomic)}
    static func load(_ root:URL)->Self? {(try? Data(contentsOf:root.appendingPathComponent("deployment-plan.json"))).flatMap {try? JSONDecoder().decode(Self.self,from:$0)}}
}
struct ModelLibrary:View {
    @ObservedObject var model:AppModel
    @StateObject private var draft=ModelLibraryDraft()
    let category:String
    let role:String


    var rows:[ModelOption] {ModelOption.all.filter{$0.engine != "qwen-tts" && $0.category==category && (!draft.installedOnly || $0.ready(model.engine.root))}}
    var body:some View {
        VStack(alignment:.leading,spacing:12) {
            Toggle(L("只顯示已下載版本"),isOn:$draft.installedOnly)
            ModelChoicePicker(title:"版本／大小／精度",rows:rows,selection:$draft.selected)
            if let row=ModelOption.all.first(where:{$0.id==draft.selected}) {
                Text(row.ready(model.engine.root) ? "已安裝":"未安裝").font(.caption)
                Text(row.repo).font(.caption2).textSelection(.enabled)
                HStack {
                    Button(row.ready(model.engine.root) ? "校驗／修復":"下載此版本") {let e=model.engine;model.task("部署 "+row.title) {try e.deployOption(row)}}
                    Button(L("使用此版本")) {
                        if category=="text" {model.selectedModel=row.id}
                        else {do {try model.engine.selectVariant(role,row.id);model.refresh()} catch {model.error=error.localizedDescription}}
                    }.disabled(!row.ready(model.engine.root))
                }
                Text(L("目前使用：")+(category=="text" ? model.selectedModel:model.engine.selectedVariant(role,default:role=="asr" ? "asr-1.7b-bf16":role=="referenceSpeech" ? "whisper-small":"whisper-large-v3"))).font(.caption)
            }
        }.onChange(of:draft.installedOnly) {_ in if !rows.contains(where:{$0.id==draft.selected}) {draft.selected=rows.first?.id ?? ""}}.onAppear {if draft.selected.isEmpty {draft.selected=category=="text" ? model.selectedModel:model.engine.selectedVariant(role,default:role=="asr" ? "asr-1.7b-bf16":role=="referenceSpeech" ? "whisper-small":"whisper-large-v3")}}.disabled(model.busy)
    }
}
struct DeploymentPresets:View {
    @ObservedObject var model:AppModel
    @StateObject private var draft=DeploymentDraft()










    var chosen:[ModelOption] {let ids=[draft.text,draft.cosy,draft.speech,draft.asr];return ids.compactMap{id in ModelOption.all.first{$0.id==id}}}
    var planMemory:Double {max(chosen.map(\.estimatedMemoryGB).max() ?? 0,draft.includeGPT ? 6:0,(draft.includeSeparation || draft.includeSpeakers) ? 5:0)+ModelHardware.reserveGB}
    var body:some View {
        VStack(alignment:.leading,spacing:20) {
            Text(L("按電腦容量建立部署方案")).font(.title2.bold())
            Text("\(Int(ModelHardware.memoryGB)) GB · \(MTLCreateSystemDefaultDevice()?.name ?? "CPU")").foregroundStyle(.secondary)
            Slider(value:Binding(get:{draft.tier},set:{draft.tier=$0;suggest()}),in:0...2,step:1)
            HStack {Text(L("節省記憶體"));Spacer();Text(L("平衡"));Spacer();Text(L("最高容量"))}
            LazyVGrid(columns:[GridItem(.adaptive(minimum:440),spacing:20)],alignment:.leading,spacing:20) {
                planChoice("文字翻譯",rows:ModelOption.all.filter{$0.category=="text"},binding:$draft.text)
                planChoice("CosyVoice",rows:ModelOption.all.filter{$0.engine=="cosyvoice3"},binding:$draft.cosy)
                planChoice("日語主辨識",rows:ModelOption.all.filter{$0.category=="speech"},binding:$draft.speech)
                planChoice("獨立覆聽",rows:ModelOption.all.filter{$0.category=="asr"},binding:$draft.asr)
                VStack(alignment:.leading,spacing:14) {
                    Toggle(String(format:L("部署 %@（模型約 %@；原生 48 kHz）"),VoiceEngineChoice.gpt.title,VoiceEngineChoice.gpt.download),isOn:$draft.includeGPT)
                    Text(model.gsvReady ? L("V4 模型已就緒；新配音使用 V4。") : L("V4 未就緒；請下載並部署。")).font(.caption).foregroundStyle(.secondary)
                    Toggle(L("背景分離 · Mel-Band RoFormer（約 913 MB）"),isOn:$draft.includeSeparation)
                    Toggle(L("角色配對 · WeSpeaker（約 27 MB）"),isOn:$draft.includeSpeakers)
                }.padding(18).background(StudioPalette.panel,in:RoundedRectangle(cornerRadius:6))
            }
            Divider()
            let bytes=chosen.filter{!$0.ready(model.engine.root)}.reduce(Int64(0)){$0+$1.bytes}
            HStack {Text(L("模型下載量")+" · "+ByteCountFormatter.string(fromByteCount:bytes,countStyle:.file));Spacer();Text(String(format:L("估計高峰記憶體 %.1f GB"),planMemory))}
            if planMemory>ModelHardware.memoryGB || chosen.contains(where:{$0.memoryWarning}) {Label(L("方案包含超出本機建議記憶體嘅模型，下載前請核對上方警告。"),systemImage:"exclamationmark.triangle.fill").foregroundStyle(.orange)}
            Text(L("方案下載量另計共用聲音編碼器及未部署嘅 GPT／背景處理元件。所有選擇可先修改；已下載版本會保留。")).font(.system(size:13)).foregroundStyle(.secondary)
            Button(L("下載並部署此方案")) {deploy()}.buttonStyle(StudioButtonStyle(prominent:true)).disabled(chosen.count < (draft.includeQwen ? 5:4) || model.busy)
        }.onAppear {if !draft.loaded {if let plan=DeploymentPlan.load(model.engine.root) {draft.apply(plan)} else {suggest();draft.text=model.selectedModel;draft.cosy=model.cosyModel;draft.qwen=model.qwenModel;draft.speech=model.selectedModelID("speech");draft.asr=model.selectedModelID("asr")};draft.loaded=true}}
            .onChange(of:draft.snapshot) {plan in if draft.loaded {do {try plan.save(model.engine.root)} catch {model.error=error.localizedDescription}}}.disabled(model.busy)
    }
    func planChoice(_ title:String,rows:[ModelOption],binding:Binding<String>)->some View {
        VStack(alignment:.leading,spacing:14) {
            Text(L(title)).font(.headline)
            Picker(L("模型版本"),selection:binding) {ForEach(rows.sorted{$0.bytes<$1.bytes}) {row in Text(row.title).tag(row.id)}}.labelsHidden()
            if let row=rows.first(where:{$0.id==binding.wrappedValue}) {
                Text(ByteCountFormatter.string(fromByteCount:row.bytes,countStyle:.file)+" · "+String(format:"%.1f GB RAM",row.estimatedMemoryGB)).font(.system(size:13)).foregroundStyle(row.memoryWarning ? .orange:.secondary)
            }
        }.padding(18).frame(maxWidth:.infinity,alignment:.leading).background(StudioPalette.panel,in:RoundedRectangle(cornerRadius:6))
    }
    func suggest() {
        let t=Int(draft.tier)
        draft.text=ModelHardware.suggestion(category:"text",tier:t)?.id ?? ""
        draft.cosy=ModelHardware.suggestion(category:"voice",engine:"cosyvoice3",tier:t)?.id ?? ""
        draft.qwen=ModelHardware.suggestion(category:"voice",engine:"qwen-tts",tier:t)?.id ?? ""
        draft.speech=ModelHardware.suggestion(category:"speech",tier:t)?.id ?? ""
        draft.asr=ModelHardware.suggestion(category:"asr",tier:t)?.id ?? ""
        draft.includeQwen=false
        draft.includeGPT=t>0 && 6+ModelHardware.reserveGB<=ModelHardware.memoryGB
    }
    func deploy() {
        do {try draft.snapshot.save(model.engine.root)} catch {model.error=error.localizedDescription;return}
        let rows=chosen,e=model.engine,gpt=draft.includeGPT,separation=draft.includeSeparation || draft.includeSpeakers,speakers=draft.includeSpeakers
        let ids=(draft.text,draft.cosy,draft.qwen,draft.speech,draft.asr),qwenEnabled=false
        model.task("部署已確認方案") {
            try e.installRuntime()
            for (index,row) in rows.enumerated() {e.event("部署方案","\(index+1)/\(rows.count) · \(row.title)");try e.deployOption(row)}
            if gpt {try e.installDubbing("gsv")}
            if separation {try e.installDubbing("separator")}
            if speakers {try e.installDubbing("speakers")}
            var choices=["text":ids.0,"cosyvoice3":ids.1,"speech":ids.3,"referenceSpeech":ids.3,"asr":ids.4]
            if qwenEnabled {choices["qwen-tts"]=ids.2}
            try e.selectVariants(choices)
            Task { @MainActor in model.selectedModel=ids.0;model.cosyModel=ids.1;if qwenEnabled {model.qwenModel=ids.2};model.ttsBackend="cosyvoice3";model.extraEngines=Set((qwenEnabled ? ["qwen-tts"]:[])+(gpt ? ["gpt-sovits"]:[]));model.separateBackground=separation;model.autoSpeakers=speakers;model.saveStudioPreset();model.refresh()}
            e.event("結果摘要","方案部署完成，已保留其他已下載版本。可以在各分類切換版本；轉片前請先試聽。",1)
        }
    }
}
