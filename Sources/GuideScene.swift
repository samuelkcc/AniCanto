import SwiftUI

/// Character lives exclusively in the sidebar. This is a compact import surface.
struct WelcomeScene:View {
    @ObservedObject var model:AppModel
    var body:some View {
        VStack(alignment:.leading,spacing:22) {
            HStack {
                Label(L("配音準備室"),systemImage:"film.stack").font(.caption.bold()).foregroundStyle(accent)
                Spacer();Image(systemName:"sparkles").foregroundStyle(accent)
            }
            Image(systemName:"play.rectangle.on.rectangle").font(.system(size:52,weight:.light)).foregroundStyle(accent).padding(.top,8)
            Text(L("下一場，輪到你配音。")).font(.system(size:26,weight:.bold,design:.rounded))
            Text(L("拖入動畫，開始你嘅廣東話配音。")).font(.callout).foregroundStyle(.secondary)
            HStack(spacing:12) {
                Label(L("匯入"),systemImage:"film")
                Image(systemName:"chevron.right").font(.caption2)
                Label(L("配音"),systemImage:"waveform")
                Image(systemName:"chevron.right").font(.caption2)
                Label(L("輸出"),systemImage:"square.and.arrow.up")
            }.font(.caption).foregroundStyle(.secondary).padding(.vertical,8)
            HStack {
                Text("MP4 / MKV / MOV").font(.caption.monospaced()).foregroundStyle(.secondary)
                Spacer()
                Button(L("批量匯入"),action:model.chooseBatch)
                Button(action:model.chooseVideo) {Label(L("選擇影片"),systemImage:"plus")}.buttonStyle(.borderedProminent)
            }.disabled(model.busy)
        }.padding(8).card()
        .onDrop(of:[.fileURL],isTargeted:nil) {providers in
            guard !model.busy,let provider=providers.first else {return false}
            _=provider.loadObject(ofClass:URL.self) {url,_ in if let url {Task {@MainActor in model.loadVideo(url)}}};return true
        }
    }
}
