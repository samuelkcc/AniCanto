import SwiftUI

struct StudioNavigation:View {
    @AppStorage("studioLanguage") private var interfaceLanguage="system"
    @ObservedObject var model:AppModel
    @ObservedObject var editor:ProjectEditor
    private var inWorkspace:Bool {[.studio,.batch,.history,.script].contains(model.section)}
    var body:some View {
        VStack(alignment:.leading,spacing:10) {
            ScrollView {
                VStack(alignment:.leading,spacing:6) {
                    Button(action:model.chooseBatch) {Image(systemName:"plus").font(.title2).frame(maxWidth:.infinity)}.help(L("匯入影片")).disabled(model.busy).keyboardShortcut("o").padding(.bottom,12)
                    EmptyView()
                    ForEach([(id:"edit",title:"剪輯",icon:"slider.horizontal.below.rectangle"),(id:"roles",title:"角色",icon:"person.3"),(id:"review",title:"校對報告",icon:"checklist"),(id:"produce",title:"製作匯出",icon:"square.and.arrow.up"),(id:"queue",title:"工作佇列",icon:"list.bullet.rectangle"),(id:"terminal",title:"終端機",icon:"terminal")],id:\.id) {page in
                        entry(page.title,page.icon,active:inWorkspace && editor.workspacePage==page.id) {
                            model.section = .studio
                            if page.id=="roles" {RoleManagerWindow.present(model:model,editor:editor)}
                            else {editor.workspacePage=page.id}
                        }.disabled(!["edit","queue","terminal"].contains(page.id) && editor.document==nil)
                    }
                    Divider().padding(.vertical,12)
                    EmptyView()
                    entry("製作預設","slider.horizontal.3",active:model.section == .presets) {model.section = .presets}
                    entry("模型中心","shippingbox",active:model.section == .environment) {model.section = .environment}
                    entry("偏好設定","gearshape",active:model.section == .settings) {model.section = .settings}
                    entry("專案／成品管理","folder",active:model.section == .projects) {model.section = .projects}
                }
            }
            Divider()
            Text("v"+(Bundle.main.object(forInfoDictionaryKey:"CFBundleShortVersionString") as? String ?? "—")).font(.caption).foregroundStyle(.secondary)
        }.padding(8).frame(width:94).background(StudioPalette.panel)
    }
    private func entry(_ title:String,_ icon:String,active:Bool=false,action:@escaping ()->Void)->some View {
        Button(action:action) {
            VStack(spacing:6) {Image(systemName:icon).font(.system(size:19));Text(L(title)).font(.system(size:10,weight:active ? .semibold:.regular)).lineLimit(2).multilineTextAlignment(.center)}
                .frame(maxWidth:.infinity,minHeight:58).foregroundStyle(active ? accent:Color.secondary)
                .background(active ? accent.opacity(0.10):Color.clear,in:RoundedRectangle(cornerRadius:10))
                .overlay(alignment:.leading) {if active {Capsule().fill(accent).frame(width:3,height:24)}}
        }.buttonStyle(.plain).help(L(title)).accessibilityLabel(L(title))
    }
}
