import SwiftUI

enum StudioTranscriptLayout {
    static func wide(_ width:Double)->Bool {width>=1150}
    static func height(preferred:Double,topHeight:Double)->Double {
        let minimum=topHeight<360 ? 110.0:180.0
        return min(max(minimum,preferred),max(minimum,topHeight*0.44),max(100,topHeight-150))
    }
}

struct TranscriptRoleCard:View {
    let profile:VoiceProfile
    let code:String
    var candidate:NSImage?=nil
    var body:some View {
        VStack(spacing:6) {
            if let image=roleImage(profile.avatar) {
                Image(nsImage:image).resizable().scaledToFill().frame(width:88,height:88).clipped().clipShape(RoundedRectangle(cornerRadius:9))
            } else if let image=roleImage(profile.sourceFrame) ?? candidate {
                Image(nsImage:image).resizable().scaledToFit().frame(width:88,height:70).clipShape(RoundedRectangle(cornerRadius:9))
                Text(L("候選畫面")).font(.caption2).foregroundStyle(.secondary)
            } else {Image(systemName:"person.crop.square.fill").font(.system(size:48)).frame(width:88,height:88).foregroundStyle(roleColor(profile.id))}
            Text(code).font(.system(size:14,weight:.semibold)).foregroundStyle(roleColor(profile.id))
            Text(localizedRoleName(profile.name)).font(.system(size:15,weight:.medium)).lineLimit(2)
        }.padding(8).frame(width:112).background(roleColor(profile.id).opacity(0.10),in:RoundedRectangle(cornerRadius:10))
    }
}

struct EditorTranscriptRoleCard:View {
    let profile:VoiceProfile
    let code:String
    @ObservedObject var editor:ProjectEditor
    @ObservedObject var model:AppModel
    let live:LiveVideoPreview
    @StateObject private var thumbnails=RoleFrameThumbnails()
    var time:Double {
        if let segment=editor.document?.segments.filter({$0.speakerId==profile.id}).max(by:{$0.end-$0.start<$1.end-$1.start}) {return editor.offset+(segment.start+segment.end)*0.5}
        if let cue=live.cues.filter({$0.speakerID==profile.id}).max(by:{$0.end-$0.start<$1.end-$1.start}) {return live.offset+(cue.start+cue.end)*0.5}
        return editor.offset+(profile.avatarTime ?? profile.referenceRanges?.first?.first ?? 0)
    }
    var video:String {editor.document?.videoOverride ?? editor.selectedRow?.video ?? editor.config["video"] as? String ?? ""}
    var key:String {thumbnails.key(video:video,time:time)}
    var body:some View {
        TranscriptRoleCard(profile:profile,code:code,candidate:thumbnails.images[key])
            .task(id:key) {if roleImage(profile.avatar)==nil && roleImage(profile.sourceFrame)==nil {thumbnails.request(video:video,time:time,ffmpeg:model.engine.ffmpeg,folder:editor.selectedRow?.review?.deletingLastPathComponent() ?? editor.selectedRow?.previewJob)}}
    }
}
