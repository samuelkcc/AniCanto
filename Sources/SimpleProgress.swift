import SwiftUI
import AppKit

struct SimpleLanguageSelector:View {
    @Binding var selection:String
    var cantoneseOnly=false
    var body:some View {
        HStack(spacing:16) {
            Text(L("配音語言")).font(.headline)
            Picker(L("配音語言"),selection:$selection) {
                Text(L("廣東話")).tag("yue")
                Text(L("英文")).tag("en").disabled(cantoneseOnly)
                Text(L("雙語")).tag("both").disabled(cantoneseOnly)
            }.pickerStyle(.segmented).labelsHidden().frame(maxWidth:430)
            Spacer(minLength:0)
        }.padding(.horizontal,18).padding(.vertical,12)
            .background(StudioPalette.panel,in:RoundedRectangle(cornerRadius:12))
    }
}

struct SimpleProgressStatus {
    let title:String
    let detail:String
    init(stage:String,detail:String,busy:Bool,paused:Bool,error:String?,languages:[String]=["yue"],exported:Bool=false,needsReview:Bool=false) {
        self.detail=localizedProgressDetail(error ?? detail)
        if paused {title=L("已暫停並保存");return}
        if !busy {title=exported ? (needsReview ? (L("成品已輸出")+" · "+L("待覆核")):L("成品已輸出")):error != nil ? L("製作未完成"):stage=="完成" ? L("成品已輸出"):L("準備好，開始你嘅配音");return}
        let languageTitle=languages==["en"] ? L("英文"):languages.contains("en") ? L("香港廣東話同英文"):L("廣東話")
        let steps:[([String],String)]=[
            (["輸出驗證","解碼驗證"],"正在檢查最終影片同音軌"),
            (["合成","封裝","輸出","mux","export"],"正在合成影片同可切換音軌"),
            (["角色卡後備"],"正在用角色卡後備聲線補配音"),
            (["核對","覆聽","驗證","檢查","校對","check","verify"],"正在檢查配音內容同完整度"),
            (["混音","音量","背景音效"],"正在調整配音同背景音量"),
            (["分離","separat"],"正在分離日文人聲同背景音樂"),
            (["角色","聲紋","人物","speaker"],"正在整理角色同參考聲線"),
            (["翻譯","場景","口語","台詞","改稿","字幕補稿","字幕對齊"],String(format:L("正在翻譯及整理%@台詞"),languageTitle)),
            (["字幕","辨識","日語","聽寫","ocr","asr"],"正在辨識日文對白同原片字幕"),
            (["配音","生成","錄音","voice","synthes"],String(format:L("正在生成%@配音"),languageTitle))]
        title=steps.first(where:{$0.0.contains(where:{stage.localizedCaseInsensitiveContains($0)})}).map{L($0.1)} ?? localizedProgressDetail(stage.isEmpty ? "正在準備影片":stage)
    }
}

/// Reuse the actual theme assistant and its authored walking poses.
struct ThemeProgressAssistant:View {
    @AppStorage("animeTheme") private var theme="studio"
    var frame:Int
    var completed:Bool
    var size:CGFloat=80
    var body:some View {
        let frames=PetArtwork.frames(theme=="ensemble" ? "studio":theme)
        Group {
            if !frames.isEmpty {Image(nsImage:frames[min(frames.count-1,completed ? 7:frame)]).resizable().scaledToFit()}
            else {AppEmblem()}
        }.frame(width:size,height:size)
    }
}

struct ClayProgressTrack:View {
    var value:Double?
    var running:Bool
    var reduceMotion=false
    var completed=false
    var compact=false
    var body:some View {
        TimelineView(.animation(minimumInterval:0.10,paused:!running || reduceMotion)) {context in
            GeometryReader {g in
                let distance=max(0,g.size.width-(compact ? 66:82))
                // An unknown percentage stays at the start; motion never
                // fabricates numerical progress or reaches the finish early.
                let position=distance*CGFloat(value ?? 0)
                let frame=running && !reduceMotion ? 8+Int(context.date.timeIntervalSinceReferenceDate*8)%4:0
                ZStack(alignment:.leading) {
                    Capsule().fill(accent.opacity(0.12)).frame(height:10).offset(y:19)
                    Capsule().fill(LinearGradient(colors:[accent,.teal],startPoint:.leading,endPoint:.trailing))
                        .frame(width:max(8,(g.size.width-20)*CGFloat(value ?? 0)),height:10).offset(y:19)
                    Image(systemName:completed ? "flag.checkered.circle.fill":"flag.checkered")
                        .font(.system(size:23)).foregroundStyle(completed ? Color.teal:accent.opacity(0.6))
                        .frame(maxWidth:.infinity,alignment:.trailing).offset(y:-1)
                    ThemeProgressAssistant(frame:frame,completed:completed,size:compact ? 64:80).offset(x:position,y:-6)
                }.frame(maxHeight:.infinity)
            }
        }.frame(height:compact ? 52:88).accessibilityHidden(true)
    }
}
