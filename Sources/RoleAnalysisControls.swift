import SwiftUI

struct RoleAnalysisControls:View {
    let model:AppModel
    var compact=false
    @AppStorage("studioInterfaceMode") private var interfaceMode="simple"
    var body:some View {
        VStack(alignment:.leading,spacing:8) {
            Text(L("角色分析方式")).font(.headline)
            Picker(L("角色分析方式"),selection:Binding(get:{model.roleAnalysisMode=="independent" ? "independent":"audio"},set:{model.roleAnalysisMode=$0;if $0=="independent" {model.visualRoleAnalysisEnabled=false}})) {
                Text(L("聲音分組（預設）")).tag("audio")
                Text(L("逐句聲音配對")).tag("independent")
            }.pickerStyle(.radioGroup).labelsHidden().disabled(!model.autoSpeakers)
            if interfaceMode=="professional" {
                Toggle(L("影像輔助角色分析（較慢，預設關閉）"),isOn:Binding(get:{model.visualRoleAnalysisEnabled},set:{model.visualRoleAnalysisEnabled=$0;model.roleAnalysisMode=$0 ? "audiovisual":"audio"})).disabled(!model.autoSpeakers || model.productionMode=="fast")
                if model.visualRoleAnalysisEnabled {
                    Text(L("逐段抽取畫面、辨識頭像及比對角色，可能顯著增加處理時間；自動配音不需要啟用。"))
                        .font(.caption).foregroundStyle(.orange).fixedSize(horizontal:false,vertical:true)
                    Text(model.selectedModelID("visual")).font(.caption).foregroundStyle(.secondary).lineLimit(2)
                }
            }
            if !compact {
                Text(L(model.roleAnalysisMode=="independent" ? "每句只用自己的原聲參考；不做聲紋分組、角色畫面分析或相簿截圖。":"按原聲聲紋分組，共用同角色參考錄音；預設不做逐段影像分析。"))
                    .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal:false,vertical:true)
                Text(L("保留逐句翻譯、配音、時長對齊及標準模式自動修復。"))
                    .font(.caption).foregroundStyle(.secondary).fixedSize(horizontal:false,vertical:true)
            }
        }
    }
}

struct RoleAnalysisResult:View {
    let result:[String:Any]
    var body:some View {
        VStack(alignment:.leading,spacing:6) {
            Text(L("本片角色分析結果")).font(.headline)
            if result["actual"] as? String=="audiovisual" {
                Text(L("聲音＋畫面")+" · \(result["analyzed"] as? Int ?? 0)/\(result["total"] as? Int ?? 0)")
                Text(L("有共同證據而重新配對")+" · \((result["changedIndices"] as? [Int] ?? []).count)")
                Text(L("畫面屬抽樣輔助，並非完整嘴形追蹤或身份認證。")).font(.caption).foregroundStyle(.secondary)
            } else if result["actual"] as? String=="independent" {
                Text(L("逐句聲音配對")+" · \(result["analyzed"] as? Int ?? 0)")
                Text(L("沒有共用聲線分組；逐句參考需要試聽。")).font(.caption).foregroundStyle(.secondary)
            } else {
                Text(L("已改用聲音分析")).foregroundStyle(.orange)
                Text(localizedProgressDetail(result["reason"] as? String ?? "")).font(.caption).textSelection(.enabled)
            }
        }
    }
}
