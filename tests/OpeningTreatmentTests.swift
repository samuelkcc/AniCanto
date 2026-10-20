import SwiftUI
import AppKit

@main struct OpeningTreatmentTests {
    @MainActor static func main() throws {
        NSApplication.shared.setActivationPolicy(.prohibited)
        let qa=URL(fileURLWithPath:FileManager.default.currentDirectoryPath+"/.build/qa259")
        precondition(ProcessInfo.processInfo.environment["SAM_CANTO_DATA"]==qa.appendingPathComponent("native-data").path)
        let model=AppModel()
        model.autoSkipOP=true;model.translateOPED=true
        let values=WorkflowValues(model)
        let saved=try JSONEncoder().encode(values)
        let restored=try JSONDecoder().decode(WorkflowValues.self,from:saved)
        model.translateOPED=false;restored.apply(to:model,editor:false)
        precondition(model.autoSkipOP && model.translateOPED)
        var legacy=try JSONSerialization.jsonObject(with:saved) as! [String:Any]
        legacy.removeValue(forKey:"translateOPED")
        let old=try JSONDecoder().decode(WorkflowValues.self,from:JSONSerialization.data(withJSONObject:legacy))
        old.apply(to:model,editor:false)
        precondition(model.autoSkipOP && !model.translateOPED,"Old presets keep Japanese treatment")
        model.translateOPED=true
        let frozen=model.conversionConfig(URL(fileURLWithPath:"/tmp/episode.mkv"),start:0)
        precondition(frozen["translateOPED"] as? Bool==true && frozen["autoSkipOP"] as? Bool==true)
        model.translateOPED=false
        precondition(frozen["translateOPED"] as? Bool==true,"Submitted configuration stays immutable")
        let plan=SimpleProductionPlan(engine:"cosyvoice3",autoSkipOP:true,translateOPED:true)
        try plan.validate()
        precondition(plan.settings()["translateOPED"] as? Bool==true)
        let preset=try JSONDecoder().decode(StudioPreset.self,from:JSONEncoder().encode(StudioPreset(model)))
        preset.apply(model);precondition(!model.translateOPED)
        for mode in ["preserve","translate","off"] {
            var detect=true,translate=false
            let controls=OpeningTreatmentControls(detect:Binding(get:{detect},set:{detect=$0}),translate:Binding(get:{translate},set:{translate=$0}))
            controls.selection.wrappedValue=mode
            precondition(controls.selection.wrappedValue==mode)
            precondition(detect==(mode != "off") && translate==(mode=="translate"))
            let host=NSHostingView(rootView:controls.padding(18).frame(width:350,height:165).background(Color.white).foregroundStyle(Color.black).environment(\.colorScheme,.light))
            host.frame=NSRect(x:0,y:0,width:350,height:165)
            let window=NSWindow(contentRect:host.frame,styleMask:[.borderless],backing:.buffered,defer:false)
            window.contentView=host;host.layoutSubtreeIfNeeded();RunLoop.main.run(until:Date().addingTimeInterval(0.2));host.layoutSubtreeIfNeeded()
            if let image=host.bitmapImageRepForCachingDisplay(in:host.bounds) {
                host.cacheDisplay(in:host.bounds,to:image)
                if let bytes=image.representation(using:.png,properties:[:]) {try bytes.write(to:qa.appendingPathComponent("opening-"+mode+".png"))}
            }
            window.close()
        }
        print("PASS OP/ED control modes, old/new presets, simple/pro configuration and frozen settings; native controls rendered")
    }
}
