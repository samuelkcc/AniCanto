import SwiftUI

final class WelcomeDeploymentState:ObservableObject {
    @Published var plan:[String:Any]?
    @Published var error:String?
    @Published var loading=false
    @Published var showing=false
    func refresh(_ engine:Engine,engineID:String) {
        guard !loading else{return};loading=true;error=nil
        DispatchQueue.global(qos:.userInitiated).async {
            do {let value=try engine.firstRunModelPlan(engine:engineID);DispatchQueue.main.async {self.plan=value;self.loading=false}}
            catch {DispatchQueue.main.async {self.error=error.localizedDescription;self.loading=false}}
        }
    }
}
struct WelcomeDeployment:View {
    @ObservedObject var model:AppModel
    @StateObject private var state=WelcomeDeploymentState()
    @Environment(\.locale) private var locale
    var english:Bool {locale.identifier.hasPrefix("en")}
    func text(_ zh:String,_ en:String)->String {english ? en:zh}
    var body:some View {
        VStack(alignment:.leading,spacing:12) {
            Label(text(state.plan?["setupReady"] as? Bool==true ? "本機模型 · 已準備好":"本機模型與部署",state.plan?["setupReady"] as? Bool==true ? "Local models · Ready":"Local models & setup"),systemImage:"desktopcomputer").font(.headline)
            if state.loading {Text(text("正在檢查電腦及已安裝元件…","Checking your computer and installed components…")).font(.caption);ProgressView().progressViewStyle(.linear)}
            if let plan=state.plan {
                let hardware=plan["hardware"] as? [String:Any] ?? [:]
                Text(String(format:text("系統記憶體 %.0f GB · 模型預算 %.1f GB","System memory %.0f GB · Model budget %.1f GB"),hardware["memoryGB"] as? Double ?? 0,plan["memoryBudgetGB"] as? Double ?? 0)).font(.caption).foregroundStyle(.secondary)
                if let engine=plan["engine"] as? String {
                    Text((VoiceEngineChoice.all.first {$0.id==engine}?.title ?? engine)).font(.subheadline.bold())
                    if engine != plan["requestedEngine"] as? String {Text(text("Drama 3 超出記憶體預算，將改用 GPT V2 Pro Plus。","Drama 3 exceeds your memory budget. Setup will use GPT V2 Pro Plus.")).font(.caption).foregroundStyle(.orange)}
                }
                let downloads=plan["downloads"] as? [[String:Any]] ?? []
                if (plan["warnings"] as? [String] ?? []).contains("drama3-small-cpu-fallback") {
                    Text(text("完整 Drama 3 超出本機預算，會用 Drama3-small。此版本使用 CPU，廣東話效果屬實驗性，速度可能較慢。","Full Drama 3 exceeds the memory budget. Drama3-small will be used on CPU; Cantonese quality is experimental and generation may be slower.")).font(.caption).foregroundStyle(.orange)
                }
                let inventory=plan["installedInventory"] as? [[String:Any]] ?? []
                let runtimes=plan["runtimeInventory"] as? [[String:Any]] ?? []
                let needed=downloads.filter {$0["installed"] as? Bool != true}
                HStack {
                    Label(text("沿用 \(downloads.count-needed.count) 項","Reuse \(downloads.count-needed.count)"),systemImage:"checkmark.circle").foregroundStyle(.green)
                    Spacer()
                    Text(text("待下載模型：","Models to download: ")+ByteCountFormatter.string(fromByteCount:needed.reduce(Int64(0)) {$0+(($1["bytes"] as? NSNumber)?.int64Value ?? 0)},countStyle:.file))
                }.font(.caption)
                Text(text("另計執行環境及分離元件；已完成同可續傳檔案會沿用。模型逐個載入，唔會同時佔用全部記憶體。","Runtimes and audio components are additional. Completed files and partial downloads are reused. Models load one at a time.")).font(.caption).foregroundStyle(.secondary)
                if !runtimes.isEmpty {
                    DisclosureGroup(text("執行環境狀態","Runtime status")) {
                        ForEach(runtimes.indices,id:\.self) {i in
                            HStack {Text(runtimes[i]["name"] as? String ?? "");Spacer();Text(runtimes[i]["ready"] as? Bool==true ? text("已檢查 · 沿用","Verified · reuse"):text("檢查並補齊","Check & install missing"))}.font(.caption)
                        }
                        Text(text("儲存於 ~/Library/Application Support/SamCantoSync；只補齊缺少或損壞項目。","Stored in ~/Library/Application Support/SamCantoSync. Only missing or damaged components are installed.")).font(.caption).foregroundStyle(.secondary)
                    }
                }
                if !inventory.isEmpty {
                    DisclosureGroup(text("已安裝模型（\(inventory.count)）","Installed models (\(inventory.count))")) {
                        ForEach(inventory.indices,id:\.self) {i in
                            HStack(alignment:.top) {Text(inventory[i]["title"] as? String ?? "").fixedSize(horizontal:false,vertical:true);Spacer();Label(text("已安裝","Installed"),systemImage:"checkmark.circle.fill").foregroundStyle(.green)}.font(.caption)
                        }
                    }
                }
                DisclosureGroup(text("下載計劃與用途","Download plan & purpose")) {
                    ForEach(downloads.indices,id:\.self) {i in
                        HStack(alignment:.top) {
                            VStack(alignment:.leading,spacing:3) {
                                Text(downloads[i]["title"] as? String ?? downloads[i]["id"] as? String ?? "").fixedSize(horizontal:false,vertical:true)
                                Text(purpose(downloads[i]["id"] as? String ?? "",plan)).foregroundStyle(.secondary)
                            }
                            Spacer()
                            Text(downloads[i]["installed"] as? Bool==true ? text("已安裝 · 沿用","Installed · reuse"):text("下載 · ","Download · ")+ByteCountFormatter.string(fromByteCount:(downloads[i]["bytes"] as? NSNumber)?.int64Value ?? 0,countStyle:.file)).multilineTextAlignment(.trailing)
                        }.font(.caption).padding(.vertical,3)
                    }
                    Text(text("另需執行環境、原聲分離及聲紋元件；下載可續傳。","Runtime, audio separation and speaker components are also required. Downloads can resume.")).font(.caption).foregroundStyle(.secondary)
                }
                WelcomePackageManager(model:model,plan:plan)
                if plan["setupReady"] as? Bool==true {
                    Label(text("沿用現有模型，無需重新部署。可以直接進入工作室。","Your existing models are ready. Enter the studio without setting up again."),systemImage:"checkmark.circle.fill").font(.caption).foregroundStyle(.green)
                } else if plan["canDeployModels"] as? Bool==true {
                    Button {model.deployFirstRun(plan)} label:{Label(text(plan["existingInstallation"] as? Bool==true ? "只補齊缺少項目":"一按部署建議模型",plan["existingInstallation"] as? Bool==true ? "Install missing components only":"Set up recommended models"),systemImage:"arrow.down.circle")}.disabled(model.busy)
                } else {
                    Text(text("暫時未有適合呢部電腦嘅完整自動部署方案。請到模型中心檢查支援情況。","A complete automatic setup is not available for this computer yet. Check supported options in Model Center.")).font(.caption).foregroundStyle(.orange)
                }
            }
            if model.busy {
                VStack(alignment:.leading,spacing:8) {
                    Text(L(model.stage)).font(.subheadline.bold())
                    if let transfer=model.downloadTransfer,let total=transfer.totalBytes,total>0 {
                        Text(transfer.stateTitle).font(.caption.bold())
                        ProgressView(value:min(1,max(0,transfer.bytesReceived/total)))
                        Text(transfer.file).font(.caption).lineLimit(2)
                        HStack {Text(transfer.sizeText);Spacer();if transfer.state=="transferring" {Text(transfer.speedText);Text(text("剩餘 ","Remaining ")+transfer.remainingText)}}.font(.caption.monospacedDigit()).foregroundStyle(.secondary)
                    } else if let component=model.componentProgress {
                        if let value=component.fraction {ProgressView(value:value)} else {ProgressView().progressViewStyle(.linear)}
                        Text(component.label).font(.caption)
                    } else {
                        ProgressView().progressViewStyle(.linear)
                        Text(text("安裝或首次載入模型時會較慢；進度暫時無法按百分比計算。","Installing or loading a model for the first time can take longer. A percentage is not available for this step.")).font(.caption).foregroundStyle(.secondary)
                    }
                    Text(model.detail).font(.caption).lineLimit(3).textSelection(.enabled)
                    Button(text("暫停並保留進度","Pause & keep progress")) {Task.detached {model.engine.cancel()}}
                }
            }
            if let error=state.error ?? model.error {Text(error).font(.caption).foregroundStyle(.orange).textSelection(.enabled)}
        }.padding(16).frame(maxWidth:.infinity,alignment:.leading).background(accent.opacity(0.06),in:RoundedRectangle(cornerRadius:14))
        .onAppear {state.refresh(model.engine,engineID:model.ttsBackend)}
        .onChange(of:model.busy) {busy in if !busy {state.refresh(model.engine,engineID:model.ttsBackend)}}
    }
    func purpose(_ id:String,_ plan:[String:Any])->String {
        let labels=["text":text("翻譯及精簡台詞","Translate & fit dialogue"),"visual":text("畫面角色分析","Visual role analysis"),"voice":text("生成配音","Generate dubbed speech"),"speech":text("日語辨識及時間","Japanese speech & timing"),"asr":text("獨立辨識","Independent speech recognition"),"referenceSpeech":text("參考錄音文字","Reference transcription")]
        if id.contains("classifier") {return text("分辨音樂、對白及其他聲音，輔助偵測 OP／ED","Detect music, speech and other sounds to help identify openings / endings")}
        let result=(plan["roles"] as? [String:String] ?? [:]).keys.sorted().filter {(plan["roles"] as? [String:String])?[$0]==id}.compactMap {labels[$0]}.joined(separator:" · ")
        return result.isEmpty ? text("配音流程所需元件","Component required for production"):result
    }
}
