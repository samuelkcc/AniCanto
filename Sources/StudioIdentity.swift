import SwiftUI
import AppKit

struct StudioThemeChoice:Identifiable {
    let id:String
    let title:String
    static let all:[Self] = [
        .init(id:"studio",title:"紫髮音控"),.init(id:"energy",title:"橙髮音控"),
        .init(id:"ocean",title:"海軍音控"),.init(id:"ninja",title:"夜行斥候"),
        .init(id:"retro",title:"復古主播"),.init(id:"forest",title:"森林錄音師"),.init(id:"future",title:"未來發明家"),
        .init(id:"mint",title:"薄荷節拍"),.init(id:"moonflower",title:"月下花語"),.init(id:"ensemble",title:"配音同樂會")
    ]
    /// Restore the requested purple identity once; subsequent choices persist.
    static func restoreDefaultIfNeeded(_ defaults:UserDefaults = .standard) {
        guard !defaults.bool(forKey:"restoredStudioIdentity201") else {return}
        defaults.set("studio",forKey:"animeTheme")
        defaults.set("dark",forKey:"studioTheme")
        defaults.set(false,forKey:"randomAnimeTheme")
        defaults.set(true,forKey:"showStudioCompanion")
        defaults.set(true,forKey:"restoredStudioIdentity201")
    }
}

struct StudioThemeMenu:View {
    @AppStorage("studioLanguage") private var language="system"
    @AppStorage("animeTheme") private var theme="studio"
    @AppStorage("studioTheme") private var appearance="system"
    @AppStorage("showStudioCompanion") private var companion=true
    @AppStorage("companionMotion") private var motion=true
    @AppStorage("desktopPetRoaming") private var roaming=true
    @AppStorage("randomAnimeTheme") private var random=false
    @AppStorage("studioCompanionSize") private var companionSize="large"
    var body:some View {
        Menu {
            Picker(L("選擇助手"),selection:$theme) {ForEach(StudioThemeChoice.all) {Text(L($0.title)).tag($0.id)}}
            Divider()
            Toggle(L("顯示動畫助手"),isOn:$companion)
            Toggle(L("角色動態效果"),isOn:$motion)
            Toggle(L("桌面自由走動"),isOn:$roaming)
            Button(L("移回螢幕角落")) {DesktopPet.shared.resetPosition()}
            Picker(L("助手大小"),selection:$companionSize) {Text(L("細")).tag("small");Text(L("標準")).tag("medium");Text(L("大")).tag("large")}
            Button(L("還原預設助手")) {theme="studio";random=false}
        } label:{Image(systemName:"pawprint")}
        .id(language).help(L("桌面助手")).accessibilityLabel(L("桌面助手"))
    }
}

/// The companion lives on the desktop; legacy layout call sites consume no space.
struct CompanionDock:View {
    @ObservedObject var model:AppModel
    var maximumHeight:CGFloat?=nil
    var body:some View {EmptyView()}
}

enum SavedVoiceLibrary {
    static func ids(_ storage:String)->Set<String> {Set(storage.split(separator:",").map(String.init))}
    static func updating(_ storage:String,id:String,saved:Bool)->String {
        var values=ids(storage)
        if saved {values.insert(id)} else {values.remove(id)}
        return values.sorted().joined(separator:",")
    }
}
