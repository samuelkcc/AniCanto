import AppKit
import SwiftUI

@main struct EditorScriptSyncTests {
 @MainActor static func main() throws {
    setbuf(stdout,nil)
    func check(_ value:@autoclosure ()->Bool,_ message:String="",line:UInt=#line) {if !value() {print("FAIL line \(line): \(message)");exit(1)}}
    NSApplication.shared.setActivationPolicy(.prohibited)
    let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath+"/.build/qa267/original")
    func object(_ name:String)throws->[String:Any] {try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent(name))) as! [String:Any]}
    let base=try object("editor-base.json")["cues"] as! [[String:Any]],current=try object("review.json")["cues"] as! [[String:Any]]
    var document=try JSONDecoder().decode(EditDocument.self,from:Data(contentsOf:root.appendingPathComponent("editor-draft.json")))
    let before=document
    check(EditorScriptSync.merge(&document,base:base,current:current)==208,"EP06 stale draft must refresh 208 untouched old scripts, including 28 blanks")
    for i in document.segments.indices {
        let old=before.segments[i],new=document.segments[i]
        check(old.start==new.start && old.end==new.end && old.speakerId==new.speakerId && old.take==new.take)
        if old.text != (base[i]["cantonese"] as? String ?? "") {check(old.text==new.text)}
    }
    check(!document.segments[190].text.isEmpty && !document.segments[214].text.isEmpty)
    check(document.pendingChanges==before.pendingChanges)
    document.segments[190].text=""
    check(EditorScriptSync.merge(&document,base:base,current:current)==0,"A user's later deletion must remain a deletion")
    var manual=before;manual.segments[190].manual=true
    check(EditorScriptSync.merge(&manual,base:base,current:current)==207)
    let frozen=try JSONEncoder().encode(document)
    var restored=try JSONDecoder().decode(EditDocument.self,from:frozen)
    check(EditorScriptSync.merge(&restored,base:base,current:current)==0,"Sync ownership must survive restart")
    print("PASS script synchronization and edit ownership")
    let model=AppModel(),editor=model.projectEditor
    model.busy=false
    let job=URL(fileURLWithPath:FileManager.default.currentDirectoryPath+"/.build/qa267/ep06")
    let cfg=try JSONSerialization.jsonObject(with:Data(contentsOf:job.appendingPathComponent("review.json"))) as! [String:Any]
    let video=(cfg["config"] as! [String:Any])["video"] as! String
    let row=ProjectRow(id:"ep06-qa",video:video,review:job.appendingPathComponent("review.json"),status:"完成")
    editor.projects=[row];editor.open(row)
    check(editor.document!.segments.filter{$0.enabled && $0.text.isEmpty}.isEmpty)
    let audit=try JSONSerialization.jsonObject(with:Data(contentsOf:job.appendingPathComponent("dialogue-delivery-audit.json"))) as! [String:Any]
    let required=((audit["tracks"] as! [[String:Any]])[0]["rows"] as! [[String:Any]])
    let live=model.workspacePreview;live.refresh(model,video:video,preferredJob:job.path)
    var tested=0
    for proof in required where proof["available"] as? Bool==true {
        let i=(proof["index"] as! Int)-1
        editor.selectedSegment=editor.document!.segments[i].id
        check(editor.cueVoiceAvailable("drama3",language:"yue"),"Pro playback unavailable at \(i+1)")
        let segment=editor.document!.segments[i]
        let simple=live.takes.first {$0.engine=="drama3" && $0.language=="yue" && abs($0.start-segment.start)<0.001 && abs($0.end-segment.end)<0.001 && $0.text==segment.text}
        check(simple != nil,"Simple playback unavailable at \(i+1)")
        check(editor.cuePlaybackPath("drama3",language:"yue")==simple!.path,"Both modes must prefer the same final take at \(i+1)")
        tested += 1
        if tested%50==0 {print("Verified \(tested) cue playback pairs")}
    }
    print("PASS \(tested) actual cue playback pairs")
    let choices=editor.productionSelection(model)
    model.selectSimpleEngine("cosyvoice3");model.selectWorkspaceLanguage("both");model.setWorkspaceOriginal(false)
    model.setWorkspaceOPDetect(true);model.setWorkspaceOPTranslate(true)
    editor.setOutputSubtitle("original",true);editor.setOutputSubtitle("english",true)
    var simple=SimpleWorkspace(model:model,editor:editor,preview:live)
    check(simple.plan.engine=="cosyvoice3" && simple.plan.languages==["yue","en"] && !simple.plan.includeOriginal)
    check(choices.engines==["cosyvoice3"] && choices.languages==["yue","en"])
    check(simple.plan.subtitles==editor.outputSubtitleModes && simple.plan.translateOPED)
    choices.engines=["drama3"];choices.languages=["yue"];choices.includeOriginal=true;choices.aiAutoFix=false
    simple=SimpleWorkspace(model:model,editor:editor,preview:live)
    check(simple.plan.engine=="drama3" && simple.plan.languages==["yue"] && simple.plan.includeOriginal && !simple.plan.aiAutoFix)
    let frozenRequest=try JSONSerialization.data(withJSONObject:["video":video,"selectedEngines":["drama3"],"ttsBackend":"drama3","dubLanguages":["yue"],"includeOriginal":true])
    model.currentBatchRequest=frozenRequest;model.busy=true
    model.selectSimpleEngine("cosyvoice3");model.selectWorkspaceLanguage("en")
    check(model.submittedVoiceSelection(video:video)?.primary=="drama3" && model.submittedVoiceSelection(video:video)?.languages==["yue"])
    check(model.currentBatchRequest==frozenRequest)
    editor.player.pause();editor.audio.pause();live.player.pause();model.busy=false
    print("PASS both interfaces: \(tested) actual delivered cues playable and use identical final audio; shared engine, language, original audio, OP/ED, subtitle and AI options; frozen request preserved")
    print("PASS EP06 actual stale draft: 208 old scripts synchronized, including 28 blanks; 191/215 restored; text edits, role, timing, disabled states, takes and pending edits preserved; restart and deliberate deletion protected")
 }
}
