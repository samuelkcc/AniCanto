import AppKit
import AVKit
import SwiftUI

// Normalized coordinates use the displayed video's top-left corner, excluding letterbox bars.
struct OCRRegion: Equatable, Codable {
    var x = 0.10
    var y = 0.78
    var width = 0.80
    var height = 0.20
    var config: [String: Double] { ["x":x, "y":y, "width":width, "height":height] }

    static func selection(from start: CGPoint, to end: CGPoint, video: CGRect) -> OCRRegion? {
        guard video.width > 0, video.height > 0, video.contains(start) else { return nil }
        let finish = CGPoint(x: min(max(end.x, video.minX), video.maxX), y: min(max(end.y, video.minY), video.maxY))
        let width = abs(finish.x-start.x), height = abs(finish.y-start.y)
        guard width >= 8, height >= 4, width/video.width >= 0.02, height/video.height >= 0.01 else { return nil }
        return OCRRegion(x: (min(start.x,finish.x)-video.minX)/video.width,
                         y: (min(start.y,finish.y)-video.minY)/video.height,
                         width: width/video.width, height: height/video.height)
    }
    func displayed(in video: CGRect) -> CGRect {
        CGRect(x: video.minX+x*video.width, y: video.minY+y*video.height, width: width*video.width, height: height*video.height)
    }
}

struct OCRSelectionPlayer: NSViewRepresentable {
    let player: CantoPlayer
    let selecting: Bool
    @Binding var region: OCRRegion
    var showsControls=true

    func makeNSView(context: Context) -> OCRPlayerContainer { OCRPlayerContainer() }
    func updateNSView(_ view: OCRPlayerContainer, context: Context) {
        if view.video.player !== player { view.video.player = player }
        view.video.showsControls=showsControls
        view.overlay.region = region
        view.overlay.selecting = selecting
        view.overlay.onSelect = { region = $0 }
        view.overlay.needsDisplay = true
        view.window?.invalidateCursorRects(for: view.overlay)
    }
}

final class OCRPlayerContainer: NSView {
    let video = VLCVideoView()
    let overlay = OCRSelectionOverlay()
    override init(frame frameRect: NSRect) {
        super.init(frame: frameRect)
        overlay.video = video
        addSubview(video)
        addSubview(overlay)
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) not supported") }
    override func layout() {
        super.layout()
        video.frame = bounds
        overlay.frame = bounds
        overlay.needsDisplay = true
    }
}

final class OCRSelectionOverlay: NSView {
    weak var video: VLCVideoView?
    var region = OCRRegion()
    var selecting = false { didSet { if !selecting { anchor = nil; draft = nil }; needsDisplay = true } }
    var onSelect: ((OCRRegion) -> Void)?
    private var anchor: CGPoint?
    private var draft: OCRRegion?
    override var isFlipped: Bool { true }
    private var videoRect: CGRect {
        guard let video else { return .zero }
        return convert(video.videoBounds, from: video).intersection(bounds)
    }
    override func hitTest(_ point: NSPoint) -> NSView? { selecting ? super.hitTest(point) : nil }
    override func resetCursorRects() {
        if selecting { addCursorRect(bounds, cursor: .crosshair) }
    }
    override func mouseDown(with event: NSEvent) {
        let point = convert(event.locationInWindow, from: nil)
        guard videoRect.contains(point) else { return }
        anchor = point; draft = nil
    }
    override func mouseDragged(with event: NSEvent) {
        guard let anchor else { return }
        draft = OCRRegion.selection(from: anchor, to: convert(event.locationInWindow, from: nil), video: videoRect)
        needsDisplay = true
    }
    override func mouseUp(with event: NSEvent) {
        guard let anchor else { return }
        if let selected = OCRRegion.selection(from: anchor, to: convert(event.locationInWindow, from: nil), video: videoRect) {
            region = selected; onSelect?(selected)
        }
        self.anchor = nil; draft = nil; needsDisplay = true
    }
    override func draw(_ dirtyRect: NSRect) {
        guard selecting, videoRect.width > 0 else { return }
        let selected = (draft ?? region).displayed(in: videoRect)
        let shade = NSBezierPath(rect: videoRect)
        shade.append(NSBezierPath(rect: selected)); shade.windingRule = .evenOdd
        NSColor.black.withAlphaComponent(0.55).setFill(); shade.fill()
        let outline = NSBezierPath(rect: selected); outline.lineWidth = 2
        NSColor.systemOrange.setStroke(); outline.stroke()
        NSColor.white.setFill()
        for point in [CGPoint(x:selected.minX,y:selected.minY),CGPoint(x:selected.maxX,y:selected.minY),CGPoint(x:selected.minX,y:selected.maxY),CGPoint(x:selected.maxX,y:selected.maxY)] {
            NSBezierPath(ovalIn: CGRect(x:point.x-3,y:point.y-3,width:6,height:6)).fill()
        }
    }
}

// Constrain the player itself to the source aspect, instead of adding wide black wings.
struct AspectPlayerFrame<Content: View>: View {
    let aspect: Double
    let maxHeight: Double
    var leftAligned=false
    @ViewBuilder var content: () -> Content
    var body: some View {
        GeometryReader { geometry in
            let ratio = aspect.isFinite && aspect > 0 ? aspect : 16.0/9.0
            let width = min(geometry.size.width, maxHeight * ratio)
            content().frame(width: width, height: width/ratio)
                .position(x: leftAligned ? width/2:geometry.size.width/2, y: maxHeight/2)
        }.frame(height: maxHeight)
    }
}
