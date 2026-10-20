import SwiftUI
import AppKit

/// Uses the existing virtualized SwiftUI scroll view; never allocates a full-film canvas.
@MainActor final class TimelineNavigation:ObservableObject {
    weak var scroll:NSScrollView?
    var panOrigin:Double?
    var pointerOrigin:Double?
    var onUserScroll:(()->Void)?
    private var observer:NSObjectProtocol?
    func attach(_ view:NSView) {
        guard let found=view.enclosingScrollView else{return}
        if scroll !== found {
            if let observer {NotificationCenter.default.removeObserver(observer)}
            observer=NotificationCenter.default.addObserver(forName:NSScrollView.willStartLiveScrollNotification,object:found,queue:.main) {[weak self] _ in
                Task {@MainActor in self?.onUserScroll?()}
            }
        }
        scroll=found;found.hasHorizontalScroller=true;found.scrollerStyle = .legacy
        found.horizontalScroller?.controlSize = .regular
    }
    deinit {if let observer {NotificationCenter.default.removeObserver(observer)}}
    func move(to proposed:Double) {
        guard let scroll,let document=scroll.documentView else{return}
        let clip=scroll.contentView
        let maximum=max(0,document.bounds.width-clip.bounds.width)
        clip.scroll(to:NSPoint(x:min(maximum,max(0,proposed)),y:clip.bounds.origin.y))
        scroll.reflectScrolledClipView(clip)
    }
    func reveal(time:Double,duration:Double,width:Double,force:Bool=false) {
        guard let scroll else{return}
        let x=max(0,min(duration,time))/max(1,duration)*width
        let bounds=scroll.contentView.bounds
        if force || x<bounds.minX+40 || x>bounds.maxX-80 {move(to:x-bounds.width*0.35)}
    }
    func pan() {
        guard let scroll else{return}
        if panOrigin==nil {panOrigin=scroll.contentView.bounds.minX;pointerOrigin=NSEvent.mouseLocation.x}
        move(to:(panOrigin ?? 0)-(NSEvent.mouseLocation.x-(pointerOrigin ?? 0)))
    }
    func endPan() {panOrigin=nil;pointerOrigin=nil}
}
struct TimelineScrollProbe:NSViewRepresentable {
    var navigation:TimelineNavigation
    func makeNSView(context:Context)->NSView {NSView(frame:.zero)}
    func updateNSView(_ view:NSView,context:Context) {DispatchQueue.main.async {navigation.attach(view)}}
}
