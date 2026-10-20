import SwiftUI
final class ModelTableSelection:ObservableObject {
    @Published var selected=""
    @Published var installed:Set<String>=[]
    @Published var local:Set<String>=[]
    @Published var installedOnly=false
    @Published var speechRole="speech"
    @Published var search=""
    @Published var filter="all"
    @Published var usedRoles:[String:[String]]=[:]
    @MainActor func refresh(_ model:AppModel) {
        installed=Set(ModelOption.all.filter {option in
            if option.category=="voice",let variant=VoiceModelVariant.all.first(where:{$0.id==option.id}) {return model.voiceVariantReady(variant)}
            return option.ready(model.engine.root)
        }.map(\.id))
        local=Set(ModelOption.all.filter {FileManager.default.fileExists(atPath:model.engine.root.appendingPathComponent($0.relativeFolder).path)}.map(\.id))
        var current:[String:[String]]=[:]
        for role in ModelUsageRole.all {let id=model.selectedModelID(role.id);if !id.isEmpty {current[id,default:[]].append(role.title)}}
        usedRoles=current
    }
}
struct ProfessionalModelBrowser:View {
    @AppStorage("studioLanguage") private var language="system"
    @ObservedObject var model:AppModel
    @StateObject private var selection=ModelTableSelection()
    @AppStorage("showAllModelSizes") private var showAllSizes=false
    var rows:[ModelOption] {
        let category=model.environmentCategory=="voices" ? "voice":model.environmentCategory=="text" ? "text":nil
        return ModelOption.all.filter {row in
            (row.engine != "qwen-tts" || (selection.filter=="local" && selection.local.contains(row.id))) && (category==nil ? ["speech","asr"].contains(row.category):row.category==category) && (row.visibleForMemory(showAll:showAllSizes) || selection.local.contains(row.id)) && (!selection.installedOnly || selection.installed.contains(row.id)) && (selection.filter=="all" || (selection.filter=="local" && selection.local.contains(row.id)) || (selection.filter=="current" && selection.usedRoles[row.id] != nil)) && (selection.search.isEmpty || (row.title+row.repo).localizedCaseInsensitiveContains(selection.search))
        }.sorted {$0.engine==$1.engine ? $0.bytes<$1.bytes:$0.engine<$1.engine}
    }
    var selected:ModelOption? {ModelOption.all.first {$0.id==selection.selected}}
    var preferredSelection:String {
        let current=model.environmentCategory=="text" ? model.selectedModel:model.environmentCategory=="voices" ? model.cosyModel:model.engine.selectedVariant("speech",default:"whisper-large-v3")
        return rows.first(where:{$0.id==current})?.id ?? rows.first(where:{$0.deployable})?.id ?? ""
    }
    var body:some View {
        HStack(spacing:0) {
            VStack(spacing:0) {
                VStack(alignment:.leading,spacing:10) {
                    TextField(L("搜尋模型"),text:$selection.search).textFieldStyle(.roundedBorder)
                    Picker(L("顯示模型"),selection:$selection.filter) {Text(L("全部模型")).tag("all");Text(L("本機檔案（包括未完成）")).tag("local");Text(L("目前選用")).tag("current")}.pickerStyle(.menu).frame(maxWidth:360,alignment:.leading)
                    HStack {Toggle(L("只顯示已下載"),isOn:$selection.installedOnly).toggleStyle(.checkbox);Toggle(L("顯示全部大小"),isOn:$showAllSizes).toggleStyle(.checkbox);Spacer()}
                    Text(String(format:L("本機模型預算 %.1f GB"),ModelHardware.modelBudgetGB)).font(.system(size:12)).foregroundStyle(.secondary)
                }.padding(16)
                HStack {Text(L("模型／版本")).frame(maxWidth:.infinity,alignment:.leading);Text(L("精度")).frame(width:60);Text(L("下載大小")).frame(width:80);Text(L("運行記憶體")).frame(width:80);Text(L("狀態")).frame(width:90)}.font(.system(size:13,weight:.semibold)).padding(.horizontal,16).frame(height:34).background(Color.primary.opacity(0.05))
                ScrollView {LazyVStack(spacing:0) {
                    if model.environmentCategory=="voices" {Button {selection.selected="gpt-v4";model.modelLibraryEngine="gpt-sovits"} label:{HStack {Text("GPT-SoVITS V2 Pro Plus／V4").font(.system(size:15,weight:.medium));Spacer();Text(L("兩種獨立版本")).foregroundStyle(.secondary)}.padding(16).frame(maxWidth:.infinity).background(selection.selected=="gpt-v4" ? accent.opacity(0.14):.clear)}.buttonStyle(.plain);Divider()}
                    ForEach(rows) {row in
                        let inUse=selection.usedRoles[row.id] != nil
                        Button {selection.selected=row.id} label:{
                            HStack {
                                Text(row.title).font(.system(size:14)).lineLimit(2).frame(maxWidth:.infinity,alignment:.leading)
                                Text(row.precision.hasPrefix("int8 runtime") ? "int8 / fp16":row.precision).font(.system(size:13)).frame(width:60).help(row.precision)
                                Text(row.deployable ? ByteCountFormatter.string(fromByteCount:row.bytes,countStyle:.file):L("未提供")).font(.system(size:13)).frame(width:80)
                                Text(String(format:"%.1f GB",row.estimatedMemoryGB)).font(.system(size:13)).foregroundStyle(row.memoryWarning ? .orange:.secondary).frame(width:80)
                                Text(L(!row.deployable ? "未接通":selection.installed.contains(row.id) ? (inUse ? "使用中":"已下載") : selection.local.contains(row.id) ? "未完成下載":"未下載")).font(.system(size:13,weight:inUse ? .semibold:.regular)).foregroundStyle(inUse ? accent:Color.primary).frame(width:90)
                            }.padding(.horizontal,16).frame(minHeight:44).background(selection.selected==row.id ? accent.opacity(0.14):.clear)
                        }.buttonStyle(.plain)
                        Divider()
                    }
                }}
            }.frame(maxWidth:.infinity)
            Divider()
            ScrollView {
                VStack(alignment:.leading,spacing:20) {
                    if selection.selected=="gpt-v4" {VoiceModelLibrary(model:model)}
                    else if let row=selected {
                        Text(row.title).font(.title2.bold())
                        if row.engine=="qwen-tts" {Text(L("Qwen TTS 已停用；只保留本機檔案管理，不再用於新配音。")).foregroundStyle(.orange)}
                        Text(row.repo).font(.system(size:13)).textSelection(.enabled)
                        if row.deployable {ModelRequirement(option:row)} else {Text(L("此版本未有已驗證下載檔案，暫時無法部署。請選擇其他版本。")).foregroundStyle(.orange)}
                        Divider()
                        let roles=model.rolesUsing(row.id)
                        if !roles.isEmpty {Label(L("目前選用")+" · "+roles.map {L($0)}.joined(separator:"、"),systemImage:"checkmark.circle.fill").foregroundStyle(accent)}
                        if selection.local.contains(row.id) && !selection.installed.contains(row.id) {Text(L("下載未完成；按續傳可沿用已下載內容。")).foregroundStyle(.orange)}
                        if row.category=="speech" {Picker(L("使用用途"),selection:$selection.speechRole) {Text(L("日語主辨識")).tag("speech");Text(L("角色參考辨識")).tag("referenceSpeech")}}
                        Button(L(selection.installed.contains(row.id) ? "校驗／修復":selection.local.contains(row.id) ? "繼續下載":"下載此版本")) {let engine=model.engine;model.task(L("部署模型")) {try engine.deployOption(row)}}.buttonStyle(StudioButtonStyle(prominent:true)).disabled(model.busy || !row.deployable || row.engine=="qwen-tts")
                        Button(L("使用此版本")) {use(row)}.disabled(model.busy || !selection.installed.contains(row.id) || row.engine=="qwen-tts")
                        Button(L("移到垃圾桶"),role:.destructive) {model.trashModel(row);selection.refresh(model)}.disabled(model.modelRemovalReason(row) != nil)
                        if let reason=model.modelRemovalReason(row) {Text(reason).font(.caption).foregroundStyle(.secondary)}
                        Text(L("下載後再按「使用此版本」，已下載嘅其他大小會保留。")).font(.system(size:13)).foregroundStyle(.secondary)
                    } else {Text(L("選擇模型以查看容量、系統要求及部署操作。")).foregroundStyle(.secondary)}
                    if model.environmentCategory=="text" {
                        Divider();Text(L("其他文字模型")).font(.headline)
                        TextField(L("Ollama 模型標籤"),text:$model.customTextModel).textFieldStyle(.roundedBorder)
                        Button(L("下載文字模型")) {
                            let name=model.customTextModel.trimmingCharacters(in:.whitespacesAndNewlines)
                            guard name.range(of:#"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,120}$"#,options:.regularExpression) != nil else {model.error=L("模型名稱格式無效。");return}
                            let engine=model.engine;model.task(L("下載文字模型")) {try engine.pullModel(name)}
                        }.disabled(model.busy || model.customTextModel.isEmpty)
                    }
                }.padding(24).frame(maxWidth:.infinity,alignment:.leading)
            }.frame(width:340).background(StudioPalette.panel)
        }.onAppear {selection.refresh(model);selection.selected=preferredSelection}
        .onChange(of:model.environmentCategory) {_ in selection.search="";selection.refresh(model);selection.selected=preferredSelection}
        .onChange(of:showAllSizes) {_ in if !rows.contains(where:{$0.id==selection.selected}) && selection.selected != "gpt-v4" {selection.selected=preferredSelection}}
        .onChange(of:model.busy) {busy in if !busy {selection.refresh(model)}}
        .onChange(of:model.modelSelectionRevision) {_ in selection.refresh(model)}
        .onChange(of:[model.selectedModel,model.cosyModel,model.qwenModel,model.voxcpmModel,model.wsyueModel,model.drama3Model]) {_ in selection.refresh(model)}
    }
    func use(_ row:ModelOption) {
        model.useModel(row.category=="text" ? "text":row.category=="voice" ? row.engine:row.category=="asr" ? "asr":selection.speechRole,row.id)
    }
}

extension ModelOption {
    func visibleForMemory(showAll:Bool,budgetGB:Double=ModelHardware.modelBudgetGB)->Bool {showAll || estimatedMemoryGB<=budgetGB}
}
