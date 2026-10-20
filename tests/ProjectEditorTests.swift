import SwiftUI
import AppKit
import AVKit
import Foundation

@main struct ProjectEditorTests {
    @MainActor static func main() throws {
        let app=NSApplication.shared
        app.setActivationPolicy(.prohibited)
        let root=URL(fileURLWithPath:ProcessInfo.processInfo.environment["SAM_CANTO_DATA"]!)
        let project=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
        let source=project.appendingPathComponent(".build/editor-media-check/source.mp4")
        let reference=project.appendingPathComponent(".build/editor-render-check/reference.wav")
        try FileManager.default.createDirectory(at:root.appendingPathComponent("jobs"),withIntermediateDirectories:true)
        for name in ["one","two"] {
            let job=root.appendingPathComponent("jobs/"+name);try FileManager.default.createDirectory(at:job,withIntermediateDirectories:true)
            let cue:[String:Any]=["start":1.0,"end":3.0,"text":"原聲辨識測試","cantonese":"你好，今日一齊去冒險。","speakerId":"role"]
            let cfg:[String:Any]=["video":source.path,"duration":8.0,"startOffset":0.0,"ttsBackend":"cosyvoice3","voiceProfiles":[["id":"role","name":"主角","reference":reference.path,"promptText":"こんにちは","language":"ja"]]]
            try JSONSerialization.data(withJSONObject:["config":cfg,"cues":[cue],"meta":["streams":[]],"status":"pending"]).write(to:job.appendingPathComponent("review.json"))
        }
        let model=AppModel();model.busy=true
        let editor=model.projectEditor;editor.refresh(model)
        precondition(editor.projects.count==2)
        let first=editor.projects[0],second=editor.projects[1]
        editor.open(first);let original=editor.document!
        editor.updateSegment {$0.text="修改稿一"}
        editor.open(second);precondition(editor.document!.segments[0].text=="你好，今日一齊去冒險。")
        editor.open(first);precondition(editor.document!.segments[0].text=="修改稿一")
        // A background event for another movie cannot change the selected editor.
        model.receive(WorkerEvent(stage:"校稿",message:"background",review:second.review!.path))
        precondition(editor.document!.review==first.review!.path && editor.document!.segments[0].text=="修改稿一")
        editor.updateSegment {$0.text="你好世界"};editor.seconds=2;editor.splitAt=2;editor.splitSegment()
        precondition(editor.document!.segments.count==2)
        precondition(editor.document!.segments.map(\.text)==["你好","世界"])
        editor.undo();precondition(editor.document!.segments.count==1)
        editor.redo();precondition(editor.document!.segments.count==2)
        editor.selectedSegment=editor.document!.segments[0].id;editor.mergeNext();precondition(editor.document!.segments[0].text=="你好世界")
        editor.seconds=4;editor.bladeClip();precondition(editor.document!.clips.count==2)
        editor.undo();precondition(editor.document!.clips.count==1)
        let ownReference=root.appendingPathComponent("own-qwen.wav")
        try Data(contentsOf:reference).write(to:ownReference)
        editor.profiles[0].engineReferences=["qwen-tts:yue":EngineVoiceReference(reference:ownReference.path,promptText:"獨立錄音",enabled:true)]
        precondition(editor.profiles[0].referenceFor("qwen-tts","yue")==ownReference.path)
        precondition(editor.profiles[0].referenceFor("gpt-sovits","yue")==editor.profiles[0].reference)
        model.submitEditor();precondition(model.editorTasks.count==1 && model.editorTasks[0].status=="queued")
        let submitted=try Data(contentsOf:URL(fileURLWithPath:model.editorTasks[0].submission))
        let submittedObject=try JSONSerialization.jsonObject(with:submitted) as! [String:Any]
        let submittedProfiles=(submittedObject["settings"] as! [String:Any])["voiceProfiles"] as! [[String:Any]]
        let submittedOwn=(submittedProfiles[0]["engineReferences"] as! [String:[String:Any]])["qwen-tts:yue"]!
        let frozenOwn=submittedOwn["reference"] as! String
        precondition(frozenOwn != ownReference.path && frozenOwn.contains("editor-references"))
        let frozenBytes=try Data(contentsOf:URL(fileURLWithPath:frozenOwn))
        let originalOwnBytes=try Data(contentsOf:ownReference)
        precondition(frozenBytes==originalOwnBytes && submittedOwn["promptText"] as? String == "獨立錄音")
        editor.updateSegment {$0.text="提交後再修改"};try editor.save()
        let after=try Data(contentsOf:URL(fileURLWithPath:model.editorTasks[0].submission));precondition(after==submitted)
        model.submitEditor();precondition(model.editorTasks[0].status=="superseded" && model.editorTasks[1].status=="queued")
        let reloaded=AppModel();precondition(reloaded.editorTasks.count==2)
        precondition(editor.document!.review==original.review)
        model.section = .history
        let view=ProjectWorkspace(model:model,editor:editor).frame(width:1220,height:1100).padding(20).background(Color.white)
        let host=NSHostingView(rootView:view);host.frame=NSRect(x:0,y:0,width:1260,height:1140)
        let window=NSWindow(contentRect:host.frame,styleMask:[.borderless],backing:.buffered,defer:false)
        window.contentView=host;window.layoutIfNeeded();host.layoutSubtreeIfNeeded()
        RunLoop.main.run(until:Date().addingTimeInterval(1))
        if let rep=host.bitmapImageRepForCachingDisplay(in:host.bounds) {
            host.cacheDisplay(in:host.bounds,to:rep)
            try rep.representation(using:.png,properties:[:])!.write(to:project.appendingPathComponent(".build/editor-workspace.png"))
        }
        editor.player.pause();editor.audio.pause();reloaded.projectEditor.player.pause()
        print("PASS: independent projects, switch autosave, background isolation, split/merge, undo/redo, clip blade, immutable submissions, queue supersession and restart persistence")
    }
}
