import SwiftUI
import AppKit

struct AnimeStyle {
    let key:String
    static var current:AnimeStyle {AnimeStyle(key:UserDefaults.standard.string(forKey:"animeTheme") ?? "studio")}
    private func color(_ light:UInt32,_ dark:UInt32)->Color {
        func ns(_ hex:UInt32)->NSColor {NSColor(red:CGFloat((hex>>16)&255)/255,green:CGFloat((hex>>8)&255)/255,blue:CGFloat(hex&255)/255,alpha:1)}
        return adaptive(ns(light),ns(dark))
    }
    var background:Color {color(0xF6F6F8,0x141521)}
    var panel:Color {color(0xFFFFFF,0x202133)}
    var secondary:Color {WelcomePalette.color(key)}
    var radius:CGFloat {12}
    var icon:String {"waveform"}
    var caption:String {"STUDIO / 聲演工作室"}
    var typeface:Font.Design {.rounded}
}
struct AnimeBackdrop:View {
    var body:some View {AnimeStyle.current.background.allowsHitTesting(false).accessibilityHidden(true)}
}
struct FrameChrome:View {
    var sidebar=false
    var body:some View {AnimeStyle.current.panel.allowsHitTesting(false).accessibilityHidden(true)}
}

struct AnimeCard: ViewModifier {
    @AppStorage("animeTheme") private var key = "studio"
    func body(content: Content) -> some View {
        let style=AnimeStyle.current
        content.padding(18).frame(maxWidth:.infinity,alignment:.leading)
            .background(style.panel,in:RoundedRectangle(cornerRadius:style.radius))
            .overlay(RoundedRectangle(cornerRadius:style.radius).stroke(style.secondary.opacity(0.20),lineWidth:1))
            .overlay(alignment:.topLeading) {
                Capsule().fill(LinearGradient(colors:[accent,style.secondary],startPoint:.leading,endPoint:.trailing)).frame(width:38,height:3).padding(.leading,style.radius+8)
            }
            .shadow(color:style.secondary.opacity(0.06),radius:12,x:0,y:3)
    }
}


/// Shared game-menu identity: every page keeps the same navigation and scene language.
extension Section {
    var sceneCode:String {
        switch self {
        case .studio:return "01 / DUBBING STUDIO"
        case .batch:return "02 / EPISODE QUEUE"
        case .voices:return "03 / VOICE CAST"
        case .script:return "04 / TIMELINE EDITOR"
        case .environment:return "05 / MODEL LIBRARY"
        case .history:return "06 / COLLECTION"
        case .settings:return "07 / SYSTEM"
        case .presets:return "08 / PRODUCTION DEFAULTS"
        case .projects:return "09 / PROJECTS AND EXPORTS"
        }
    }
    var sceneHint:String {
        switch self {
        case .studio:return "揀一集動畫，開展你嘅廣東話聲演。"
        case .batch:return "排好每一集，共用設定，自動完成。"
        case .voices:return "原聲自動配對；想微調先入嚟試聽。"
        case .script:return "睇住畫面，逐句打磨對白同節奏。"
        case .environment:return "為你嘅工作室裝備合適嘅本機模型。"
        case .history:return "你嘅配音成品，隨時重溫同分享。"
        case .settings:return "佈置你嘅工作室，了解幕後製作。"
        case .presets:return "設定新影片嘅製作預設。"
        case .projects:return "管理專案同輸出成品。"
        }
    }
}
struct AppEmblem:View {
    var body:some View {
        if let url=Bundle.main.url(forResource:"AniCanto",withExtension:"icns"),let image=NSImage(contentsOf:url) {
            Image(nsImage:image).resizable().scaledToFit()
        } else {Image(systemName:"waveform.bubble.fill").resizable().scaledToFit().foregroundStyle(accent)}
    }
}

/// Code-drawn cool night scenery matches the purple palette without a warm interior image.
struct StarryStudioScene:View {
    @Environment(\.colorScheme) private var scheme
    var body:some View {
        ZStack {
            LinearGradient(colors:[Color(red:0.13,green:0.15,blue:0.32),Color(red:0.29,green:0.24,blue:0.49),Color(red:0.44,green:0.36,blue:0.62)],startPoint:.top,endPoint:.bottom)
            Canvas {ctx,size in
                for i in 0..<72 {
                    let x=Double((i*73+31)%997)/997*size.width,y=Double((i*137+89)%991)/991*size.height
                    let r=i%5==0 ? 1.5:0.7
                    ctx.fill(Path(ellipseIn:CGRect(x:x,y:y,width:r*2,height:r*2)),with:.color(.white.opacity(i%5==0 ? 0.8:0.4)))
                }
                let moon=CGRect(x:size.width*0.62,y:size.height*0.68,width:32,height:32)
                ctx.fill(Path(ellipseIn:moon.insetBy(dx:-8,dy:-8)),with:.color(.white.opacity(0.06)))
                ctx.fill(Path(ellipseIn:moon),with:.color(Color(red:0.85,green:0.83,blue:1).opacity(0.75)))
                for i in 0..<12 {
                    let width=size.width/10,height=Double((i*43+19)%70+30)
                    let rect=CGRect(x:Double(i)*width-width,y:size.height-height,width:width,height:height)
                    ctx.fill(Path(rect),with:.color(Color(red:0.12,green:0.13,blue:0.25).opacity(0.8)))
                    for floor in 0..<Int(height/12) {ctx.fill(Path(CGRect(x:rect.minX+6,y:rect.minY+8+Double(floor)*12,width:3,height:4)),with:.color(.purple.opacity(0.4)))}
                }
            }
        }.opacity(scheme == .dark ? 1:0.45).allowsHitTesting(false).accessibilityHidden(true)
    }
}
