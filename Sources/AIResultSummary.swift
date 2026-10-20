import SwiftUI

struct AIResultSummaryView:View {
    @ObservedObject var model:AppModel
    var body:some View {
        VStack(alignment:.leading,spacing:18) {
            Label(L("AI 處理摘要"),systemImage:"wand.and.stars").font(.title2.bold())
            ScrollView {Text(model.resultSummary).textSelection(.enabled).frame(maxWidth:.infinity,alignment:.leading)}
            HStack {
                Button(L("詳細紀錄")) {model.showAIResultSummary=false;model.projectEditor.workspacePage="review"}
                Spacer()
                Button(L("完成")) {model.showAIResultSummary=false}.buttonStyle(.borderedProminent).keyboardShortcut(.defaultAction)
            }
        }.padding(24).frame(minWidth:600,idealWidth:760,minHeight:320,idealHeight:440)
    }
}
