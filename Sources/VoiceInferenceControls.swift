import SwiftUI

struct VoiceInferenceControls:View {
    @ObservedObject var editor:ProjectEditor
    @ObservedObject var options:ProjectWorkspaceOptions
    var body:some View {
        DisclosureGroup(L("配音生成參數")) {
            VStack(alignment:.leading,spacing:10) {
                if editor.previewEngine=="cosyvoice3" {
                    Picker(L("情緒表演"),selection:$options.cosyExpression) {
                        Text(L("沿用參考" )).tag("neutral");Text(L("有表情")).tag("expressive");Text(L("緊張／堅定")).tag("urgent");Text(L("平靜／溫柔")).tag("calm")
                    }
                    control("Temperature",$options.cosyTemperature,0.3...1)
                } else {
                    control("Temperature",$options.gptTemperature,0.6...1.2)
                    control("Top P",$options.gptTopP,0.6...1)
                    control("Repetition penalty",$options.gptRepetitionPenalty,1...1.6)
                    Stepper("Top K · \(options.gptTopK)",value:$options.gptTopK,in:5...30)
                    Text(L("GPT 未提供獨立情緒或去口音控制；參考錄音仍會影響語調。" )).font(.caption).foregroundStyle(.secondary)
                }
                if let i=editor.segmentIndex {
                    Stepper(L("隨機種子")+" · \(editor.document!.segments[i].take)",value:Binding(get:{editor.document?.segments[i].take ?? 42},set:{v in editor.updateSegment {$0.take=v}}),in:0...999999)
                }
                Button(L("重設生成參數")) {options.gptTemperature=1;options.gptTopP=1;options.gptTopK=15;options.gptRepetitionPenalty=1.35;options.cosyTemperature=0.7;options.cosyExpression="neutral"}
                Text(L("參數只用於新試音；不能保證消除口音。更換參考錄音請到角色頁。" )).font(.caption).foregroundStyle(.secondary)
            }.padding(.vertical,8)
        }
    }
    private func control(_ title:String,_ value:Binding<Double>,_ range:ClosedRange<Double>)->some View {
        VStack(alignment:.leading,spacing:4) {HStack {Text(title);Spacer();Text(String(format:"%.2f",value.wrappedValue)).monospacedDigit()};Slider(value:value,in:range)}.font(.caption)
    }
}

struct VoiceABControls:View {
    @ObservedObject var model:AppModel
    @ObservedObject var editor:ProjectEditor
    @ObservedObject var options:ProjectWorkspaceOptions
    var body:some View {
        DisclosureGroup(L("A／B 試音比較"),isExpanded:$options.showABComparison) {
            VStack(alignment:.leading,spacing:10) {
                candidate("A",$options.comparisonEngineA,$options.comparisonParametersA)
                candidate("B",$options.comparisonEngineB,$options.comparisonParametersB)
                Text(L("同一句、同一語言、同一角色參考。可選不同模型，亦可用同一模型比較參數；不合片、不自動採用。")).font(.caption).foregroundStyle(.secondary)
                Button(L("生成 A＋B 並比較")) {model.compareCantoneseAuditions()}.disabled(model.busy)
            }.padding(.vertical,8)
        }
    }
    func candidate(_ label:String,_ engine:Binding<String>,_ parameters:Binding<[String:Any]?>)->some View {
        VStack(alignment:.leading,spacing:5) {
            HStack {Text(label).font(.headline);Picker(L("模型"),selection:engine) {ForEach(VoiceEngineChoice.all) {Text($0.title).tag($0.id)}}.labelsHidden()}
            HStack {Button(L("保存目前參數")) {parameters.wrappedValue=options.inferenceSettings};if parameters.wrappedValue != nil {Button(L("使用目前參數")) {parameters.wrappedValue=nil}}}
            Text(parameters.wrappedValue.map {String(format:"Temperature %.2f · Top P %.2f",$0["gptTemperature"] as? Double ?? 1,$0["gptTopP"] as? Double ?? 1)} ?? L("使用目前參數")).font(.caption).foregroundStyle(.secondary)
        }
    }
}
