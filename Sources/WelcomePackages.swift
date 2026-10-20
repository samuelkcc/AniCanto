import SwiftUI

extension Engine {
    func removeWelcomePackage(_ id:String,runtime:Bool) throws {
        let fm=FileManager.default
        func remove(_ relative:String) throws {
            let target=root.appendingPathComponent(relative).standardizedFileURL
            guard target.path.hasPrefix(root.standardizedFileURL.path+"/"),target.resolvingSymlinksInPath().path.hasPrefix(root.resolvingSymlinksInPath().path+"/") else {throw AppFailure(message:"Invalid package path")}
            if fm.fileExists(atPath:target.path) {try fm.removeItem(at:target)}
        }
        if runtime {
            guard Self.welcomeRuntimeNames.contains(id),lightweightPackage else {throw AppFailure(message:"This runtime is part of the application package.")}
            releaseTextModels();try remove(id);try remove("runtime-receipts/"+id+".json")
            return
        }
        guard let option=ModelOption.all.first(where:{$0.id==id}) else {throw AppFailure(message:"Unknown model")}
        releaseTextModels()
        let shared=Set(ModelOption.all.filter {$0.id != id && $0.ready(root)}.flatMap {other in other.files.map {other.relativeFolder+"/"+$0.path}})
        for file in option.files {
            let path=option.relativeFolder+"/"+file.path
            if !shared.contains(path) {try remove(path);try remove(path+".partial")}
        }
        try remove("model-ready/"+id.replacingOccurrences(of:":",with:"-")+".json")
    }
    static let welcomeRuntimeNames=["runtime","text-runtime","asr-runtime","separator-runtime","gsv-runtime","cosy-runtime","local-tts-runtime","qwen-runtime"]
}

final class WelcomePackageState:ObservableObject {
    @Published var pendingID=""
    @Published var pendingTitle=""
    @Published var action=""
    @Published var runtime=false
    @Published var confirm=false
    @Published var cleanupPlan:[String:Any]?
    @Published var scanning=false
    @Published var cleanupConfirm=false
    @Published var cleanupError:String?
}

struct WelcomePackageManager:View {
    @ObservedObject var model:AppModel
    @StateObject private var state=WelcomePackageState()
    @Environment(\.locale) private var locale
    @AppStorage("welcomePackagesExpanded") private var expanded=false
    let plan:[String:Any]
    var english:Bool {locale.identifier.hasPrefix("en")}
    func text(_ zh:String,_ en:String)->String {english ? en:zh}
    var models:[ModelOption] {
        let required=Set((plan["downloads"] as? [[String:Any]] ?? []).compactMap {$0["id"] as? String})
        return ModelOption.all.filter {required.contains($0.id) || $0.ready(model.engine.root) || FileManager.default.fileExists(atPath:model.engine.root.appendingPathComponent($0.relativeFolder).path)}
    }
    func prompt(_ id:String,_ title:String,_ runtime:Bool,_ action:String) {
        state.pendingID=id;state.pendingTitle=title;state.runtime=runtime;state.action=action;state.confirm=true
    }
    func execute(_ id:String,runtime:Bool,action:String) {
        let engine=model.engine
        model.task(text("管理本機元件","Manage local components")) {
            if action != "repair" {try engine.removeWelcomePackage(id,runtime:runtime)}
            if action != "remove" {
                if runtime {try engine.ensureMacRuntime(id)}
                else if let row=ModelOption.all.first(where:{$0.id==id}) {try engine.deployOption(row)}
            }
        }
    }
    func cleanup(_ mode:String) {
        guard !model.busy,!state.scanning else{return}
        state.scanning=true;state.cleanupError=nil
        let engine=model.engine
        DispatchQueue.global(qos:.userInitiated).async {
            do {
                let plan=try StudioContract.call(["operation":"cleanup-plan","root":engine.root.path,"mode":mode],resources:engine.resources)
                DispatchQueue.main.async {state.cleanupPlan=plan;state.scanning=false;state.cleanupConfirm=true}
            } catch {DispatchQueue.main.async {state.scanning=false;state.cleanupError=error.localizedDescription}}
        }
    }
    func removeDownloads() {
        guard let plan=state.cleanupPlan,!model.busy else{return}
        let engine=model.engine
        model.busy=true
        DispatchQueue.global(qos:.userInitiated).async {
            engine.shutdown()
            do {
                let result=try StudioContract.call(["operation":"cleanup-downloads","root":engine.root.path,"mode":plan["mode"] ?? "models","token":plan["token"] ?? ""],resources:engine.resources)
                DispatchQueue.main.async {
                    if result["complete"] as? Bool != true {
                        let alert=NSAlert();alert.messageText=text("部分檔案未能移除","Some files could not be removed")
                        alert.informativeText=(result["failures"] as? [String] ?? []).prefix(8).joined(separator:"\n");alert.runModal()
                    }
                    NSApp.terminate(nil)
                }
            } catch {
                DispatchQueue.main.async {
                    let alert=NSAlert();alert.messageText=text("清理未完成","Cleanup did not complete");alert.informativeText=error.localizedDescription;alert.runModal();NSApp.terminate(nil)
                }
            }
        }
    }
    var cleanupDescription:String {
        guard let plan=state.cleanupPlan else{return ""}
        let size=ByteCountFormatter.string(fromByteCount:(plan["bytes"] as? NSNumber)?.int64Value ?? 0,countStyle:.file)
        let scope=plan["mode"] as? String=="all" ? text("模型、執行環境、工具及下載快取","Models, runtimes, tools and download caches"):text("模型及未完成下載","Models and partial downloads")
        return scope+" · "+size+"\n"+text("會先停止本 App 嘅模型服務，清理後關閉 App。影片、專案、錄音、成品及設定會保留。下次使用時會下載所需元件。資料夾外嘅共用快取唔會移除。","The app will stop its model services, remove these downloads and close. Videos, projects, recordings, exports and settings are kept. Required components download again next time. Shared caches outside the app folder are kept.")
    }
    @ViewBuilder func actions(_ id:String,_ title:String,_ runtime:Bool) -> some View {
        Menu {
            Button(text("檢查及修復（沿用正常檔案）","Check & repair (reuse valid files)")) {execute(id,runtime:runtime,action:"repair")}
            Button(text("重新下載…","Download again…")) {prompt(id,title,runtime,"redownload")}
            Button(text("移除本機檔案…","Remove local files…"),role:.destructive) {prompt(id,title,runtime,"remove")}
        } label:{Image(systemName:"ellipsis.circle")}.menuStyle(.borderlessButton).frame(width:28).disabled(model.busy)
    }
    var body:some View {
        DisclosureGroup(text("管理模型與執行環境","Manage models & runtimes"),isExpanded:$expanded) {
            VStack(alignment:.leading,spacing:10) {
                ForEach(models) {row in
                    HStack(alignment:.top) {
                        VStack(alignment:.leading,spacing:3) {Text(row.title);Text(row.ready(model.engine.root) ? text("已安裝 · 沿用","Installed · reuse"):text("未完整安裝","Not fully installed")).foregroundStyle(.secondary)}
                        Spacer();actions(row.id,row.title,false)
                    }.font(.caption)
                }
                Divider()
                ForEach((plan["runtimeInventory"] as? [[String:Any]] ?? []).indices,id:\.self) {i in
                    let row=(plan["runtimeInventory"] as! [[String:Any]])[i]
                    let name=row["name"] as? String ?? ""
                    HStack {Text(name);Spacer();Text(row["ready"] as? Bool==true ? text("可用","Ready"):text("需檢查／安裝","Check / install")).foregroundStyle(.secondary);actions(name,name,true)}.font(.caption)
                }
                Divider()
                Text(model.engine.root.path).font(.caption2).foregroundStyle(.secondary).textSelection(.enabled)
                HStack {
                    Button(text("刪除已下載模型…","Delete downloaded models…")) {cleanup("models")}
                    Button(text("清除全部下載並關閉…","Delete all downloads & close…")) {cleanup("all")}
                }.disabled(model.busy || state.scanning)
                if state.scanning {ProgressView().progressViewStyle(.linear);Text(text("正在計算檔案大小…","Calculating file sizes…")).font(.caption)}
                if let error=state.cleanupError {Text(error).font(.caption).foregroundStyle(.orange)}
                Button(text("開啟儲存資料夾","Open storage folder")) {NSWorkspace.shared.open(model.engine.root)}
                Text(text("只管理本機模型及元件；影片、專案同成品會保留。重新下載前會再確認。","These controls manage local models and components. Videos, projects and exports are kept. Downloading again asks for confirmation.")).font(.caption).foregroundStyle(.secondary)
            }.padding(.top,8)
        }.alert(text("移除下載檔案並關閉？","Remove downloaded files & close?"),isPresented:$state.cleanupConfirm) {
            Button(text("取消","Cancel"),role:.cancel) {}
            Button(text("移除並關閉","Remove & close"),role:.destructive) {removeDownloads()}
        } message:{Text(cleanupDescription)}
        .alert(state.action=="remove" ? text("移除本機元件？","Remove local component?"):text("重新下載元件？","Download component again?"),isPresented:$state.confirm) {
            Button(text("取消","Cancel"),role:.cancel) {}
            Button(state.action=="remove" ? text("移除","Remove"):text("重新下載","Download again"),role:.destructive) {execute(state.pendingID,runtime:state.runtime,action:state.action)}
        } message:{Text(state.pendingTitle+"\n"+text("影片、專案及已輸出檔案會保留。所選元件要重新安裝完成先可以使用。","Your videos, projects and exports are kept. This component must be installed again before it can be used."))}
    }
}
