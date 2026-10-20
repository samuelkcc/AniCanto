import SwiftUI
import AppKit

/// Sizes are logical points. Retina displays add pixels, not smaller controls.
enum StudioMetrics {
    static var fontSize:CGFloat {UserDefaults.standard.string(forKey:"studioDensity")=="large" ? 17:15}
    static var buttonHeight:CGFloat {fontSize+19}
}
enum StudioPalette {
    static var base:Color {AnimeStyle.current.background}
    static var panel:Color {AnimeStyle.current.panel}
    static var border:Color {AnimeStyle.current.secondary.opacity(0.25)}
}
struct StudioButtonStyle:ButtonStyle {
    var prominent=false
    @Environment(\.isEnabled) private var enabled
    func makeBody(configuration:Configuration)->some View {
        configuration.label.font(.system(size:StudioMetrics.fontSize,weight:.medium))
            .foregroundStyle(prominent ? Color.white:Color.primary)
            .padding(.horizontal,10).frame(minHeight:StudioMetrics.buttonHeight)
            .background(prominent ? accent.opacity(configuration.isPressed ? 0.75:1):configuration.isPressed ? accent.opacity(0.20):Color.primary.opacity(0.055),in:RoundedRectangle(cornerRadius:5))
            .overlay(RoundedRectangle(cornerRadius:5).stroke(StudioPalette.border,lineWidth:0.5))
            .opacity(enabled ? 1:0.42)
    }
}
struct StudioPanelHeader:View {
    let title:String
    var icon:String=""
    var body:some View {HStack {if !icon.isEmpty {Image(systemName:icon)};Text(L(title)).font(.system(size:14,weight:.semibold));Spacer()}.padding(.horizontal,12).frame(height:36).background(Color.primary.opacity(0.035))}
}
struct StudioHeader:View {
    @ObservedObject var model:AppModel
    @ObservedObject var editor:ProjectEditor
    @ObservedObject var options:ProjectWorkspaceOptions
    var body:some View {
        VStack(spacing:0) {StudioAppBar(model:model,basic:false);if model.busy {StudioProcessingProgress(model:model)}}
    }
}
struct StudioProcessingProgress:View {
    @ObservedObject var model:AppModel
    private var value:Double? {model.displayProgress.flatMap {$0.isFinite ? min(1,max(0,$0)):nil}}
    var body:some View {
        VStack(alignment:.leading,spacing:4) {
            HStack(spacing:12) {
                Text(!model.busy && model.displayJourney?.complete==true ? L("成品已輸出")+(model.displayJourney?.qualityStatus=="needs-review" ? " · "+L("待覆核"):""):localizedProgressDetail(model.stage)).font(.system(size:13,weight:.semibold)).lineLimit(1)
                Spacer(minLength:4)
                Text(value.map{String(format:"%.0f%%",$0*100)} ?? L("處理中…")).font(.system(size:14,weight:.semibold)).monospacedDigit().fixedSize()
            }
            if let value {
                GeometryReader {g in
                    ZStack(alignment:.leading) {
                        Capsule().fill(accent.opacity(0.16))
                        Capsule().fill(accent).frame(width:g.size.width*value)
                    }
                }.frame(height:6)
                .accessibilityLabel(L("處理進度"))
                .accessibilityValue(String(format:"%.0f%%",value*100))
            } else {ProgressView().progressViewStyle(.linear).tint(accent).frame(height:6).accessibilityLabel(L("處理中…"))}
            ProductionMilestones(journey:model.displayJourney)
            ViewThatFits(in:.horizontal) {
                HStack(alignment:.top,spacing:20) {
                    statusDetail.frame(maxWidth:.infinity,alignment:.leading)
                    ProductionTimeStatus(model:model,compact:true).frame(width:320,alignment:.trailing)
                }.frame(minWidth:760)
                VStack(alignment:.leading,spacing:4) {
                    statusDetail
                    ProductionTimeStatus(model:model,compact:true).frame(maxWidth:.infinity,alignment:.trailing)
                }
            }
        }.padding(.horizontal,12).padding(.vertical,6)
        .background(accent.opacity(0.035))
    }
    @ViewBuilder private var statusDetail:some View {
        if !model.detail.isEmpty,model.detail != model.stage {
            Text(localizedProgressDetail(model.detail)).font(.system(size:12)).foregroundStyle(.secondary).fixedSize(horizontal:false,vertical:true).textSelection(.enabled)
        }
    }
}
extension ContentView {
    var professionalHeader:some View {StudioHeader(model:m,editor:m.projectEditor,options:m.workspaceOptions)}
    var professionalModelPage:some View {
        HStack(spacing:0) {
            VStack(spacing:0) {
                StudioPanelHeader(title:"模型中心",icon:"shippingbox")
                ForEach([("presets","部署方案"),("voices","配音模型"),("text","文字翻譯"),("speech","語音辨識"),("audio","音訊處理"),("runtime","執行環境")],id:\.0) {key,title in
                    Button {m.environmentCategory=key} label:{HStack {Text(L(title));Spacer();if m.environmentCategory==key {Image(systemName:"chevron.right")}}.padding(10).background(m.environmentCategory==key ? accent.opacity(0.14):.clear)}.buttonStyle(.plain)
                }
                Spacer()
                VStack(alignment:.leading,spacing:8) {Text(L("本機模型預算")).font(.headline);Text(String(format:"%.1f GB",ModelHardware.modelBudgetGB)).font(.title2.monospacedDigit());Text(L("模型逐個運行；容量估計已預留系統用量。")).font(.system(size:13)).foregroundStyle(.secondary)}.padding(16)
                CompanionDock(model:m)
            }.frame(width:220).background(FrameChrome(sidebar:true))
            Divider()
            if ["voices","text","speech"].contains(m.environmentCategory) {ProfessionalModelBrowser(model:m)}
            else {ScrollView {environment.padding(24).frame(maxWidth:.infinity,alignment:.leading)}}
        }
    }
}
struct ProfessionalPreferences:View {
    @ObservedObject var model:AppModel
    @AppStorage("studioLanguage") private var language="system"
    @AppStorage("studioTheme") private var appearance="system"
    @AppStorage("studioDensity") private var density="comfortable"
    @AppStorage("animeTheme") private var anime="studio"
    @AppStorage("showStudioCompanion") private var companion=true
    @AppStorage("companionMotion") private var motion=true
    @AppStorage("desktopPetRoaming") private var roaming=true
    @AppStorage("studioCompanionSize") private var companionSize="large"
    @AppStorage("randomAnimeTheme") private var random=false
    var body:some View {
        ScrollView {VStack(alignment:.leading,spacing:24) {
            Text(L("偏好設定")).font(.system(size:24,weight:.semibold))
            GroupBox(L("介面與操作")) {
                VStack(alignment:.leading,spacing:20) {
                    Picker(L("介面語言"),selection:$language) {Text(L("跟隨系統")).tag("system");Text(L("香港繁體中文")).tag("zh-HK");Text("English").tag("en")}
                    Picker(L("外觀"),selection:$appearance) {Text(L("跟隨系統")).tag("system");Text(L("淺色")).tag("light");Text(L("深色")).tag("dark")}.pickerStyle(.segmented)
                    Picker(L("桌面角色"),selection:$anime) {ForEach(StudioThemeChoice.all) {Text(L($0.title)).tag($0.id)}}.id(language)
                    Toggle(L("顯示動畫助手"),isOn:$companion)
                    Toggle(L("角色動態效果"),isOn:$motion)
                    Toggle(L("桌面自由走動"),isOn:$roaming)
                    Button(L("移回螢幕角落")) {DesktopPet.shared.resetPosition()}
                    Picker(L("助手大小"),selection:$companionSize) {Text(L("細")).tag("small");Text(L("標準")).tag("medium");Text(L("大")).tag("large")}
                    Toggle(L("每次啟動隨機助手"),isOn:$random)
                    Text(L("桌面夥伴會按製作狀態轉換動作；可以拖曳及按右鍵設定。減少動態效果會停止動畫與走動。")).font(.system(size:13)).foregroundStyle(.secondary)
                    Picker(L("控制項大小"),selection:$density) {Text(L("舒適 · 15 pt")).tag("comfortable");Text(L("較大 · 17 pt")).tag("large")}.pickerStyle(.segmented)
                    Text(L("4K／Retina 以系統縮放保持字體大小。可拖動面板分隔線，或喺工作區隱藏側欄。")).foregroundStyle(.secondary)
                }.padding(18)
            }
            HStack {Button(L("模型選用")) {ProfessionalSettingsWindow.show(model:model,category:"models")};Button(L("儲存製作預設"),action:model.saveStudioPreset);if model.presetSavedAt != nil {Text(L("預設已儲存")).foregroundStyle(accent)}}
            GroupBox(L("專案資料")) {
                HStack {Text(model.engine.root.path).textSelection(.enabled);Spacer();Button(L("在 Finder 顯示")) {NSWorkspace.shared.open(model.engine.root)}}.padding(18)
            }
            HStack {Button(L("專案／成品管理")) {model.showProjectManager=true};Button(L("關於 AniCanto")) {model.showAbout=true}}
            Spacer()
        }.padding(32).frame(maxWidth:1050,alignment:.leading).frame(maxWidth:.infinity,alignment:.topLeading)}
    }
}
