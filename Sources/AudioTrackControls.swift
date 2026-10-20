import SwiftUI
struct AudioTrackProgress:Codable {
    var review:String,folder:String,engine:String,language:String,token:String,state:String
}
extension AppModel {
    func skipAudioTrack() {
        guard busy,let track=activeAudioTrack,!audioSkipRequested else{return}
        let folder=URL(fileURLWithPath:track.folder).standardizedFileURL
        guard folder.path.hasPrefix(engine.root.standardizedFileURL.path+"/jobs/") else{return}
        do {try JSONEncoder().encode(track).write(to:folder.appendingPathComponent("skip-generation.json"),options:.atomic);audioSkipRequested=true;logs.append("["+L("跳過音軌")+"] "+L("完成目前一句後跳過餘下生成；已完成錄音保留。"))}
        catch {self.error=error.localizedDescription}
    }
}
struct SkipAudioTrackButton:View {
    @ObservedObject var model:AppModel
    var body:some View {
        if model.busy,model.activeAudioTrack != nil {
            Button {model.skipAudioTrack()} label:{Label(L(model.audioSkipRequested ? "等待目前一句完成…":"跳過本音軌餘下生成"),systemImage:"forward.end")}.disabled(model.audioSkipRequested || model.pauseRequested)
        }
    }
}
