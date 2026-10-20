import SwiftUI

struct StudioToolbarIcon:View {
    let name:String
    var body:some View {Image(systemName:name).font(.system(size:15,weight:.medium)).frame(width:18,height:18)}
}

struct StudioAppBar:View {
    @ObservedObject var model:AppModel
    var basic:Bool
    @AppStorage("navigationExpanded") private var navigationExpanded=true
    var body:some View {
        HStack(spacing:12) {
            HStack(spacing:8) {AppEmblem().frame(width:24,height:24);Text("AniCanto").font(.system(size:17,weight:.bold,design:.rounded))}
            Spacer(minLength:12)
            if basic && ![.studio,.batch,.history,.script].contains(model.section) {
                Button {model.section = .studio} label:{Label(L("返回工作區"),systemImage:"arrow.left")}
            }
            HStack(spacing:6) {
                if !basic {
                    StudioEditorActions(model:model,editor:model.projectEditor)
                    StudioLayoutControls(options:model.workspaceOptions)
                    Divider().frame(height:20).padding(.horizontal,4)
                }
                StudioInterfaceSwitch()
                Button {NotificationCenter.default.post(name:Notification.Name("AniCantoTutorial"),object:nil)} label:{StudioToolbarIcon(name:"questionmark.circle")}.help(L("使用教學")).accessibilityLabel(L("使用教學"))
                Button {model.showAbout=true} label:{StudioToolbarIcon(name:"info.circle")}.help(L("關於與授權")).accessibilityLabel(L("關於與授權"))
                Button {NotificationCenter.default.post(name:Notification.Name("AniCantoWelcome"),object:nil)} label:{StudioToolbarIcon(name:"house")}.help(L("返回歡迎畫面")).accessibilityLabel(L("返回歡迎畫面"))
                if !basic {
                    Divider().frame(height:20).padding(.horizontal,4)
                    if model.busy || model.hasSavedWork {ProcessingQueueButton(model:model,iconOnly:true)}
                    StudioExportAction(model:model,editor:model.projectEditor)
                }
            }
        }.padding(.horizontal,20).frame(height:58).background(StudioPalette.panel)
    }
}

/// Independent switches remain reachable even when every panel is hidden.
struct StudioLayoutControls:View {
    @ObservedObject var options:ProjectWorkspaceOptions
    @AppStorage("navigationExpanded") private var navigationExpanded=true
    var body:some View {
        HStack(spacing:4) {
            control("工作選單","sidebar.left",$navigationExpanded)
            control("專案庫","rectangle.lefthalf.inset.filled",$options.showBrowser)
            control("檢查器","sidebar.right",$options.showInspector)
            Menu {
                Button(L("重設面板配置")) {options.showBrowser=true;options.showInspector=true;navigationExpanded=true;options.browserWidth=220;options.inspectorWidth=350;options.timelineHeight=0;options.transcriptHeight=240;options.focusPreview=false;options.layoutRevision+=1}
                Button(L(options.focusPreview ? "返回剪輯配置":"放大預覽")) {options.focusPreview.toggle()}
                Button(L("全螢幕")) {NSApp.keyWindow?.toggleFullScreen(nil)}
            } label:{StudioToolbarIcon(name:"rectangle.3.group")}
            .menuIndicator(.hidden).help(L("佈局")).accessibilityLabel(L("佈局"))
        }.accessibilityElement(children:.contain).accessibilityLabel(L("佈局"))
    }
    func control(_ title:String,_ icon:String,_ binding:Binding<Bool>)->some View {
        Button {binding.wrappedValue.toggle();options.focusPreview=false} label:{StudioToolbarIcon(name:icon).foregroundStyle(binding.wrappedValue ? accent:Color.secondary)}
            .help(L(title)).accessibilityLabel(L(title)).accessibilityValue(L(binding.wrappedValue ? "顯示":"隱藏"))
    }
}

struct StudioEditorActions:View {
    @ObservedObject var model:AppModel
    @ObservedObject var editor:ProjectEditor
    private var visible:Bool {[.studio,.batch,.history,.script].contains(model.section) && editor.workspacePage=="edit"}
    var body:some View {
        if visible {
            Button(action:editor.undo) {StudioToolbarIcon(name:"arrow.uturn.backward")}.help(L("撤銷")).accessibilityLabel(L("撤銷")).disabled(editor.undoStack.isEmpty).keyboardShortcut("z")
            Button(action:editor.redo) {StudioToolbarIcon(name:"arrow.uturn.forward")}.help(L("重做")).accessibilityLabel(L("重做")).disabled(editor.redoStack.isEmpty).keyboardShortcut("z",modifiers:[.command,.shift])
            Button {do {try editor.save()} catch {editor.error=error.localizedDescription}} label:{StudioToolbarIcon(name:"square.and.arrow.down")}.help(L("儲存")).accessibilityLabel(L("儲存")).disabled(editor.document==nil || editor.readOnlyPreview).keyboardShortcut("s")
        }
    }
}

struct StudioExportAction:View {
    @ObservedObject var model:AppModel
    @ObservedObject var editor:ProjectEditor
    var body:some View {
        if [.studio,.batch,.history,.script].contains(model.section) {
            Button {editor.workspacePage="produce"} label:{HStack(spacing:6) {StudioToolbarIcon(name:"film.stack");Text(L("匯出影片")).lineLimit(1)}.fixedSize()}
                .buttonStyle(StudioButtonStyle(prominent:true)).disabled(editor.document==nil)
                .help(L("匯出影片")).accessibilityLabel(L("匯出影片"))
        }
    }
}
