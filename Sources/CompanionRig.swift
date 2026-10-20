import SwiftUI
import AppKit

/// A continuous 2D mesh: head, arms and legs have separate, overlapping influence
/// regions. Smooth falloffs keep joints connected without cutting the illustration.
enum CompanionMesh {
    static let columns=16,rows=28
    static let source:[SIMD2<Float>]=(0...rows).flatMap {y in (0...columns).map {x in SIMD2(Float(x)/Float(columns),Float(y)/Float(rows))}}
    static func smooth(_ a:Float,_ b:Float,_ x:Float)->Float {let t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)}
    static func band(_ a:Float,_ b:Float,_ c:Float,_ d:Float,_ x:Float)->Float {smooth(a,b,x)*(1-smooth(c,d,x))}
    static func destination(time:Double,mood:CompanionMood)->[SIMD2<Float>] {
        let t=Float(time)
        let effort:Float=mood == .working || mood == .recording ? 1.4:1
        let sleepy=mood == .sleeping
        func rotate(_ p:SIMD2<Float>,_ pivot:SIMD2<Float>,_ angle:Float)->SIMD2<Float> {
            let q=p-pivot
            // Cells are twice as tall as wide; rotate in physical rather than UV space.
            return SIMD2(q.x*cos(angle)-q.y*2*sin(angle),q.x*0.5*sin(angle)+q.y*cos(angle))+pivot-p
        }
        return source.map {p in
            let x=p.x,y=p.y
            let edge=band(0,0.12,0.88,1,x)
            let head=smooth(0.71,0.83,y)*edge
            let headAngle:Float=sin(t*(sleepy ? 0.7:1.15))*0.025+(sleepy ? 0.02:0)
            var delta=rotate(p,SIMD2(0.5,0.74),headAngle)*head
            let upper=band(0.40,0.52,0.70,0.82,y)
            let leftArm=band(0.02,0.17,0.34,0.49,x)*upper
            let rightArm=band(0.51,0.66,0.83,0.98,x)*upper
            delta += rotate(p,SIMD2(0.35,0.73),sin(t*1.75)*0.045*effort)*leftArm
            delta += rotate(p,SIMD2(0.65,0.73),sin(t*1.4+1.1)*(-0.04)*effort)*rightArm
            let lower=band(0.01,0.10,0.39,0.49,y)
            let leftLeg=band(0.04,0.24,0.44,0.53,x)*lower
            let rightLeg=band(0.47,0.56,0.76,0.96,x)*lower
            delta += rotate(p,SIMD2(0.44,0.45),sin(t*0.85)*0.018)*leftLeg
            delta += rotate(p,SIMD2(0.56,0.45),sin(t*0.85+2)*(-0.018))*rightLeg
            let chest=band(0.40,0.53,0.76,0.88,y)*edge
            delta.y += sin(t*(sleepy ? 1:1.65))*0.0035*chest
            return p+delta
        }
    }
}
/// AppKit draws on the main run loop. No SpriteKit display-link queue survives
/// removal of a SwiftUI sidebar, theme switch or application deactivation.
@MainActor final class CompanionCanvas:NSView {
    var theme="studio",mood=CompanionMood.idle,moving=false,fixedTime:Double?
    private var timer:Timer?
    private(set) var updates=0
    var animating:Bool {timer != nil}
    func configure(theme:String,mood:CompanionMood,moving:Bool,time:Double?) {
        self.theme=theme;self.mood=mood;self.moving=moving;fixedTime=time
        updateTimer();needsDisplay=true
    }
    override func viewDidMoveToWindow() {super.viewDidMoveToWindow();updateTimer()}
    private func updateTimer() {
        let active=moving && fixedTime==nil && window != nil
        if active && timer==nil {
            let t=Timer(timeInterval:1.0/15,repeats:true) {[weak self] _ in self?.needsDisplay=true}
            RunLoop.main.add(t,forMode:.common);timer=t
        } else if !active {stopAnimation()}
    }
    func stopAnimation() {timer?.invalidate();timer=nil}
    override func draw(_ dirtyRect:NSRect) {
        super.draw(dirtyRect)
        let time=fixedTime ?? (moving ? ProcessInfo.processInfo.systemUptime:0)
        let blink=moving && mood == .idle && time.truncatingRemainder(dividingBy:6.2)>6.02
        guard let image=CompanionArtwork.image(theme:theme,index:blink ? 1:mood.frame),let ctx=NSGraphicsContext.current?.cgContext else{return}
        let width=min(max(1,bounds.width-12),max(1,bounds.height-12)*0.5)
        let breathing=moving ? sin(time*1.65)*0.0035:0
        let tilt=moving ? sin(time*1.15)*0.018:0
        ctx.saveGState();defer {ctx.restoreGState()}
        ctx.translateBy(x:bounds.midX,y:6)
        ctx.rotate(by:tilt)
        ctx.scaleBy(x:theme=="studio" ? -1:1,y:1+breathing)
        image.draw(in:NSRect(x:-width/2,y:0,width:width,height:width*2),from:.zero,operation:.sourceOver,fraction:1)
        updates+=1
    }
    deinit {timer?.invalidate()}
}
struct RigPortrait:NSViewRepresentable {
    var theme:String,mood:CompanionMood,moving:Bool,time:Double?
    func makeNSView(context:Context)->CompanionCanvas {
        let view=CompanionCanvas();view.configure(theme:theme,mood:mood,moving:moving,time:time);return view
    }
    func updateNSView(_ view:CompanionCanvas,context:Context) {view.configure(theme:theme,mood:mood,moving:moving,time:time)}
    static func dismantleNSView(_ view:CompanionCanvas,coordinator:()) {view.stopAnimation()}
}
