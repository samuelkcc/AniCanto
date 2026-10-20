import SwiftUI
import Foundation
import AppKit
import CryptoKit

@main struct NaturalTakeIndexTests {
    @MainActor static func main() throws {
        NSApplication.shared.setActivationPolicy(.prohibited)
        let root=URL(fileURLWithPath:ProcessInfo.processInfo.environment["SAM_CANTO_DATA"]!)
        try FileManager.default.createDirectory(at:root,withIntermediateDirectories:true)
        let model=AppModel();model.busy=true;let editor=model.projectEditor;editor.auditionVoiceStyle=nil
        let roleState=RoleManagerState(),savedRoleDraft=root.appendingPathComponent("role-pending.json")
        roleState.configureDraft(savedRoleDraft)
        roleState.draft.stage("role-b",segments:[EditSegment(id:"draft-line",sources:[0],start:0,end:1,captionStart:0,captionEnd:1,text:"測試",original:"test",speakerId:"role-a")])
        let restoredRoleState=RoleManagerState();restoredRoleState.configureDraft(savedRoleDraft)
        precondition(restoredRoleState.draft.changes["draft-line"]?.target=="role-b","Role proposals were lost on page/app reopen")
        restoredRoleState.draft.undo();let undoneRoleState=RoleManagerState();undoneRoleState.configureDraft(savedRoleDraft)
        precondition(undoneRoleState.draft.changes.isEmpty,"Role proposal undo did not persist")
        editor.readOnlyPreview=true;editor.configure(root:root)
        func json(_ object:Any,_ url:URL) throws {try JSONSerialization.data(withJSONObject:object).write(to:url)}
        let review=root.appendingPathComponent("review.json")
        editor.projects=[ProjectRow(id:"project",video:"fixture.mp4",review:review,status:"已完成")];editor.selected="project"
        let low=NaturalVoiceChoice.all.first {$0.id=="yue-low"}!,bright=NaturalVoiceChoice.all.first {$0.id=="yue-bright"}!,english=NaturalVoiceChoice.all.first {$0.id=="en-low"}!
        editor.config=["voiceStyleMode":"natural","selectedEngines":["gpt-sovits"],"dubLanguages":["yue","en"]]
        editor.profiles=[VoiceProfile(id:"role",name:"Role",reference:low.path,promptText:"Japanese original",naturalVoices:["yue":"yue-bright","en":"en-low"])]
        editor.document=EditDocument(review:review.path,segments:[EditSegment(id:"spoken",sources:[0],start:2,end:3,captionStart:2,captionEnd:3,text:"我哋一齊講清楚。",original:"original",speakerId:"role",english:"Let's explain this clearly."),EditSegment(id:"original",sources:[1],start:4,end:5,captionStart:4,captionEnd:5,text:"啊！",original:"original",speakerId:"role")],clips:[EditClip(start:0,end:6)],dubLanguages:["yue","en"],voiceStyleMode:"natural")
        var tracks:[[String:Any]]=[]
        for (language,voice) in [("yue",bright),("en",english)] {
            let folder=root.appendingPathComponent("tracks/"+language);try FileManager.default.createDirectory(at:folder,withIntermediateDirectories:true)
            let wave=folder.appendingPathComponent("gpt-sovits-fixture.wav");try FileManager.default.copyItem(at:URL(fileURLWithPath:voice.path),to:wave)
            let original=folder.appendingPathComponent("original-vocalization-fixture.wav");try FileManager.default.copyItem(at:URL(fileURLWithPath:low.path),to:original)
            let spoken:[String:Any]=["start":2.0,"end":3.0,"speakerId":"role","cantonese":language=="en" ? "Let's explain this clearly.":"我哋一齊講清楚。","english":"Let's explain this clearly."]
            try json(["config":["voiceStyleMode":"natural","gsvVersion":"v4","targetLanguage":language],"cues":[spoken,["start":4.0,"end":5.0,"speakerId":"role","cantonese":"啊！"]]],folder.appendingPathComponent("review.json"))
            try json([["start":2.0,"end":3.0,"audio":wave.path,"renderedSeconds":1.0],["start":4.0,"end":5.0,"audio":original.path,"renderedSeconds":1.0]],folder.appendingPathComponent("timing.json"))
            let hash=SHA256.hash(data:try Data(contentsOf:URL(fileURLWithPath:voice.path))).map {String(format:"%02x",$0)}.joined()
            try json(["role":hash],folder.appendingPathComponent("voice-reference-manifest.json"))
            tracks.append(["engine":"gpt-sovits","language":language,"report":folder.appendingPathComponent("report.json").path])
        }
        try json(["tracks":tracks],root.appendingPathComponent("report.json"));editor.refreshEvidence()
        precondition(editor.engineTake("gpt-sovits",segmentID:"spoken") != nil,"Natural finalized take compared against Japanese source hash")
        precondition(editor.engineTake("gpt-sovits",segmentID:"original") != nil,"Preserved source does not use a voice-cloning reference")
        precondition(editor.cueAudioStatus("gpt-sovits",segmentID:"original")==L("保留原聲（未經聲線模仿）"))
        editor.previewLanguage="en";precondition(editor.engineTake("gpt-sovits",segmentID:"spoken") != nil)
        editor.previewLanguage="yue";editor.profiles[0].naturalVoices?["yue"]="yue-low"
        precondition(editor.engineTake("gpt-sovits",segmentID:"spoken")==nil,"A changed natural voice must not approve an old voice take")
        precondition(editor.engineTake("gpt-sovits",segmentID:"original") != nil)
        editor.profiles[0].naturalVoices?["yue"]="yue-bright"
        let track=root.appendingPathComponent("tracks/yue")
        try json([["start":2.0,"end":3.0,"skipped":true,"audio":track.appendingPathComponent("gpt-sovits-fixture.wav").path,"renderedSeconds":0.0]],track.appendingPathComponent("timing.json"))
        editor.refreshEvidence()
        precondition(editor.engineTake("gpt-sovits",segmentID:"spoken")==nil,"Failed delivery must not be exposed as playable")
        // A cached miss must be invalidated when a single-line audition appears;
        // previews are not full-track reports, but are still playback evidence.
        editor.selectedSegment="spoken";editor.previewEngine="cosyvoice3"
        precondition(editor.engineTake("cosyvoice3")==nil)
        let audition=root.appendingPathComponent("versions/new-cosy-audition")
        try FileManager.default.createDirectory(at:audition,withIntermediateDirectories:true)
        let audio=root.appendingPathComponent("tracks/en/gpt-sovits-fixture.wav")
        try json(["id":"new-cosy-audition","status":"preview","engine":"cosyvoice3","language":"yue","segment":"spoken","created":"2026-10-13T23:00:00Z","output":audio.path],audition.appendingPathComponent("version.json"))
        try json(["config":["voiceStyleMode":"natural"],"cues":[["start":2.0,"end":3.0,"speakerId":"role","cantonese":"我哋一齊講清楚。"]]],audition.appendingPathComponent("review.json"))
        try json([["start":2.0,"end":3.0,"audio":audio.path,"renderedSeconds":1.0]],audition.appendingPathComponent("timing.json"))
        editor.versions=[EditVersion(id:"new-cosy-audition",status:"preview",output:audio,report:nil,folder:audition,created:"2026-10-13T23:00:00Z")]
        editor.profiles[0].naturalVoices?["yue"]="auto"
        try json(["roles":[["roleId":"role","language":"yue","voiceId":"yue-bright"]]],audition.appendingPathComponent("natural-casting.json"))
        let auditionHash=SHA256.hash(data:try Data(contentsOf:URL(fileURLWithPath:bright.path))).map {String(format:"%02x",$0)}.joined()
        try json(["role":auditionHash],audition.appendingPathComponent("voice-reference-manifest.json"))
        editor.refreshEvidence()
        precondition(editor.engineTake("cosyvoice3") != nil,"New CosyVoice audition left playback disabled after a cached miss")
        if ProcessInfo.processInfo.environment["CANTO_SNAPSHOT_DIR"] != nil {
            let qa=URL(fileURLWithPath:ProcessInfo.processInfo.environment["CANTO_SNAPSHOT_DIR"]!)
            for page in ["edit","review","produce","roles"] {
                editor.workspacePage=page
                let view=ContentView().environmentObject(model)
                let host=NSHostingView(rootView:view.frame(width:1440,height:960).background(Color.white).foregroundStyle(Color.black).environment(\.colorScheme,.light))
                host.frame=NSRect(x:0,y:0,width:1440,height:960)
                let window=NSWindow(contentRect:host.frame,styleMask:[.borderless],backing:.buffered,defer:false);window.isReleasedWhenClosed=false;window.contentView=host
                host.layoutSubtreeIfNeeded();RunLoop.main.run(until:Date().addingTimeInterval(0.5));host.layoutSubtreeIfNeeded()
                if let image=host.bitmapImageRepForCachingDisplay(in:host.bounds) {host.cacheDisplay(in:host.bounds,to:image);try image.representation(using:.png,properties:[:])!.write(to:qa.appendingPathComponent("workspace-"+page+".png"))}
                window.close()
            }
        }
        print("PASS: finalized natural Cantonese/English playback uses target references; changed voices invalidate takes; preserved originals stay playable and labeled accurately.")
    }
}
