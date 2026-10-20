import SwiftUI

struct VoiceModelVariant: Decodable, Identifiable {
    struct ModelFile:Decodable {let path:String;let size:Int64?}
    let files:[ModelFile]
    let id: String
    let engine: String
    let title: String
    let repo: String
    let revision: String
    let bytes: Int64
    let legacy: String?
    static let all: [Self] = {
        guard let url=Bundle.main.url(forResource:"voice-models",withExtension:"json"),let data=try? Data(contentsOf:url) else{return []}
        return (try? JSONDecoder().decode([Self].self,from:data)) ?? []
    }()
    func folder(_ root:URL)->URL {root.appendingPathComponent(legacy ?? "models/voice-variants/\(id)")}
}
extension AppModel {
    func voiceVariantReady(_ variant:VoiceModelVariant)->Bool {
        let fm=FileManager.default
        guard !variant.files.isEmpty else{return false}
        guard variant.files.allSatisfy({file in
            let path=variant.folder(engine.root).appendingPathComponent(file.path)
            guard let attributes=try? fm.attributesOfItem(atPath:path.path),let size=attributes[.size] as? NSNumber else{return false}
            return file.size == nil || size.int64Value == file.size
        }) else{return false}
        let marker=engine.root.appendingPathComponent("voice-model-ready/\(variant.id).json")
        if let data=try? Data(contentsOf:marker),let row=try? JSONSerialization.jsonObject(with:data) as? [String:Any],row["revision"] as? String==variant.revision{return true}
        if variant.id=="qwen-0.6b-4bit" {return fm.fileExists(atPath:engine.root.appendingPathComponent("qwen-ready.json").path)}
        if variant.id=="cosy-0.5b-4bit" {return fm.fileExists(atPath:engine.root.appendingPathComponent("cosy-ready.json").path)}
        return false
    }
    func voiceModelTitle(_ id:String)->String {
        let selected=voiceModelSelection(id)
        return id.hasPrefix("gpt-sovits") ? ((id=="gpt-sovits-v2" ? "V2 Pro Plus":(VoiceEngineChoice.all.first {$0.id==id}?.gsvVersion ?? "v4").uppercased())+" · 原生 "+(id=="gpt-sovits-v2" ? "32":id=="gpt-sovits-v3" ? "24":"48")+" kHz") : VoiceModelVariant.all.first(where:{$0.id==selected})?.title ?? selected
    }
    func removeVoiceVariant(_ row:VoiceModelVariant) {
        if let option=ModelOption.all.first(where:{$0.id==row.id}) {trashModel(option);return}
        guard !busy else{return}
        do {
            try FileManager.default.trashItem(at:row.folder(engine.root),resultingItemURL:nil)
            let marker=engine.root.appendingPathComponent("voice-model-ready/\(row.id).json")
            if FileManager.default.fileExists(atPath:marker.path) {try FileManager.default.removeItem(at:marker)}
            refresh()
        } catch {self.error=error.localizedDescription}
    }
    var dubLanguages:[String] {dubMode=="both" ? ["yue","en"] : [dubMode]}
}
final class VoiceBrowserSelection:ObservableObject { @Published var id="" }
struct VoiceModelLibrary:View {
    @ObservedObject var model:AppModel
    @StateObject private var browser=VoiceBrowserSelection()
    var chosen:String {browser.id.isEmpty ? model.voiceModelSelection(model.modelLibraryEngine):browser.id}
    var body:some View {
        VStack(alignment:.leading,spacing:16) {
            Picker(L("配音引擎"),selection:$model.modelLibraryEngine) {ForEach(VoiceEngineChoice.all) {Text($0.title).tag($0.id)}}.pickerStyle(.menu)
            Text(L("下載大小係模型檔案，唔等於運行時記憶體。大模型／高精度通常需要更多記憶體同時間。所選版本會保存；處理時如需要替代版本，結果會列明。")).font(.caption).foregroundStyle(.secondary)
            if model.modelLibraryEngine.hasPrefix("gpt-sovits") {
                let version=VoiceEngineChoice.all.first {$0.id==model.modelLibraryEngine}?.gsvVersion ?? "v4"
                let rate=version=="v2ProPlus" ? "32":"48"
                VStack(alignment:.leading,spacing:10) {
                    Text("GPT-SoVITS "+gsvModelTitle(version)).font(.headline)
                    Text("原生 "+rate+" kHz · "+(model.engineReady(model.modelLibraryEngine) ? "已部署":"未部署"))
                    Text(L("Apple Silicon · macOS 14+ · 建議至少 16 GB 系統記憶體；實際用量視句長及裝置而定。")).font(.caption).foregroundStyle(.secondary)
                    Text(L("V2 Pro Plus／V4 獨立生成及保留音軌；兩款共用 GPT 語義模型，聲音合成模型不同。參考錄音品質仍影響結果。")).font(.caption).foregroundStyle(.secondary)
                    if 6+ModelHardware.reserveGB>ModelHardware.memoryGB {Label(L("超出本機建議記憶體：可能變慢或無法載入。"),systemImage:"exclamationmark.triangle.fill").foregroundStyle(.orange)}
                    
                    Text(L("GPT-SoVITS 獨立讀取角色原聲及逐字原文；參考音效殘留同跨語言效果需要覆聽。")).font(.caption).foregroundStyle(.secondary)
                    Text(L("自動拼接參考會改用同角色連續原聲並核對原文。字詞／語言通過，仍需試聽廣東話聲調。")).font(.caption).foregroundStyle(.secondary)
                    Text(L("此 GPT 模型隨 App 提供，不能在模型中心獨立移除；可取消選用此引擎。" )).font(.caption).foregroundStyle(.secondary)
                    Button("下載／修復 "+gsvModelTitle(version)) {let e=model.engine;model.task("部署 GPT-SoVITS "+gsvModelTitle(version)) {try e.installDubbing("gsv",variant:version)}}
                }.card()
            } else {
                Picker(L("模型大小／精度"),selection:Binding(get:{chosen},set:{browser.id=$0})) {ForEach(VoiceModelVariant.all.filter{$0.engine==model.modelLibraryEngine}.sorted{$0.bytes<$1.bytes}) {Text($0.title).tag($0.id)}}
                ForEach(VoiceModelVariant.all.filter{$0.engine==model.modelLibraryEngine && $0.id==chosen}) {row in
                    let ready=model.voiceVariantReady(row)
                    let selected=model.voiceModelSelection(row.engine)==row.id
                    HStack(alignment:.top,spacing:14) {
                        VStack(alignment:.leading,spacing:5) {
                            HStack {Text(row.title).font(.headline);if selected{Text(L("目前選用")).font(.caption).foregroundStyle(accent)}}
                            Text(ByteCountFormatter.string(fromByteCount:row.bytes,countStyle:.file)+" · "+(ready ? "已安裝":"未安裝")).font(.caption)
                            if let option=ModelOption.all.first(where:{$0.id==row.id}) {ModelRequirement(option:option)}
                            Text(row.repo).font(.caption2).foregroundStyle(.secondary).textSelection(.enabled)
                        }
                        Spacer()
                        VStack(alignment:.trailing) {
                            Button(ready ? "校驗／修復":"下載") {let e=model.engine;model.task("下載 "+row.title) {try e.installDubbing(VoiceEngineChoice.all.first {$0.id==row.engine}?.kind ?? "cosy",variant:row.id)}}
                            Button(selected ? "已選用":"使用此模型") {model.setVoiceModel(row.engine,row.id)}.disabled(!ready || selected)
                            if ready {Button(L("移到垃圾桶"),role:.destructive) {model.removeVoiceVariant(row)}}
                        }
                    }.card()
                }
                if model.modelLibraryEngine=="drama3" {Text(L("Fish Audio Drama 3 · 原生 44.1 kHz · MLX 4-bit。本機生成；廣東話以語言指示引導，請自行覆聽口音與聲調。")).font(.caption).foregroundStyle(.secondary)}
                if model.modelLibraryEngine=="cosyvoice3" {Text(L("此清單係同一個 0.5B 模型嘅不同精度；聲音編碼器另需約 1 GB，各版本共用。")).font(.caption).foregroundStyle(.secondary)}

            }
        }.onAppear {model.modelLibraryEngine=VoiceEngineChoice.active(model.modelLibraryEngine)}.onChange(of:model.modelLibraryEngine) {_ in browser.id=""}.disabled(model.busy)
    }
}
