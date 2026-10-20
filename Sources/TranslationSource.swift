import SwiftUI

/// Expert-only input selection. Output subtitle tracks remain independent.
struct TranslationSourceControl:View {
    @Binding var source:String
    @AppStorage("studioInterfaceMode") private var mode="simple"
    var body:some View {
        if mode=="professional" {VStack(alignment:.leading,spacing:7) {
            Picker(L("翻譯來源"),selection:$source) {
                Text(L("日文原聲＋中文字幕輔助")).tag("audio-and-subtitles")
                Text(L("只聽日文原聲")).tag("audio-only")
            }
            if source=="audio-only" {
                Text(L("直接由日語辨識翻譯香港廣東話及／或英文；翻譯及修復不使用 OCR、內置或外掛中文字幕。品質檢查維持原設定。")).font(.caption).foregroundStyle(.secondary)
            }
        }}
    }
}
