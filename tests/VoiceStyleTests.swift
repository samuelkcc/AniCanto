import SwiftUI
import AppKit
import Foundation

@main struct VoiceStyleTests {
    @MainActor static func main() throws {
        NSApplication.shared.setActivationPolicy(.prohibited)
        let root=URL(fileURLWithPath:ProcessInfo.processInfo.environment["SAM_CANTO_DATA"]!)
        try FileManager.default.createDirectory(at:root,withIntermediateDirectories:true)
        let qa=URL(fileURLWithPath:FileManager.default.currentDirectoryPath).appendingPathComponent(".build/qa237")
        let model=AppModel();model.busy=true
        precondition(model.voiceStyleMode=="natural")
        var values=WorkflowValues(model);values.voiceStyleMode="clone";values.apply(to:model,editor:false)
        precondition(model.voiceStyleMode=="clone")
        values.voiceStyleMode=nil;values.apply(to:model,editor:false);precondition(model.voiceStyleMode=="natural")
        precondition(NaturalVoiceChoice.all.count==7)
        let editor=model.projectEditor;editor.configure(root:root);editor.readOnlyPreview=true
        editor.config=["voiceStyleMode":"natural","roleAnalysisMode":"independent","video":qa.appendingPathComponent("test-clock.mp4").path]
        let reference=NaturalVoiceChoice.all.first {$0.id=="yue-low"}!
        editor.profiles=[VoiceProfile(id:"role",name:"第 1 句原聲",reference:reference.path,promptText:"Japanese",naturalVoices:["yue":"yue-low","en":"en-bright"],identityStatus:"independent")]
        editor.document=EditDocument(review:root.appendingPathComponent("review.json").path,segments:[EditSegment(id:"one",sources:[0],start:2,end:3,captionStart:2,captionEnd:3,text:"我哋一齊慢慢講清楚呢件事。",original:"原聲",speakerId:"role")],clips:[EditClip(start:0,end:18)],voiceStyleMode:"natural")
        editor.selectedSegment="one";editor.duration=18
        precondition(editor.naturalReference(editor.profiles[0],engine:"gpt-sovits",language:"yue")==reference.path)
        precondition(editor.naturalReference(editor.profiles[0],engine:"gpt-sovits",language:"en")==NaturalVoiceChoice.all.first {$0.id=="en-bright"}?.path)
        let encoded=try JSONEncoder().encode(editor.profiles[0]);let decoded=try JSONDecoder().decode(VoiceProfile.self,from:encoded)
        precondition(decoded.naturalVoices==editor.profiles[0].naturalVoices)
        // Exercise real VLC seeking backwards before a short context audition.
        editor.player.volume=0;editor.playSource();RunLoop.main.run(until:Date().addingTimeInterval(2))
        editor.seek(13);editor.player.play();RunLoop.main.run(until:Date().addingTimeInterval(0.5))
        editor.playSegment(context:true)
        precondition(editor.loopStart==1.5 && editor.stopAt==3.75)
        RunLoop.main.run(until:Date().addingTimeInterval(0.7))
        precondition(editor.seconds<5,"Stale pre-seek clock leaked into the short audition")
        editor.player.pause()
        func snapshot<V:View>(_ view:V,name:String,width:Double,height:Double) throws {
            let host=NSHostingView(rootView:view.frame(width:width,height:height).background(Color.white).foregroundStyle(Color.black).environment(\.colorScheme,.light))
            host.frame=NSRect(x:0,y:0,width:width,height:height)
            let window=NSWindow(contentRect:host.frame,styleMask:[.borderless],backing:.buffered,defer:false);window.contentView=host
            host.layoutSubtreeIfNeeded();RunLoop.main.run(until:Date().addingTimeInterval(0.5));host.layoutSubtreeIfNeeded()
            if let image=host.bitmapImageRepForCachingDisplay(in:host.bounds) {host.cacheDisplay(in:host.bounds,to:image);try image.representation(using:.png,properties:[:])!.write(to:qa.appendingPathComponent(name+".png"))}
            window.close()
        }
        try snapshot(VoiceStyleControls(mode:.constant("natural")).padding(20),name:"voice-style-natural",width:510,height:220)
        try snapshot(VoiceStyleControls(mode:.constant("clone")).padding(20),name:"voice-style-clone",width:510,height:220)
        try snapshot(RoleManager(model:model,editor:editor,close:{},fullscreen:{}),name:"natural-reference-ui",width:1100,height:720)
        print("PASS: default natural, setting migration, independent Cantonese/English casting choices, profile persistence and real backward seek/context audition; native UI rendered.")
    }
}
