import AppKit
import SwiftUI

@MainActor final class ProfessionalTerminalWindow:NSObject,NSWindowDelegate {
    private static let controller=ProfessionalTerminalWindow()
    private var window:NSWindow?
    private weak var model:AppModel?
    static func show(model:AppModel) {
        let c=controller;c.model=model
        let host=NSHostingView(rootView:TerminalLogView(model:model).environment(\.locale,appInterfaceLocale))
        if let window=c.window {window.contentView=host;window.title=L("終端機");window.makeKeyAndOrderFront(nil);return}
        let screen=(NSApp.mainWindow?.screen ?? NSScreen.main)?.visibleFrame ?? NSRect(x:0,y:0,width:1440,height:1000)
        let frame=screen.insetBy(dx:screen.width*0.05,dy:screen.height*0.05)
        let window=NSWindow(contentRect:frame,styleMask:[.titled,.closable,.resizable,.miniaturizable],backing:.buffered,defer:false)
        window.title=L("終端機");window.minSize=NSSize(width:760,height:520)
        window.isReleasedWhenClosed=false;window.delegate=c;window.contentView=host
        c.window=window;window.makeKeyAndOrderFront(nil)
    }
    static func close() {controller.window?.close()}
    func windowWillClose(_ notification:Notification) {model?.showLogs=false}
}
