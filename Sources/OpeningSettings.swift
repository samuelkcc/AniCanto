import SwiftUI

struct OpeningTreatmentControls:View {
    @Binding var detect:Bool
    @Binding var translate:Bool
    var selection:Binding<String> {Binding(get:{!detect ? "off":translate ? "translate":"preserve"},set:{value in detect=value != "off";translate=value=="translate"})}
    var body:some View {
        VStack(alignment:.leading,spacing:6) {
            Picker(L("OP／ED 處理"),selection:selection) {
                Text(L("保留日文原聲")).tag("preserve")
                Text(L("亦翻譯配音")).tag("translate")
                Text(L("不偵測，全部照常處理")).tag("off")
            }
            Text(L(translate && detect ? "OP／ED 範圍內對白亦會翻譯配音；不會因偵測結果跳過片頭對白。歌詞以配音朗讀。":"設定套用至之後開始嘅轉換；已提交工作沿用原有設定。"))
                .font(.caption).foregroundStyle(.secondary)
        }
    }
}
