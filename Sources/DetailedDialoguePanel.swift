import SwiftUI
final class DialoguePanelOptions:ObservableObject {@Published var category="timing"}
struct DetailedDialoguePanel:View {
    @ObservedObject var model:AppModel
    @ObservedObject var editor:ProjectEditor
    var close:()->Void
    @StateObject private var options=DialoguePanelOptions()
    var body:some View {
        VStack(spacing:0) {
            HStack {Text(L("對白詳細設定")).font(.title2.bold());Spacer();Button(L("完成"),action:close)}.padding(20)
            Divider()
            Picker(L("分類"),selection:$options.category) {Text(L("時段與裁切")).tag("timing");Text(L("改稿與試音")).tag("takes");Text(L("台詞分割")).tag("split")}.pickerStyle(.segmented).padding(20)
            ScrollView {
                VStack(alignment:.leading,spacing:22) {
                    if let i=editor.segmentIndex,let segment=editor.document?.segments[i] {
                        Text(L("對白")+" \(i+1) · "+studioTimecode(segment.start)+" — "+studioTimecode(segment.end)).font(.headline)
                        if options.category=="timing" {
                            Grid(alignment:.leading,horizontalSpacing:35,verticalSpacing:22) {
                                GridRow {field("配音開始",\.start);field("配音結束",\.end)}
                                GridRow {field("字幕開始",\.captionStart);field("字幕結束",\.captionEnd)}
                                GridRow {field("裁頭（秒）",\.trimStart);field("裁尾（秒）",\.trimEnd)}
                                GridRow {field("語速",\.rate)}
                            }
                            Text(L("拖動時間軸邊界可 trim。裁頭／裁尾只處理配音 take；影片剪接喺時間軸及剪接檢查器設定。")).foregroundStyle(.secondary)
                        } else if options.category=="takes" {
                            Picker(L("試音引擎"),selection:$editor.previewEngine) {ForEach(VoiceEngineChoice.all) {Text($0.title).tag($0.id)}}
                            Picker(L("試聽語言"),selection:$editor.previewLanguage) {Text(L("廣東話")).tag("yue");Text(L("英文")).tag("en")}.pickerStyle(.segmented)
                            HStack {Button(L("生成呢段試音")) {model.submitEditor(previewOnly:true)}.disabled(model.busy);Button(L("另一個 take")) {editor.updateSegment {$0.take+=1;$0.audioTake=nil};model.submitEditor(previewOnly:true)}.disabled(model.busy)}
                            HStack {Button(L("重譯原文建議")) {model.suggestEditorShortening(translate:true)};Button(L("AI 改短建議")) {model.suggestEditorShortening()}}.disabled(model.busy)
                            Stepper("Take \(segment.take)",value:Binding(get:{segment.take},set:{v in editor.updateSegment {$0.take=v}}),in:0...100000)
                            if let suggestion=editor.suggestion {GroupBox(L("待批核建議")) {VStack(alignment:.leading,spacing:16) {Text(suggestion).textSelection(.enabled);HStack {Button(L("採用建議")) {editor.acceptSuggestion()};Button(L("保留原文")) {editor.suggestion=nil;editor.suggestionTarget=nil}}}.padding(18)}}
                        } else {
                            Text(L("先將播放頭移到分割時間，再選文字分界；重新配音會保留字句完整。")).foregroundStyle(.secondary)
                            Stepper(L("文字分界")+" \(editor.splitAt)",value:$editor.splitAt,in:1...max(1,segment.text.count-1))
                            if !segment.captionText.isEmpty {Stepper(L("顯示字幕分界")+" \(editor.splitCaptionAt)",value:$editor.splitCaptionAt,in:1...max(1,segment.captionText.count-1))}
                            Text(String(segment.text.prefix(editor.splitAt))+" ｜ "+String(segment.text.dropFirst(editor.splitAt))).font(.title3).textSelection(.enabled)
                            HStack {Button(L("分割台詞")) {editor.splitSegment()};Button(L("分割現有聲音 take")) {editor.splitSegment(reuseAudio:true)}.disabled(segment.audioTake==nil);Button(L("合併下一段"),action:editor.mergeNext).disabled(i+1>=editor.document!.segments.count)}
                        }
                    }
                }.padding(28).frame(maxWidth:.infinity,alignment:.leading)
            }
        }.frame(width:1100,height:700).background(StudioPalette.panel).font(.system(size:15)).buttonStyle(StudioButtonStyle()).environment(\.locale,appInterfaceLocale)
    }
    func field(_ title:String,_ key:WritableKeyPath<EditSegment,Double>)->some View {
        HStack {Text(L(title)).frame(width:140,alignment:.leading);TextField(L(title),value:Binding(get:{guard let i=editor.segmentIndex else{return 0};return editor.document?.segments[i][keyPath:key] ?? 0},set:{v in editor.updateSegment {$0[keyPath:key]=v}}),format:.number.precision(.fractionLength(2))).textFieldStyle(.roundedBorder).frame(width:140)}
    }
}
