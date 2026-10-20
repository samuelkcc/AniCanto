import SwiftUI
import AppKit
final class DockDragState:ObservableObject {var previous=0.0}
struct StudioDockDivider:View {
    var vertical=false
    var label:String
    var adjust:(Double)->Void
    @StateObject private var drag=DockDragState()
    var body:some View {
        Rectangle().fill(Color.primary.opacity(0.10))
            .frame(width:vertical ? nil:6,height:vertical ? 6:nil)
            .contentShape(Rectangle())
            .gesture(DragGesture(minimumDistance:0).onChanged {value in
                let next=vertical ? value.translation.height:value.translation.width
                adjust(next-drag.previous);drag.previous=next
            }.onEnded {_ in drag.previous=0})
            .onHover {inside in if inside {(vertical ? NSCursor.resizeUpDown:NSCursor.resizeLeftRight).push()} else {NSCursor.pop()}}
            .accessibilityLabel(L(label)).accessibilityAdjustableAction {direction in adjust(direction == .increment ? 15:-15)}
    }
}
