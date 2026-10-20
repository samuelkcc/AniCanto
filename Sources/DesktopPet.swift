import AppKit
import SwiftUI

/// App-owned desktop companion. No global event tap, screen capture or inference.
enum PetGeometry {
    static func clamp(_ frame:NSRect,to screen:NSRect)->NSRect {
        var result=frame
        result.origin.x=min(max(screen.minX,frame.minX),max(screen.minX,screen.maxX-frame.width))
        result.origin.y=min(max(screen.minY,frame.minY),max(screen.minY,screen.maxY-frame.height))
        return result
    }
    static func pose(mood:CompanionMood,walking:Bool,time:Double,greeting:Bool)->Int {
        if greeting {return 4}
        if walking {return 8+Int(time*8)%4}
        switch mood {
        case .thinking,.review,.working:return 2
        case .recording:return 3
        case .success:return 7
        case .attention:return 5
        case .sleeping:return 6
        default:return time.truncatingRemainder(dividingBy:5)<0.16 ? 1:0
        }
    }
}

@MainActor enum PetArtwork {
    private static var cache:[String:[NSImage]]=[:]
    static func frames(_ theme:String)->[NSImage] {
        if let result=cache[theme] {return result}
        let key=StudioThemeChoice.all.contains {$0.id==theme} ? theme:"studio"
        guard let url=Bundle.main.url(forResource:"pet-\(key)",withExtension:"png"),
              let image=NSImage(contentsOf:url),let cg=image.cgImage(forProposedRect:nil,context:nil,hints:nil) else {return []}
        let tiles=PetAtlas.tiles(cg)
        let side=CGFloat(tiles.map {max($0.width,$0.height)}.max() ?? 1)
        let result=tiles.map {PetAtlas.frame($0,canvas:NSSize(width:side,height:side))}
        cache[theme]=result;return result
    }
}

private final class PetPanel:NSPanel {
    override var canBecomeKey:Bool {false}
    override var canBecomeMain:Bool {false}
}

@MainActor final class DesktopPet:NSObject {
    static let shared=DesktopPet()
    private(set) var panel:NSPanel?
    private var petView:DesktopPetView?
    private weak var model:AppModel?
    private var timer:Timer?
    private var observations:[NSObjectProtocol]=[]
    private var last=ProcessInfo.processInfo.systemUptime
    private var elapsed:Double=0
    private var direction:CGFloat=1
    private var greetingUntil=0.0
    private var wasBusy=false
    private var completedUntil=0.0
    private var suspended=false
    private var petSize:CGFloat=0
    private var activeTheme=""
    private var lastActivity=ProcessInfo.processInfo.systemUptime
    var dragging=false
    var isRunning:Bool {timer != nil}

    func start(model:AppModel) {
        guard self.model == nil else {refresh();return}
        self.model=model
        let nc=NotificationCenter.default
        observations.append(nc.addObserver(forName:UserDefaults.didChangeNotification,object:nil,queue:.main) {[weak self] _ in MainActor.assumeIsolated {self?.refresh()}})
        observations.append(nc.addObserver(forName:NSApplication.didChangeScreenParametersNotification,object:nil,queue:.main) {[weak self] _ in MainActor.assumeIsolated {self?.reposition()}})
        for name in [NSWorkspace.willSleepNotification,NSWorkspace.screensDidSleepNotification] {
            observations.append(NSWorkspace.shared.notificationCenter.addObserver(forName:name,object:nil,queue:.main) {[weak self] _ in MainActor.assumeIsolated {self?.suspended=true;self?.stopTimer()}})
        }
        for name in [NSWorkspace.didWakeNotification,NSWorkspace.screensDidWakeNotification] {
            observations.append(NSWorkspace.shared.notificationCenter.addObserver(forName:name,object:nil,queue:.main) {[weak self] _ in MainActor.assumeIsolated {self?.suspended=false;self?.refresh()}})
        }
        refresh()
    }
    func stop() {
        stopTimer();panel?.orderOut(nil);panel=nil;petView=nil;model=nil
        for observer in observations {NotificationCenter.default.removeObserver(observer);NSWorkspace.shared.notificationCenter.removeObserver(observer)}
        observations=[]
    }
    private func stopTimer() {timer?.invalidate();timer=nil}
    func refresh() {
        let defaults=UserDefaults.standard
        guard model != nil else {return}
        guard defaults.object(forKey:"showStudioCompanion") as? Bool ?? true else {stopTimer();panel?.orderOut(nil);return}
        let size:CGFloat=defaults.string(forKey:"studioCompanionSize")=="small" ? 180:defaults.string(forKey:"studioCompanionSize")=="medium" ? 260:330
        let theme=defaults.string(forKey:"animeTheme") ?? "studio"
        if panel == nil {
            let p=PetPanel(contentRect:NSRect(x:0,y:0,width:size,height:size),styleMask:[.borderless,.nonactivatingPanel],backing:.buffered,defer:false)
            p.backgroundColor = .clear;p.isOpaque=false;p.hasShadow=false;p.level = .floating
            p.hidesOnDeactivate=false;p.isReleasedWhenClosed=false;p.isExcludedFromWindowsMenu=true
            p.collectionBehavior=[.canJoinAllSpaces,.fullScreenAuxiliary,.ignoresCycle]
            p.title=L("桌面夥伴")
            let view=DesktopPetView(frame:p.contentView!.bounds);view.owner=self;p.contentView=view
            panel=p;petView=view;petSize=size;activeTheme=theme
            view.setFrames(PetArtwork.frames(theme));reposition(reset:true)
        }
        if petSize != size {petSize=size;panel?.setContentSize(NSSize(width:size,height:size));reposition()}
        if activeTheme != theme {activeTheme=theme;petView?.setFrames(PetArtwork.frames(theme))}
        panel?.orderFrontRegardless()
        guard !suspended else {return}
        if timer == nil {
            last=ProcessInfo.processInfo.systemUptime
            let t=Timer(timeInterval:1.0/15,repeats:true) {[weak self] _ in self?.tick()}
            RunLoop.main.add(t,forMode:.common);timer=t
        }
        tick()
    }
    func reposition(reset:Bool=false) {
        guard let panel,let screen=(reset ? NSScreen.main:panel.screen) ?? NSScreen.main else {return}
        var frame=panel.frame
        if reset {frame.origin=CGPoint(x:screen.visibleFrame.maxX-frame.width-32,y:screen.visibleFrame.minY+8)}
        panel.setFrame(PetGeometry.clamp(frame,to:screen.visibleFrame),display:true)
    }
    func greet() {
        lastActivity=ProcessInfo.processInfo.systemUptime
        if let model,model.error != nil || model.batchNeedsAttention || model.projectEditor.studioIssues.contains(where:{!$0.repaired}) {showEditor();model.projectEditor.workspacePage="review"}
        else {greetingUntil=lastActivity+2.5}
    }
    private func tick() {
        guard let panel,let view=petView,let model else {return}
        let now=ProcessInfo.processInfo.systemUptime,dt=min(0.15,max(0,now-last));last=now
        let defaults=UserDefaults.standard
        let animated=(defaults.object(forKey:"companionMotion") as? Bool ?? true) && !NSWorkspace.shared.accessibilityDisplayShouldReduceMotion
        if animated {elapsed+=dt}
        if wasBusy != model.busy {lastActivity=now}
        let issues=model.projectEditor.studioIssues
        let failed=model.error != nil || (!model.busy && (!model.projectEditor.failedTracks.isEmpty || issues.contains {$0.title=="生成失敗" && !$0.repaired}))
        let review=model.batchNeedsAttention || (!model.busy && issues.contains {!$0.repaired})
        if wasBusy && !model.busy && !failed && !review && model.stage=="完成" {completedUntil=now+5}
        wasBusy=model.busy
        let mood=review && !model.busy && !failed ? CompanionMood.review:CompanionMood.resolve(busy:model.busy,stage:model.stage,error:failed,idle:now-lastActivity,completed:now<completedUntil ? 0:nil,greeting:false)
        let walking=animated && !dragging && now>greetingUntil && !model.busy && mood == .idle && (defaults.object(forKey:"desktopPetRoaming") as? Bool ?? true) && elapsed.truncatingRemainder(dividingBy:22)>12
        if walking,let screen=panel.screen ?? NSScreen.main {
            var next=panel.frame;next.origin.x+=direction*dt*32
            if next.minX<screen.visibleFrame.minX || next.maxX>screen.visibleFrame.maxX {direction *= -1}
            panel.setFrame(PetGeometry.clamp(next,to:screen.visibleFrame),display:false)
        }
        view.update(pose:PetGeometry.pose(mood:mood,walking:walking,time:animated ? elapsed:1,greeting:animated && now<greetingUntil),flipped:walking && direction<0,time:elapsed,motion:animated,busy:model.busy)
        view.toolTip=L(mood.caption)+" · "+L("拖曳移動，按右鍵設定")
        // Transparent pixels must not block clicks on the editor or other apps.
        if !dragging {
            let point=view.convert(panel.convertPoint(fromScreen:NSEvent.mouseLocation),from:nil)
            panel.ignoresMouseEvents = !view.containsArtwork(point)
        }
    }
    func move(to origin:NSPoint) {
        guard let panel else {return}
        let screen=NSScreen.screens.first {$0.frame.contains(NSEvent.mouseLocation)} ?? panel.screen ?? NSScreen.main
        if let screen {panel.setFrame(PetGeometry.clamp(NSRect(origin:origin,size:panel.frame.size),to:screen.visibleFrame),display:true)}
    }
    @objc func toggleRoaming() {let d=UserDefaults.standard;d.set(!(d.object(forKey:"desktopPetRoaming") as? Bool ?? true),forKey:"desktopPetRoaming")}
    @objc func toggleMotion() {let d=UserDefaults.standard;d.set(!(d.object(forKey:"companionMotion") as? Bool ?? true),forKey:"companionMotion")}
    @objc func hidePet() {UserDefaults.standard.set(false,forKey:"showStudioCompanion");refresh()}
    @objc func showEditor() {model?.section = .studio;NSApp.activate(ignoringOtherApps:true);NSApp.windows.first {!($0 is NSPanel) && $0.isVisible}?.makeKeyAndOrderFront(nil)}
    @objc func resetPosition() {reposition(reset:true)}
}

@MainActor final class DesktopPetView:NSView {
    weak var owner:DesktopPet?
    private var frames:[NSImage]=[]
    private var masks:[NSBitmapImageRep]=[]
    private var pose=0,mirrored=false
    private var animationTime=0.0,animated=false,working=false
    private var mouseStart=NSPoint.zero,windowStart=NSPoint.zero
    private var moved=false
    override var isOpaque:Bool {false}
    override var acceptsFirstResponder:Bool {false}
    override func acceptsFirstMouse(for event:NSEvent?)->Bool {true}
    func setFrames(_ values:[NSImage]) {
        frames=values;masks=values.compactMap {$0.cgImage(forProposedRect:nil,context:nil,hints:nil).map(NSBitmapImageRep.init(cgImage:))};needsDisplay=true
        setAccessibilityElement(true);setAccessibilityRole(.button);setAccessibilityLabel(L("桌面夥伴"));setAccessibilityHelp(L("拖曳移動，按右鍵設定"))
    }
    func update(pose:Int,flipped:Bool,time:Double=0,motion:Bool=false,busy:Bool=false) {
        let changed=self.pose != pose || mirrored != flipped || animated != motion
        self.pose=pose;mirrored=flipped;animationTime=time;animated=motion;working=busy
        if changed || motion {needsDisplay=true}
    }
    private var artworkRect:NSRect {bounds.insetBy(dx:8,dy:8)}
    func containsArtwork(_ point:NSPoint)->Bool {
        guard artworkRect.contains(point),masks.indices.contains(pose) else {return false}
        let mask=masks[pose],u=(point.x-artworkRect.minX)/artworkRect.width,v=(point.y-artworkRect.minY)/artworkRect.height
        let x=min(mask.pixelsWide-1,max(0,Int((mirrored ? 1-u:u)*CGFloat(mask.pixelsWide))))
        let y=min(mask.pixelsHigh-1,max(0,Int((1-v)*CGFloat(mask.pixelsHigh))))
        return (mask.colorAt(x:x,y:y)?.alphaComponent ?? 0)>0.15
    }
    override func draw(_ dirtyRect:NSRect) {
        NSColor.clear.setFill();bounds.fill(using:.copy)
        guard frames.indices.contains(pose),let ctx=NSGraphicsContext.current?.cgContext else {return}
        ctx.saveGState();defer {ctx.restoreGState()}
        if mirrored {ctx.translateBy(x:bounds.width,y:0);ctx.scaleBy(x:-1,y:1)}
        if animated {
            ctx.translateBy(x:bounds.midX,y:artworkRect.minY)
            ctx.rotate(by:sin(animationTime*(working ? 1.8:0.8))*0.007)
            ctx.scaleBy(x:1,y:1+sin(animationTime*1.5)*0.006)
            ctx.translateBy(x:-bounds.midX,y:-artworkRect.minY)
        }
        frames[pose].draw(in:artworkRect,from:.zero,operation:.sourceOver,fraction:1)
    }
    override func mouseDown(with event:NSEvent) {owner?.dragging=true;mouseStart=NSEvent.mouseLocation;windowStart=window?.frame.origin ?? .zero;moved=false}
    override func mouseDragged(with event:NSEvent) {let point=NSEvent.mouseLocation;moved=moved || hypot(point.x-mouseStart.x,point.y-mouseStart.y)>3;owner?.move(to:NSPoint(x:windowStart.x+point.x-mouseStart.x,y:windowStart.y+point.y-mouseStart.y))}
    override func mouseUp(with event:NSEvent) {owner?.dragging=false;if !moved {owner?.greet()}}
    override func accessibilityPerformPress()->Bool {owner?.greet();return true}
    override func menu(for event:NSEvent)->NSMenu? {
        let menu=NSMenu()
        for (title,selector) in [("返回剪輯器",#selector(DesktopPet.showEditor)),("開啟／暫停走動",#selector(DesktopPet.toggleRoaming)),("開啟／暫停動畫",#selector(DesktopPet.toggleMotion)),("移回螢幕角落",#selector(DesktopPet.resetPosition)),("隱藏桌面夥伴",#selector(DesktopPet.hidePet))] {
            let item=NSMenuItem(title:L(title),action:selector,keyEquivalent:"");item.target=owner;menu.addItem(item)
        }
        return menu
    }
}
