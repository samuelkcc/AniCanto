import SwiftUI

/// Frozen per submitted job. Interface mode never changes production policy.
enum ProductionModePolicy {
    static func applying(to input:[String:Any])->[String:Any] {
        var cfg=input
        if !["fast","normal"].contains(input["productionMode"] as? String ?? "standard") {
            if let saved=cfg.removeValue(forKey:"_standardProductionSettings") as? [String:Any] {
                for (key,value) in saved {if value is NSNull {cfg.removeValue(forKey:key)} else {cfg[key]=value}}
            }
            return cfg
        }
        let keys=["roleAnalysisMode","voiceStyleMode","autoSpeakers","separateBackground","speechTiming","translate","autoApprove","autoFit","strictSpeechTiming","continueOnError","autoValidate","aiAutoFix","fallbackToRoleVoice","allowCrossEngineRepair","requireCompleteDubbing","fillMissingVoiceScripts","reanalyzeRoles","independentReferences","preserveNonverbal"]
        if cfg["_standardProductionSettings"] == nil {cfg["_standardProductionSettings"]=Dictionary(uniqueKeysWithValues:keys.map {($0,cfg[$0] ?? NSNull())})}
        cfg.merge(["roleAnalysisMode":"independent","voiceStyleMode":"clone","autoSpeakers":true,
                   "separateBackground":true,"speechTiming":true,"translate":true,"autoApprove":true,
                   "autoFit":true,"strictSpeechTiming":true,"continueOnError":true,
                   "autoValidate":false,"aiAutoFix":false,"fallbackToRoleVoice":false,
                   "allowCrossEngineRepair":false,"requireCompleteDubbing":false,
                   "fillMissingVoiceScripts":false,"reanalyzeRoles":false,
                   "independentReferences":false,"preserveNonverbal":false]) {_,new in new}
        return cfg
    }
}

struct ProductionModeControl:View {
    @Binding var mode:String
    var locked=false
    var body:some View {
        VStack(alignment:.leading,spacing:8) {
            Text(L("製作模式")).font(.subheadline.weight(.semibold))
            Picker(L("製作模式"),selection:$mode) {
                Text(L("一般模式")).tag("normal")
                Text(L("完整 AI 覆核")).tag("standard")
                Text(L("高速模式")).tag("fast")
            }.pickerStyle(.segmented).labelsHidden().disabled(locked)
            if mode=="fast" {
                Label(L("跳過所有品質檢查；生成影片可能存在配音缺陷。"),systemImage:"exclamationmark.triangle").font(.caption).foregroundStyle(.orange)
                Text(L("Qwen 翻譯 → 逐句模仿分離原聲 → 時長對齊 → 合成。不建立角色卡、不覆聽或品質重錄；仍檢查檔案有效性。失敗句會列於摘要，可能留空。"))
                    .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal:false,vertical:true)
            } else if mode=="normal" {
                Text(L("逐句模仿原聲；局部處理 OP／ED、人名、普通話及缺聲，不用通用角色卡。"))
                    .font(.caption).foregroundStyle(.secondary)
            } else {
                Text(L("包含角色配對、品質檢查及自動修復。")).font(.caption).foregroundStyle(.secondary)
            }
            if locked {Text(L("已提交工作沿用開始時嘅模式。")).font(.caption).foregroundStyle(.secondary)}
        }.accessibilityIdentifier("production-mode")
    }
}

extension AppModel {
    var workspaceProductionMode:String {projectEditor.document == nil ? productionMode:projectEditor.productionSelection(self).productionMode}
    func setWorkspaceProductionMode(_ value:String) {
        guard !busy,["standard","normal","fast"].contains(value) else{return}
        productionMode=value
        if projectEditor.document != nil {projectEditor.productionSelection(self).productionMode=value}
    }
}
