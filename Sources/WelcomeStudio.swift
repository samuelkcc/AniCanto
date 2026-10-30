import SwiftUI
import AppKit

final class WelcomeSession:ObservableObject {
    @Published var showWelcome=true
    @Published var showing=false
    @Published var expert=false
    @Published var setupExpanded=true
}

enum WelcomePalette {
    static let keys=["studio","ocean","energy","ninja","retro","forest","future","mint","moonflower"]
    static func color(_ key:String)->Color {
        let hex:UInt32=["ocean":0x007E91,"energy":0xB84D18,"ninja":0x426D61,"retro":0xB34372,"forest":0x47773E,"future":0x3268BC,"studio":0x7050B9,"mint":0x23796A,"moonflower":0x8051AA,"ensemble":0xA64A51][key] ?? 0x7050B9
        return Color(red:Double((hex>>16)&255)/255,green:Double((hex>>8)&255)/255,blue:Double(hex&255)/255)
    }
}
struct StudioHelpButton:View {
    @AppStorage("studioLanguage") private var language="system"
    var body:some View {
        Button {NotificationCenter.default.post(name:Notification.Name("AniCantoTutorial"),object:nil)} label:{Label(L("使用教學"),systemImage:"questionmark.circle")}
            .id(language)
    }
}
struct StudioTutorial:View {
    var close:()->Void = {}
    @AppStorage("studioLanguage") private var language="system"
    @StateObject private var viewState=WelcomeSession()
    var body:some View {
        VStack(alignment:.leading,spacing:20) {
            HStack {Text(L("使用教學")).font(.largeTitle.bold());Spacer();Button(action:close) {Image(systemName:"xmark").accessibilityLabel(L("關閉"))}.keyboardShortcut(.cancelAction)}
            Picker(L("介面模式"),selection:$viewState.expert) {Text(L("基本模式")).tag(false);Text(L("專家模式")).tag(true)}.pickerStyle(.segmented)
            ScrollView {
                VStack(alignment:.leading,spacing:24) {
                    if viewState.expert {
                        step("1","揀一段對白","喺時間線點選對白，預覽畫面、原文及翻譯會同步。先揀需要處理嘅配音語言。")
                        step("2","先聽，再重錄","右邊「試聽」列出本段錄音。要另一個版本，就去「重錄」揀引擎，再按生成新錄音。原錄音會保留。")
                        step("3","採用你鍾意嘅錄音","比較錄音後按採用。角色參考同語速喺「調整」頁；字幕可以直接改。最後按右上角匯出，製作新版。")
                    } else {
                        step("1","加入一集，或者成季","匯入一條或多條影片。影片清單可以切換預覽、移除項目，亦可以開始全部待處理影片。")
                        step("2","揀聲音同字幕","只揀一個配音引擎，再選香港廣東話、英文或雙語。字幕可多選，輸出後可以開關及切換。")
                        step("3","開始，交畀工作室","自動辨識、翻譯、配音、檢查、修復及匯出。完成嘅對白可以即時試聽；暫停並保存後可繼續。")
                    }
                    step("⚡","高速模式","跳過所有品質檢查；生成影片可能存在配音缺陷。")
                    Text(L("Qwen 翻譯 → 逐句模仿分離原聲 → 時長對齊 → 合成。不建立角色卡、不覆聽或品質重錄；仍檢查檔案有效性。失敗句會列於摘要，可能留空。")).font(.callout).foregroundStyle(.secondary)
                    Divider()
                    step("↗","搵返成品","完成後按顯示檔案，或者到專案／成品管理。首次使用先下載所需模型；速度視乎電腦、引擎及影片長度。")
                    Text(L("翻譯以香港常用廣東話為目標。AI 仍可能譯錯或讀錯；自動修復會保留記錄，無法完成時會保存進度及說明原因。")).font(.callout).foregroundStyle(.secondary)
                }.padding(.vertical,12)
            }
        }.padding(28).frame(maxWidth:.infinity,maxHeight:.infinity).id(language)
    }
    func step(_ number:String,_ title:String,_ detail:String)->some View {
        HStack(alignment:.top,spacing:18) {
            Text(number).font(.title2.bold()).foregroundStyle(accent).frame(width:38,height:38).background(accent.opacity(0.1),in:RoundedRectangle(cornerRadius:10))
            VStack(alignment:.leading,spacing:7) {Text(L(title)).font(.title3.bold());Text(L(detail)).foregroundStyle(.secondary).fixedSize(horizontal:false,vertical:true)}
        }
    }
}
struct WelcomeStudio:View {
    @StateObject private var session=WelcomeSession()
    @ObservedObject var model:AppModel
    @Binding var showing:Bool
    @AppStorage("studioInterfaceMode") private var mode="simple"
    @AppStorage("animeTheme") private var theme="studio"
    @AppStorage("studioLanguage") private var language="system"
    var body:some View {
        GeometryReader {g in
            HStack(spacing:0) {
                VStack(alignment:.leading,spacing:18) {
                    HStack {AppEmblem().frame(width:32,height:32);Text("AniCanto").font(.title2.bold())}
                    Spacer(minLength:12)
                    Text(L("你嘅動畫，另一把聲音。")).font(.system(size:38,weight:.bold,design:.rounded)).fixedSize(horizontal:false,vertical:true)
                    Text(L("香港廣東話 · 普通話 · English · Just for fun")).font(.headline).foregroundStyle(.secondary)
                    if let url=Bundle.main.url(forResource:"welcome-"+theme+"-1",withExtension:"png",subdirectory:"welcome-art"),let art=NSImage(contentsOf:url) {
                        Image(nsImage:art).resizable().scaledToFit().frame(maxWidth:.infinity,maxHeight:.infinity).accessibilityLabel(L("配音助手大合照"))
                    } else {AppEmblem().frame(maxWidth:.infinity,maxHeight:.infinity)}
                    Text("SCKC / ANIME DUBBING PLAYGROUND").font(.caption.weight(.semibold)).tracking(2).foregroundStyle(.secondary)
                }.padding(36).frame(width:g.size.width*0.45).background(accent.opacity(0.09))
                ScrollView {
                    VStack(alignment:.leading,spacing:26) {
                        HStack {Spacer();StudioLanguagePicker()}
                        Text(L("歡迎返到聲演工作室")).font(.largeTitle.bold())
                        Text(L("放入動畫，揀把聲，睇角色講你嘅語言。")).font(.title3).foregroundStyle(.secondary)
                        choice("simple","基本模式","揀引擎同字幕，一按自動製作。","sparkles")
                        choice("professional","專家模式","時間線、逐句試聽、重錄與精細編輯。","slider.horizontal.3")
                        DisclosureGroup(L("本機模型與部署"),isExpanded:$session.setupExpanded) {WelcomeDeployment(model:model)}
                        Button {model.applyWelcomeLanguageDefaults(language);showing=false} label:{HStack {Text(L("進入工作室"));Spacer();Image(systemName:"arrow.right")}.padding(8)}.buttonStyle(StudioButtonStyle(prominent:true))
                        HStack {StudioHelpButton();Spacer();Button(L("關於與授權")) {model.showAbout=true}}
                        Divider();Text(L("由 SCKC 為興趣而製作，分享配音樂趣，同時探索香港廣東話文化。")).font(.callout).foregroundStyle(.secondary)
                    }.padding(44).frame(maxWidth:650)
                }.frame(maxWidth:.infinity,maxHeight:.infinity)
            }
        }.background(StudioPalette.panel)
        .onChange(of:language) {value in model.applyWelcomeLanguageDefaults(value,force:true)}
        .onAppear {session.setupExpanded = !(model.engine.runtimeReady && model.engineReady(model.ttsBackend) && model.engine.asrReady && model.engine.speechReady && model.engine.speakersReady)}
    }
    func choice(_ value:String,_ title:String,_ detail:String,_ icon:String)->some View {
        Button {mode=value} label:{HStack(spacing:16) {Image(systemName:icon).font(.title2).foregroundStyle(accent);VStack(alignment:.leading,spacing:7) {Text(L(title)).font(.title3.bold());Text(L(detail)).font(.callout).foregroundStyle(.secondary)};Spacer();Image(systemName:mode==value ? "checkmark.circle.fill":"circle").foregroundStyle(accent)}.padding(20).frame(maxWidth:.infinity,alignment:.leading).background(mode==value ? accent.opacity(0.09):Color.primary.opacity(0.025),in:RoundedRectangle(cornerRadius:14)).overlay(RoundedRectangle(cornerRadius:14).stroke(mode==value ? accent:StudioPalette.border,lineWidth:mode==value ? 2:1))}.buttonStyle(.plain)
    }
}
