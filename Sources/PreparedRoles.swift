import Foundation

extension ProjectEditor {
    var isIndependentVoiceMapping:Bool {config["roleAnalysisMode"] as? String=="independent" || (!profiles.isEmpty && profiles.allSatisfy {$0.identityStatus=="independent"})}
    var voiceManagerTitle:String {isIndependentVoiceMapping ? "逐句配音參考":"角色相簿"}
    func showAnalyzedRoles(_ version:EditVersion,model:AppModel) {
        let path=version.folder.appendingPathComponent("review.json")
        do {
            guard var row=selectedRow,let obj=try JSONSerialization.jsonObject(with:Data(contentsOf:path)) as? [String:Any],let cfg=obj["config"] as? [String:Any],let cues=obj["cues"] as? [[String:Any]],let voices=cfg["voiceProfiles"] else{return}
            let snapshot=ProjectEditor();snapshot.readOnlyPreview=true;snapshot.configure(root:model.engine.root)
            row.review=path;row.previewJob=version.folder;snapshot.projects=[row];snapshot.selected=row.id;snapshot.config=cfg
            snapshot.profiles=try JSONDecoder().decode([VoiceProfile].self,from:JSONSerialization.data(withJSONObject:voices))
            snapshot.duration=cfg["duration"] as? Double ?? duration;snapshot.outputDuration=snapshot.duration;snapshot.offset=cfg["startOffset"] as? Double ?? 0
            let segments=cues.enumerated().map {i,c in EditSegment(id:c["editorID"] as? String ?? "version-\(i)",sources:c["editorSources"] as? [Int] ?? [i],start:c["start"] as? Double ?? 0,end:c["end"] as? Double ?? 1,captionStart:c["subtitleStart"] as? Double ?? c["start"] as? Double ?? 0,captionEnd:c["subtitleEnd"] as? Double ?? c["end"] as? Double ?? 1,text:c["cantonese"] as? String ?? "",original:c["japanese"] as? String ?? c["text"] as? String ?? "",speakerId:c["speakerId"] as? String ?? "",enabled:c["enabled"] as? Bool ?? true,english:c["english"] as? String) }
            snapshot.document=EditDocument(review:path.path,segments:segments,clips:[EditClip(start:0,end:snapshot.duration)])
            snapshot.selectedSegment=segments.first?.id;snapshot.dirty=false;snapshot.refreshEvidence()
            rolePageEditor=snapshot;rolePageState.roleID=snapshot.profiles.first?.id ?? "";workspacePage="roles"
        } catch {self.error=error.localizedDescription}
    }
}

@MainActor extension RoleManagerWindow {
    static func preparedEditor(model:AppModel,editor:ProjectEditor,live:LiveVideoPreview?=nil)->ProjectEditor? {
        guard let row=editor.selectedRow else{return nil}
        if editor.document != nil && !(model.busy && model.activePreviewJob==row.review?.deletingLastPathComponent().path) {return editor}
        let snapshot=ProjectEditor();snapshot.readOnlyPreview=true
        guard loadPreparedRoles(model:model,row:row,into:snapshot,live:live) else{return nil}
        return snapshot
    }
    @discardableResult static func loadPreparedRoles(model:AppModel,row:ProjectRow,into snapshot:ProjectEditor,live:LiveVideoPreview?=nil)->Bool {
        let folder=row.previewJob ?? SavedWorkspace.folder(root:model.engine.root,video:row.video,preferred:model.activePreviewJob)
        let preview=live ?? LiveVideoPreview();preview.refresh(model,video:row.video,preferredJob:folder?.path)
        guard preview.processingVideo==row.video,!preview.profiles.isEmpty else{return false}
        let segments=preview.cues.map {cue in
            EditSegment(id:"preview-\(cue.id)",sources:[cue.id],start:cue.start,end:cue.end,captionStart:cue.start,captionEnd:cue.end,text:cue.cantonese,original:cue.original,speakerId:cue.speakerID,english:cue.english)
        }
        snapshot.configure(root:model.engine.root)
        var linkedRow=row
        if let folder {linkedRow.review=folder.appendingPathComponent("review.json")}
        snapshot.projects=[linkedRow];snapshot.selected=row.id
        let saved=folder.flatMap {try? Data(contentsOf:$0.appendingPathComponent("review.json"))}.flatMap {try? JSONSerialization.jsonObject(with:$0) as? [String:Any]}
        snapshot.config=saved?["config"] as? [String:Any] ?? ["video":row.video]
        snapshot.offset=preview.offset;snapshot.duration=preview.duration;snapshot.outputDuration=preview.duration
        snapshot.sourceCaptions=preview.sourceCaptions
        snapshot.profiles=preview.profiles
        snapshot.document=EditDocument(review:(folder ?? model.engine.root).appendingPathComponent("prepared-role-preview.json").path,segments:segments,clips:[EditClip(start:0,end:preview.duration)])
        if !segments.contains(where:{$0.id==snapshot.selectedSegment}) {snapshot.selectedSegment=segments.first?.id}
        snapshot.dirty=false
        snapshot.refreshEvidence()
        if snapshot.player.currentItem==nil {snapshot.playSource()}
        return true
    }
}
