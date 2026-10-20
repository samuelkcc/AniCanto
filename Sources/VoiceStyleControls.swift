import SwiftUI
import AVKit

struct NaturalVoiceChoice:Decodable,Identifiable {
    var id:String;var title:String;var file:String;var language:String;var pitchHz:Double
    static var all:[NaturalVoiceChoice] {
        struct Catalog:Decodable {var voices:[NaturalVoiceChoice]}
        guard let root=Bundle.main.resourceURL,let data=try? Data(contentsOf:root.appendingPathComponent("natural-voices/catalog.json")) else{return []}
        return (try? JSONDecoder().decode(Catalog.self,from:data).voices) ?? []
    }
    var path:String {Bundle.main.resourceURL!.appendingPathComponent("natural-voices").appendingPathComponent(file).path}
}
struct VoiceStyleControls:View {
    @Binding var mode:String
    var body:some View {EmptyView()}
}

extension ProjectEditor {
    var voiceStyleMode:String {"clone"}
    func naturalReference(_ profile:VoiceProfile,engine:String,language:String,castingFolder:URL?=nil)->String? {
        if let own=profile.engineReferences?[engine+":"+language],own.enabled,own.language==language,own.ready {return own.reference}
        if profile.language==language,profile.ready {return profile.reference}
        let selected=profile.naturalVoices?[language] ?? "auto"
        if selected != "auto" {return NaturalVoiceChoice.all.first {$0.id==selected && $0.language==language}?.path}
        if let folder=castingFolder ?? evidenceFolders[engine+":"+language],let data=try? Data(contentsOf:folder.appendingPathComponent("natural-casting.json")),let cast=try? JSONSerialization.jsonObject(with:data) as? [String:Any],let rows=cast["roles"] as? [[String:Any]],let row=rows.first(where:{$0["roleId"] as? String==profile.id && $0["language"] as? String==language}),let id=row["voiceId"] as? String {return NaturalVoiceChoice.all.first {$0.id==id}?.path}
        return nil
    }
}
struct NaturalRoleVoiceControls:View {
    @ObservedObject var editor:ProjectEditor
    let profileID:String
    var selection:Binding<String> {Binding(get:{editor.profiles.first {$0.id==profileID}?.naturalVoices?[editor.previewLanguage] ?? "auto"},set:{value in
        guard let index=editor.profiles.firstIndex(where:{$0.id==profileID}) else{return}
        if editor.profiles[index].naturalVoices==nil {editor.profiles[index].naturalVoices=[:]}
        editor.profiles[index].naturalVoices?[editor.previewLanguage]=value;editor.invalidateTakes();editor.dirty=true;editor.scheduleSave()
    })}
    var body:some View {
        VStack(alignment:.leading,spacing:8) {
            Picker(L("自然聲線"),selection:selection) {
                Text(L("自動按角色音域選擇")).tag("auto")
                ForEach(NaturalVoiceChoice.all.filter {$0.language==editor.previewLanguage}) {row in Text(L(row.title)).tag(row.id)}
            }.disabled(editor.readOnlyPreview)
            Text(L("同一角色、同一語言固定使用所選聲線；只改新生成配音。自動選擇係音域近似，並非性別或身份辨識。")).font(.caption).foregroundStyle(.secondary)
            Text(L("可在參考錄音設定匯入自己的同語言 WAV，取代內置聲線。")).font(.caption).foregroundStyle(.secondary)
        }
    }
}
