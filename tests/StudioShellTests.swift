import SwiftUI
import AppKit

/// Native integration checks: route without extra windows and preserve saved work.
struct StudioShellTests {
    @MainActor static func run(_ model:AppModel) throws {
        let a=try JSONSerialization.data(withJSONObject:["video":"episode-a.mkv","ttsBackend":"drama3","dubLanguages":["yue"]])
        let b=try JSONSerialization.data(withJSONObject:["video":"stale.mkv","videos":[["video":"episode-b.mkv"],["video":"episode-c.mkv"]],"ttsBackend":"gpt-sovits","dubLanguages":["yue","en"]])
        let rows=StudioQueuedVideo.rows([b],active:a)
        precondition(rows.map(\.video)==["episode-a.mkv","episode-b.mkv","episode-c.mkv"])
        precondition(rows.map(\.active)==[true,false,false])
        precondition(rows[2].languages==["yue","en"])
        precondition(StudioQueuedVideo.rows([Data("invalid".utf8)],active:nil).isEmpty)
        let originalRequests=model.pendingBatchRequests
        model.pendingBatchRequests=[a,b];model.queuePaused=true
        let originalMode=UserDefaults.standard.string(forKey:"studioInterfaceMode") ?? "simple"
        UserDefaults.standard.set("professional",forKey:"studioInterfaceMode")
        let host=NSHostingView(rootView:ContentView(welcomeInitiallyVisible:false).environmentObject(model))
        host.frame=NSRect(x:0,y:0,width:1440,height:940)
        let window=NSWindow(contentRect:host.frame,styleMask:[.borderless],backing:.buffered,defer:false)
        window.contentView=host;host.layoutSubtreeIfNeeded()
        RunLoop.main.run(until:Date().addingTimeInterval(0.2))
        let count=NSApp.windows.count
        model.showWorkspaceSettings=true
        RunLoop.main.run(until:Date().addingTimeInterval(0.3))
        precondition(model.section == .presets && !model.showWorkspaceSettings)
        precondition(NSApp.windows.count==count,"Production defaults stay in the main window")
        model.showProjectManager=true
        RunLoop.main.run(until:Date().addingTimeInterval(0.3))
        precondition(model.section == .projects && !model.showProjectManager)
        precondition(NSApp.windows.count==count,"Project management stays in the main window")
        ProfessionalSettingsWindow.show(model:model,category:"models")
        RunLoop.main.run(until:Date().addingTimeInterval(0.3))
        precondition(model.section == .presets && model.setupCategory=="models")
        precondition(model.pendingBatchRequests==[a,b] && model.queuePaused,"Navigation must not rewrite or start saved jobs")
        window.contentView=nil
        model.pendingBatchRequests=originalRequests;model.section = .studio
        UserDefaults.standard.set(originalMode,forKey:"studioInterfaceMode")
        for theme in StudioThemeChoice.all where theme.id != "ensemble" {
            precondition(PetArtwork.frames(theme.id).count==12,"Missing theme assistant poses: "+theme.id)
        }
        print("PASS unified routes create no extra windows, saved requests stay frozen, mixed video queue projection, all nine theme assistants")
    }
}

struct FastProductionModeTests {
    @MainActor static func run(_ model:AppModel) throws {
        let normal:[String:Any] = ["productionMode":"standard","aiAutoFix":true,"roleAnalysisMode":"audiovisual","autoValidate":true]
        var fast=normal;fast["productionMode"]="fast"
        let cfg=ProductionModePolicy.applying(to:fast)
        precondition(cfg["aiAutoFix"] as? Bool == false && cfg["roleAnalysisMode"] as? String == "independent")
        var restored=cfg;restored["productionMode"]="standard"
        restored=ProductionModePolicy.applying(to:restored)
        precondition(restored["aiAutoFix"] as? Bool == true && restored["roleAnalysisMode"] as? String == "audiovisual")
        var plan=SimpleProductionPlan(engine:"drama3");plan.productionMode="fast"
        precondition(plan.settings()["productionMode"] as? String == "fast")
        precondition(plan.settings()["requireCompleteDubbing"] as? Bool == false)
        let mode=model.productionMode,requests=model.pendingBatchRequests
        model.setWorkspaceProductionMode("fast")
        precondition(model.workspaceProductionMode=="fast")
        let config=model.conversionConfig(URL(fileURLWithPath:"/tmp/fast-fixture.mp4"),start:0)
        precondition(config["productionMode"] as? String == "fast" && config["roleAnalysisMode"] as? String == "independent")
        model.pendingBatchRequests=[try JSONSerialization.data(withJSONObject:config)]
        model.setWorkspaceProductionMode("standard")
        precondition(model.workspaceProductionMode=="standard")
        precondition(model.submittedVoiceSelection(video:"/tmp/fast-fixture.mp4")?.productionMode=="fast")
        let preset=StudioPreset(model),copy=try JSONDecoder().decode(StudioPreset.self,from:JSONEncoder().encode(preset))
        precondition(copy.productionMode=="standard")
        model.productionMode=mode;model.pendingBatchRequests=requests
        print("PASS fast mode policy, shared selection, immutable queue and preset roundtrip")
    }
}


struct WelcomeDefaultTests {
    @MainActor static func run(_ model:AppModel) throws {
        let frozen=model.pendingBatchRequests,old=model.dubMode,sub=model.subtitleOutput,original=model.includeOriginal,burn=model.burnOutputCaptions
        let defaults=UserDefaults.standard,marker=defaults.object(forKey:"welcomeEnglishDefaults.v1"),simple=defaults.object(forKey:"simpleSubtitleModes")
        defaults.removeObject(forKey:"welcomeEnglishDefaults.v1")
        model.applyWelcomeLanguageDefaults("en")
        precondition(model.dubMode=="both" && model.includeOriginal && model.subtitleOutput=="separate" && !model.burnOutputCaptions)
        precondition(defaults.string(forKey:"simpleSubtitleModes")=="yue,english" && model.pendingBatchRequests==frozen)
        model.dubMode="yue";model.applyWelcomeLanguageDefaults("en")
        precondition(model.dubMode=="yue","Returning to Welcome keeps later explicit production choices")
        model.dubMode=old;model.subtitleOutput=sub;model.includeOriginal=original;model.burnOutputCaptions=burn
        if let marker {defaults.set(marker,forKey:"welcomeEnglishDefaults.v1")} else {defaults.removeObject(forKey:"welcomeEnglishDefaults.v1")}
        if let simple {defaults.set(simple,forKey:"simpleSubtitleModes")} else {defaults.removeObject(forKey:"simpleSubtitleModes")}
        print("PASS English welcome bilingual audio and soft subtitle defaults; frozen requests and later explicit choices preserved")
    }
}
