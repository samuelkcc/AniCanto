import SwiftUI
struct StudioSoundMixer:View {
    @ObservedObject var editor:ProjectEditor
    @ObservedObject var live:LiveVideoPreview
    var body:some View {
        VStack(alignment:.leading,spacing:18) {
            Text(L("音量與混音")).font(.headline)
            GroupBox(L("試聽音量")) {
                VStack(alignment:.leading,spacing:8) {
                    HStack {Image(systemName:"speaker.wave.2");Slider(value:$editor.previewVolume,in:0...1);Text(String(format:"%.0f%%",editor.previewVolume*100)).monospacedDigit().frame(width:45)}
                    Text(L("只調整播放器與逐句試聽音量，不影響成品。")).font(.caption).foregroundStyle(.secondary)
                }.padding(8)
            }
            if let document=editor.document {
                GroupBox(L("成品背景音")) {
                    VStack(alignment:.leading,spacing:10) {
                        Text(L("背景音樂／音效"))
                        HStack {Slider(value:Binding(get:{document.backgroundGain},set:{gain in editor.update {$0.backgroundGain=gain}}),in:0...2);Text(String(format:"%.0f%%",document.backgroundGain*100)).monospacedDigit().frame(width:50)}
                        Toggle(L("有人講嘢時降低背景音"),isOn:Binding(get:{document.backgroundDucking ?? false},set:{value in editor.update {$0.backgroundDucking=value}}))
                        Text(L("配音保持已檢查的音量；背景修改會套用到下一個生成版本。")).font(.caption).foregroundStyle(.secondary)
                    }.padding(8)
                }
            }
            Text(L("原裝中文字幕跟影片原時間，配音語速與音量不會改動原字幕。")).font(.caption).foregroundStyle(.secondary)
        }.onChange(of:editor.previewVolume) {_ in live.player.volume=Float(editor.previewVolume)}
    }
}
