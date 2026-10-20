import SwiftUI
import AppKit
import Foundation

@main struct ProductionWorkflowTests {
    @MainActor static func main() throws {
        NSApplication.shared.setActivationPolicy(.prohibited)
        let project=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
        let qa=project.appendingPathComponent(".build/qa235")
        let root=URL(fileURLWithPath:ProcessInfo.processInfo.environment["SAM_CANTO_DATA"]!)
        let job=root.appendingPathComponent("jobs/production-test")
        try FileManager.default.createDirectory(at:job,withIntermediateDirectories:true)
        func write(_ value:Any,_ url:URL) throws {try JSONSerialization.data(withJSONObject:value,options:[.prettyPrinted,.sortedKeys]).write(to:url,options:.atomic)}
        let reference=project.appendingPathComponent(".build/editor-render-check/reference.wav")
        let video=project.appendingPathComponent(".build/editor-media-check/source.mp4")
        let cue:[String:Any]=["start":1.0,"end":3.0,"subtitleStart":0.9,"subtitleEnd":3.2,"text":"原聲原文","cantonese":"咁樣嘅話，我哋會全力配合你哋！","english":"The approved English line.","speakerId":"role"]
        let cfg:[String:Any]=["video":video.path,"duration":8.0,"model":"local","ttsBackend":"gpt-sovits","selectedEngines":["gpt-sovits"],"dubLanguages":["yue"],"subtitleOutput":"yue","cantonesePronunciationText":"話 = waa6","voiceProfiles":[["id":"role","name":"主角","reference":reference.path,"promptText":"こんにちは","language":"ja"]]]
        let review=job.appendingPathComponent("review.json")
        try write(["config":cfg,"cues":[cue],"meta":["streams":[]],"status":"pending"],review)
        let originalBytes=try Data(contentsOf:review)
        let model=AppModel();model.busy=true
        let editor=model.projectEditor;editor.refresh(model);editor.open(editor.projects.first {$0.review==review}!)
        let original=editor.document!
        editor.profiles=[] // Subtitle work must not depend on a voice card.
        model.submitEditor(audioSettings:["subtitlesOnly":true,"scriptLanguages":["en"],"scriptRevisionMode":"all"])
        precondition(editor.error==nil && model.editorTasks.count==1)
        let task=model.editorTasks[0],submission=URL(fileURLWithPath:task.submission)
        let object=try JSONSerialization.jsonObject(with:Data(contentsOf:submission)) as! [String:Any]
        let settings=object["settings"] as! [String:Any]
        precondition((settings["voiceProfiles"] as! [Any]).isEmpty && settings["cantonesePronunciationText"] as? String=="話 = waa6")
        let folder=job.appendingPathComponent("versions/"+task.id);try FileManager.default.createDirectory(at:folder,withIntermediateDirectories:true)
        var proposal=try JSONDecoder().decode(EditDocument.self,from:Data(contentsOf:submission))
        proposal.segments[0].english="New reviewed English."
        try JSONEncoder().encode(proposal).write(to:folder.appendingPathComponent("subtitle-draft.json"))
        try write(["id":task.id,"status":"script-ready","created":"2026-10-13T10:00:00Z","submission":submission.path,"scriptLanguages":["en"]],folder.appendingPathComponent("version.json"))
        editor.loadVersions();let version=editor.scriptVersions[0]
        editor.updateSegment {$0.text="保留後來修改嘅廣東話。"}
        try editor.applySubtitleProposal(version)
        precondition(editor.scriptVersions.isEmpty)
        precondition(editor.document!.segments[0].text=="保留後來修改嘅廣東話。")
        precondition(editor.document!.segments[0].english=="New reviewed English." && editor.document!.subtitleOutput=="separate")
        precondition(editor.document!.segments[0].start==original.segments[0].start && editor.document!.segments[0].captionEnd==original.segments[0].captionEnd && editor.document!.segments[0].speakerId=="role")
        editor.undo();precondition(editor.document!.segments[0].english==original.segments[0].english)
        editor.updateSegment {$0.english="Manual English edit."}
        do {try editor.applySubtitleProposal(version);fatalError("Stale proposal replaced a newer English edit")} catch {}
        precondition(editor.document!.segments[0].english=="Manual English edit.")
        // A newly added engine/language must become visible without editing the base review.
        let rendered=job.appendingPathComponent("versions/new-audio");let track=rendered.appendingPathComponent("tracks/en-cosy")
        try FileManager.default.createDirectory(at:track,withIntermediateDirectories:true)
        let audio=track.appendingPathComponent("new.wav");try FileManager.default.copyItem(at:reference,to:audio)
        let segment=editor.document!.segments[0]
        let oldTrack=job.appendingPathComponent("tracks/old-en-cosy");try FileManager.default.createDirectory(at:oldTrack,withIntermediateDirectories:true)
        let oldAudio=oldTrack.appendingPathComponent("old.wav");try FileManager.default.copyItem(at:reference,to:oldAudio)
        try write(["tracks":[["engine":"cosyvoice3","language":"en","report":oldTrack.appendingPathComponent("report.json").path]]],job.appendingPathComponent("report.json"))
        try write(["config":["ttsBackend":"cosyvoice3","targetLanguage":"en"],"cues":[["start":segment.start,"end":segment.end,"cantonese":segment.english!,"english":segment.english!,"speakerId":"role"]]],oldTrack.appendingPathComponent("review.json"))
        try write([["start":segment.start,"end":segment.end,"renderedAudio":oldAudio.path,"renderedSeconds":2.0]],oldTrack.appendingPathComponent("timing.json"))
        try write(["id":"new-audio","created":"2026-10-13T11:00:00Z","status":"complete"],rendered.appendingPathComponent("version.json"))
        try write(["tracks":[["engine":"cosyvoice3","language":"en","report":track.appendingPathComponent("report.json").path]]],rendered.appendingPathComponent("report.json"))
        try write(["config":["ttsBackend":"cosyvoice3","targetLanguage":"en"],"cues":[["start":segment.start,"end":segment.end,"cantonese":segment.english!,"english":segment.english!,"speakerId":"role"]]],track.appendingPathComponent("review.json"))
        try write([["start":segment.start,"end":segment.end,"renderedStart":segment.start,"renderedEnd":segment.end,"renderedAudio":audio.path,"renderedSeconds":2.0,"speakerId":"role"]],track.appendingPathComponent("timing.json"))
        editor.loadVersions();editor.previewLanguage="en"
        precondition(editor.availableDubLanguages.contains("en") && editor.availableVoiceEngines.contains("cosyvoice3"))
        precondition(editor.engineTake("cosyvoice3")?.path==audio.path)
        let preservedBytes=try Data(contentsOf:review);precondition(preservedBytes==originalBytes)
        model.busy=false
        // Draw the actual SwiftUI panel at the inspector's normal width.
        model.gsvReady=true
        let options=ProjectWorkspaceOptions()
        for operation in ["voice","subtitles","samples"] {
            let choices=ProductionSelection();choices.operation=operation
            let view=ProductionControls(model:model,editor:editor,options:options,selection:choices)
            let host=NSHostingView(rootView:ScrollView {view.padding(16)}.frame(width:420,height:860).background(Color.white).foregroundStyle(Color.black).environment(\.colorScheme,.light))
            host.frame=NSRect(x:0,y:0,width:420,height:860)
            let window=NSWindow(contentRect:host.frame,styleMask:[.borderless],backing:.buffered,defer:false);window.contentView=host
            host.layoutSubtreeIfNeeded();RunLoop.main.run(until:Date().addingTimeInterval(0.5));host.layoutSubtreeIfNeeded()
            if let image=host.bitmapImageRepForCachingDisplay(in:host.bounds) {host.cacheDisplay(in:host.bounds,to:image);if let bytes=image.representation(using:.png,properties:[:]) {try bytes.write(to:qa.appendingPathComponent("production-"+operation+".png"))}}
            window.close()
        }
        print("PASS: subtitle tasks independent of roles; language-scoped apply and undo; stale-edit protection; original clocks/source preserved; new engine/language timeline and audition discovery; native SwiftUI panels rendered.")
        if ProcessInfo.processInfo.environment["SAM_PRODUCTION_VISUAL"]=="1" {
            NSApplication.shared.setActivationPolicy(.regular)
            let host=NSHostingView(rootView:ScrollView {ProductionControls(model:model,editor:editor,options:options).padding(16)}.frame(width:440,height:850).background(StudioPalette.panel).foregroundStyle(ink).environment(\.colorScheme,.light))
            let window=NSWindow(contentRect:NSRect(x:100,y:100,width:440,height:850),styleMask:[.titled,.closable,.resizable],backing:.buffered,defer:false)
            window.title="AniCanto Production QA";window.contentView=host;window.appearance=NSAppearance(named:.aqua);window.makeKeyAndOrderFront(nil);NSApplication.shared.activate(ignoringOtherApps:true)
            NSApplication.shared.run()
        }
    }
}
