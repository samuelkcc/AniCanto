import SwiftUI
import AppKit
import Foundation

@main struct VoiceModeTests {
    @MainActor static func main() throws {
        NSApplication.shared.setActivationPolicy(.prohibited)
        let root=URL(fileURLWithPath:ProcessInfo.processInfo.environment["SAM_CANTO_DATA"]!)
        let project=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
        let qa=project.appendingPathComponent(".build/qa236")
        let model=AppModel();model.busy=true
        precondition(model.roleAnalysisMode=="audiovisual")
        var values=WorkflowValues(model);values.roleAnalysisMode="independent";values.apply(to:model,editor:false)
        precondition(model.roleAnalysisMode=="independent")
        precondition(JourneyStep.matching("逐句聲音配對")==JourneyStep.subtitles)
        let editor=model.projectEditor;editor.configure(root:root)
        let reference=project.appendingPathComponent(".build/qa234/role3-continuous-ja.wav").path
        editor.config=["roleAnalysisMode":"independent"]
        editor.profiles=[VoiceProfile(id:"line-one",name:"第 1 句原聲",reference:reference,promptText:"こんにちは",shortReference:true,identityStatus:"independent"),VoiceProfile(id:"line-two",name:"第 2 句原聲",reference:reference,promptText:"ありがとう",identityStatus:"independent")]
        editor.readOnlyPreview=true
        editor.document=EditDocument(review:root.appendingPathComponent("fixture-review.json").path,segments:[EditSegment(id:"one",sources:[0],start:1,end:3,captionStart:1,captionEnd:3,text:"咁樣嘅話，我哋會全力配合你哋！",original:"こんにちは",speakerId:"line-one"),EditSegment(id:"two",sources:[1],start:3,end:5,captionStart:3,captionEnd:5,text:"唔該晒你。",original:"ありがとう",speakerId:"line-two")],clips:[EditClip(start:0,end:6)])
        editor.selectedSegment="one"
        precondition(editor.isIndependentVoiceMapping && editor.voiceManagerTitle=="逐句配音參考")
        precondition(editor.profiles.allSatisfy {$0.avatar==nil})
        func snapshot<V:View>(_ view:V,name:String,width:Double,height:Double) throws {
            let host=NSHostingView(rootView:view.frame(width:width,height:height).background(Color.white).foregroundStyle(Color.black).environment(\.colorScheme,.light))
            host.frame=NSRect(x:0,y:0,width:width,height:height)
            let window=NSWindow(contentRect:host.frame,styleMask:[.borderless],backing:.buffered,defer:false);window.contentView=host
            host.layoutSubtreeIfNeeded();RunLoop.main.run(until:Date().addingTimeInterval(0.5));host.layoutSubtreeIfNeeded()
            if let image=host.bitmapImageRepForCachingDisplay(in:host.bounds) {host.cacheDisplay(in:host.bounds,to:image);if let bytes=image.representation(using:.png,properties:[:]) {try bytes.write(to:qa.appendingPathComponent(name+".png"))}}
            window.close()
        }
        try snapshot(RoleManager(model:model,editor:editor,close:{},fullscreen:{}),name:"independent-reference-ui",width:1100,height:680)
        for mode in ["audiovisual","independent"] {
            model.roleAnalysisMode=mode
            try snapshot(RoleAnalysisControls(model:model).padding(20),name:"analysis-choice-"+mode,width:460,height:280)
        }
        print("PASS: character cards default; per-line mode survives settings snapshots; reference UI is independent and image-free; two native option layouts rendered.")
    }
}
