import SwiftUI

final class EditorOptions: ObservableObject { @Published var showAll=false }
extension ContentView {
    var editorCaptions:[PreviewCaption] {
        m.scriptCues.filter(\.included).map { PreviewCaption(start:m.showingOutput ? $0.start : ($0.sourceStart ?? $0.start),end:m.showingOutput ? $0.end : ($0.sourceEnd ?? $0.end),text:$0.cantonese) }
    }
    var editorIndices:[Int] {
        if editorOptions.showAll { return Array(m.scriptCues.indices) }
        if let i=m.selectedCue,m.scriptCues.indices.contains(i) { return [i] }
        if let i=m.scriptCues.firstIndex(where:{($0.sourceStart ?? $0.start)<=m.playbackSeconds && m.playbackSeconds<($0.sourceEnd ?? $0.end)}) { return [i] }
        return m.scriptCues.isEmpty ? [] : [0]
    }
}
struct SubtitleTimeline: View {
    @ObservedObject var model:AppModel
    var body: some View {
        GeometryReader { geometry in
            let bounds=model.scriptCues.map { cue in (model.showingOutput ? cue.start : cue.sourceStart ?? cue.start, model.showingOutput ? cue.end : cue.sourceEnd ?? cue.end) }
            let origin=max(0,(bounds.map(\.0).min() ?? 0)-1)
            let duration=max(1,(bounds.map(\.1).max() ?? model.playbackDuration)+1-origin)
            let width=geometry.size.width
            ZStack(alignment:.topLeading) {
                RoundedRectangle(cornerRadius:8).fill(surface)
                Canvas { ctx,size in
                    for tick in 0...10 {
                        let x=size.width*Double(tick)/10
                        var line=Path();line.move(to:CGPoint(x:x,y:0));line.addLine(to:CGPoint(x:x,y:size.height))
                        ctx.stroke(line,with:.color(.secondary.opacity(0.2)),lineWidth:1)
                        let seconds=origin+duration*Double(tick)/10
                        ctx.draw(Text(String(format:"%02d:%02d",Int(seconds)/60,Int(seconds)%60)).font(.system(size:9,design:.monospaced)).foregroundColor(.secondary),at:CGPoint(x:min(max(18,x),size.width-18),y:9))
                    }
                    for (i,cue) in model.scriptCues.enumerated() {
                        let start=model.showingOutput ? cue.start : cue.sourceStart ?? cue.start
                        let end=model.showingOutput ? cue.end : cue.sourceEnd ?? cue.end
                        let x=max(0,(start-origin)/duration*size.width),right=min(size.width,(end-origin)/duration*size.width)
                        guard right>x else { continue }
                        let active=start<=model.playbackSeconds && model.playbackSeconds<end
                        let rect=CGRect(x:x,y:26,width:max(2,right-x),height:28)
                        ctx.fill(Path(roundedRect:rect,cornerRadius:3),with:.color(cue.included ? accent.opacity(active || model.selectedCue==i ? 0.9 : 0.35) : .gray.opacity(0.3)))
                        if rect.width>42 { ctx.draw(Text(String(cue.cantonese.prefix(8))).font(.system(size:9)).foregroundColor(.primary),at:CGPoint(x:rect.midX,y:rect.midY)) }
                    }
                }
                Rectangle().fill(Color.red).frame(width:2,height:64).offset(x:min(width,max(0,(model.playbackSeconds-origin)/duration*width)))
            }.contentShape(Rectangle()).gesture(DragGesture(minimumDistance:0).onChanged { value in
                let seconds=origin+min(duration,max(0,value.location.x/max(1,width)*duration))
                model.seekVideo(seconds)
                model.selectedCue=model.scriptCues.firstIndex { cue in
                    let start=model.showingOutput ? cue.start : cue.sourceStart ?? cue.start
                    let end=model.showingOutput ? cue.end : cue.sourceEnd ?? cue.end
                    return start<=seconds && seconds<end
                }
            }).accessibilityLabel("字幕片段時間軸")
        }.onAppear { model.selectPreviewSubtitle() }
        .onDisappear { model.selectPreviewSubtitle() }
        .onChange(of:model.playbackSeconds) { seconds in
            if !model.scriptCues.isEmpty {
                model.selectedCue=model.scriptCues.firstIndex { cue in
                    let start=model.showingOutput ? cue.start : cue.sourceStart ?? cue.start
                    let end=model.showingOutput ? cue.end : cue.sourceEnd ?? cue.end
                    return start<=seconds && seconds<end
                }
            }
        }
    }
}
