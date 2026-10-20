import SwiftUI
import AppKit

/// Deterministic UI companion. No model calls, microphones or background services.
enum CompanionMood:String,CaseIterable {
    case idle,download,thinking,working,recording,success,attention,sleeping,review
    var frame:Int {
        switch self {case .idle,.download:return 0;case .thinking,.review:return 2;case .working:return 3;case .recording:return 4;case .success:return 5;case .attention:return 6;case .sleeping:return 7}
    }
    var caption:String {
        switch self {
        case .idle:return "準備好，一齊開工。"
        case .download:return "模型下載中，陪你等。"
        case .thinking:return "等我睇清楚啲對白…"
        case .working:return "努力製作中…"
        case .recording:return "投入配音中…"
        case .success:return "完成喇，辛苦晒！"
        case .attention:return "有啲嘢需要你睇睇。"
        case .sleeping:return "休息一陣…叫我就得。"
        case .review:return "份稿等緊你過目。"
        }
    }
    var icon:String {
        switch self {case .idle:return "sparkles";case .download:return "arrow.down.circle";case .thinking:return "text.book.closed";case .working:return "gearshape.2";case .recording:return "waveform";case .success:return "checkmark.seal";case .attention:return "exclamationmark.bubble";case .sleeping:return "moon.zzz";case .review:return "doc.text.magnifyingglass"}
    }
    static func resolve(busy:Bool,stage:String,error:Bool,idle:TimeInterval,completed:TimeInterval?,greeting:Bool)->Self {
        if error {return .attention}
        if busy {
            if stage.contains("下載") || stage.contains("部署") {return .download}
            if stage.contains("翻譯") || stage.contains("改稿") || stage.contains("辨識") || stage.contains("分析") || stage.contains("字幕") {return .thinking}
            if stage.contains("配音") || stage.contains("試聽") {return .recording}
            return .working
        }
        if stage.contains("批准") || stage.contains("校稿") {return .review}
        if greeting || (completed.map {$0 < 8} ?? false) {return .success}
        return idle >= 90 ? .sleeping:.idle
    }
}
@MainActor final class CompanionActivity:ObservableObject {
    @Published var touched=Date()
    @Published var completed:Date?
    @Published var greetingUntil=Date.distantPast
    @Published var active=NSApp.isActive
    private var monitor:Any?
    private var observers:[NSObjectProtocol]=[]
    func start() {
        guard monitor == nil else {return}
        monitor=NSEvent.addLocalMonitorForEvents(matching:[.keyDown,.leftMouseDown,.rightMouseDown,.scrollWheel,.mouseMoved]) { [weak self] event in
            if let self,Date().timeIntervalSince(self.touched)>1 {self.touched=Date()}
            return event
        }
        let nc=NotificationCenter.default
        for name in [NSApplication.didBecomeActiveNotification,NSApplication.didResignActiveNotification,NSWindow.didChangeOcclusionStateNotification] {
            observers.append(nc.addObserver(forName:name,object:nil,queue:.main) { [weak self] _ in
                MainActor.assumeIsolated { self?.active=NSApp.isActive && NSApp.windows.contains {$0.occlusionState.contains(.visible)} }
            })
        }
    }
    func stop() {if let monitor {NSEvent.removeMonitor(monitor)};monitor=nil;observers.forEach(NotificationCenter.default.removeObserver);observers=[]}
    func greet() {touched=Date();greetingUntil=Date().addingTimeInterval(2.5)}
}
@MainActor enum CompanionArtwork {
    private static var key=""
    private static var frames:[NSImage]=[]
    static func image(theme:String,index:Int)->NSImage? {
        let theme=["studio","energy","ocean","ninja","retro","forest","future"].contains(theme) ? theme:"studio"
        if key != theme || frames.isEmpty {
            guard let url=Bundle.main.url(forResource:"companion-\(theme)",withExtension:"png"),let source=NSImage(contentsOf:url),let cg=source.cgImage(forProposedRect:nil,context:nil,hints:nil) else {return nil}
            frames=decode(cg)
            key=theme
        }
        return frames.indices.contains(index) ? frames[index]:nil
    }
    private static func decode(_ cg:CGImage)->[NSImage] {
        let width=cg.width,height=cg.height,w=width/4,h=height/2
        let space=CGColorSpaceCreateDeviceRGB()
        guard let pixels=CGContext(data:nil,width:width,height:height,bitsPerComponent:8,bytesPerRow:width*4,space:space,bitmapInfo:CGImageAlphaInfo.premultipliedLast.rawValue),let data=pixels.data else {return []}
        pixels.draw(cg,in:CGRect(x:0,y:0,width:width,height:height))
        let bytes=data.assumingMemoryBound(to:UInt8.self)
        func alpha(_ x:Int,_ y:Int)->UInt8 {bytes[(y*width+x)*4+3]}
        var regions:[CGRect]=[]
        for row in 0..<2 {
            let y0=row*h,y1=row == 1 ? height:(row+1)*h
            var cuts=[0]
            // Generated atlases may place a transparent gutter off the nominal grid.
            for col in 1..<4 {
                let nominal=col*w
                var cut=nominal,best=Int.max
                for x in (nominal-w/5)...(nominal+w/5) {
                    var score=abs(x-nominal)
                    for y in y0..<y1 {if alpha(x,y)>20 {score+=1000}}
                    if score<best {best=score;cut=x}
                }
                cuts.append(cut)
            }
            cuts.append(width)
            for col in 0..<4 {
                var left=cuts[col+1],right=cuts[col],top=y1,bottom=y0
                for y in y0..<y1 {for x in cuts[col]..<cuts[col+1] where alpha(x,y)>20 {
                    left=min(left,x);right=max(right,x);top=min(top,y);bottom=max(bottom,y)
                }}
                guard right>=left,bottom>=top else {return []}
                left=max(cuts[col],left-2);right=min(cuts[col+1]-1,right+2)
                top=max(y0,top-2);bottom=min(y1-1,bottom+2)
                regions.append(CGRect(x:left,y:top,width:right-left+1,height:bottom-top+1))
            }
        }
        let scale=min(448/(regions.map(\.width).max() ?? 448),896/(regions.map(\.height).max() ?? 896))
        return regions.compactMap {rect in
            guard let tile=cg.cropping(to:rect),let canvas=CGContext(data:nil,width:512,height:1024,bitsPerComponent:8,bytesPerRow:512*4,space:space,bitmapInfo:CGImageAlphaInfo.premultipliedLast.rawValue) else {return nil}
            let size=CGSize(width:rect.width*scale,height:rect.height*scale)
            canvas.interpolationQuality = .high
            canvas.draw(tile,in:CGRect(x:(512-size.width)/2,y:48,width:size.width,height:size.height))
            guard let image=canvas.makeImage() else {return nil}
            return NSImage(cgImage:image,size:NSSize(width:512,height:1024))
        }
    }
}
struct StudioCompanion:View {
    @ObservedObject var model:AppModel
    @StateObject private var activity=CompanionActivity()
    @AppStorage("animeTheme") private var theme="studio"
    @AppStorage("companionMotion") private var motion=true
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.colorScheme) private var scheme
    // Fixed dates are used by the isolated QA harness, never the production workflow.
    var previewMood:CompanionMood?=nil
    var previewTime:TimeInterval?=nil
    private var animated:Bool {motion && !reduceMotion && activity.active}
    var body:some View {
        TimelineView(.periodic(from:.now,by:1)) { clock in
            let mood=previewMood ?? CompanionMood.resolve(busy:model.busy,stage:model.stage,error:model.error != nil,idle:clock.date.timeIntervalSince(activity.touched),completed:activity.completed.map {clock.date.timeIntervalSince($0)},greeting:clock.date<activity.greetingUntil)
            GeometryReader { proxy in
                VStack(spacing:0) {
                    ZStack(alignment:.bottom) {
                        Ellipse().fill(RadialGradient(colors:[accent.opacity(0.22),.clear],center:.center,startRadius:5,endRadius:100)).frame(height:70)
                        Group {
                            if animated {
                                RigPortrait(theme:theme,mood:mood,moving:true,time:previewTime)
                            } else if let image=CompanionArtwork.image(theme:theme,index:mood.frame) {
                                // A static image keeps the character visible while the GPU scene sleeps.
                                Image(nsImage:image).resizable().scaledToFit().scaleEffect(x:theme == "studio" ? -1:1,y:1)
                            }
                        }.aspectRatio(0.5,contentMode:.fit)
                            .allowsHitTesting(false).accessibilityHidden(true)
                        if mood == .sleeping {Text("z Z").font(.system(size:18,weight:.medium,design:.rounded)).foregroundStyle(accent.opacity(0.65)).offset(x:65,y:-max(50,proxy.size.height*0.65)).accessibilityHidden(true)}
                    }.frame(height:max(60,proxy.size.height-42))
                    Label(L(mood.caption),systemImage:mood.icon)
                        .font(.system(size:12,weight:.medium,design:.rounded)).multilineTextAlignment(.center)
                        .padding(.horizontal,8).padding(.vertical,7).frame(maxWidth:.infinity)
                        .background(surface.opacity(0.9),in:RoundedRectangle(cornerRadius:10))
                        .overlay(RoundedRectangle(cornerRadius:10).stroke(accent.opacity(0.18)))
                        .foregroundStyle(mood == .attention ? Color.orange:ink)
                }.contentShape(Rectangle()).onTapGesture {activity.greet()}
                    .accessibilityElement(children:.ignore).accessibilityLabel(Text(L(mood.caption)))
                    .accessibilityAddTraits(.isButton).accessibilityAction {activity.greet()}.help(L("同角色打個招呼"))
            }
        }.onAppear {activity.start()}.onDisappear {activity.stop()}
        .onChange(of:model.busy) { before,after in
            activity.touched=Date()
            if before && !after && model.error == nil && model.stage == "完成" {activity.completed=Date()}
            if after {activity.completed=nil}
        }
    }
}
