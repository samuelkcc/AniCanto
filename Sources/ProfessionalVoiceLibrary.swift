import SwiftUI
import AppKit

final class ProfessionalVoiceSelection:ObservableObject {
    @Published var selected=""
    @Published var search=""
}
extension ContentView {
    func clearLibraryVoices(_ ids:Set<String>) {
        guard !m.busy,!ids.isEmpty else{return}
        let alert=NSAlert()
        alert.messageText=String(format:L("刪除 %d 個聲線？"),ids.count)
        alert.informativeText=L("只清理聲線資料庫；影片專案嘅角色、配音同原片會保留。")
        alert.addButton(withTitle:L("刪除"));alert.addButton(withTitle:L("取消"))
        guard alert.runModal() == .alertFirstButtonReturn else{return}
        do {
            try m.removeLibraryVoices(ids)
            savedVoiceIDs=SavedVoiceLibrary.ids(savedVoiceIDs).subtracting(ids).sorted().joined(separator:",")
            selectLibraryVoice()
        } catch {m.error=error.localizedDescription}
    }
    var voiceLibraryRows:[VoiceProfile] {
        let saved=SavedVoiceLibrary.ids(savedVoiceIDs)
        return m.voiceProfiles.filter {(voiceLibraryCategory == "saved" ? saved.contains($0.id):!saved.contains($0.id)) && (libraryOptions.search.isEmpty || $0.name.localizedCaseInsensitiveContains(libraryOptions.search))}
    }
    func selectLibraryVoice() {if !voiceLibraryRows.contains(where:{$0.id==libraryOptions.selected}) {libraryOptions.selected=voiceLibraryRows.first?.id ?? ""}}
    var professionalVoicePage:some View {
        HStack(spacing:0) {
            VStack(spacing:0) {
                StudioPanelHeader(title:"常用聲線",icon:"person.2")
                Picker(L("聲線分類"),selection:$voiceLibraryCategory) {Text(L("常用聲線")).tag("saved");Text(L("歷史參考")).tag("history")}.labelsHidden().pickerStyle(.segmented).padding(12)
                TextField(L("搜尋角色"),text:$libraryOptions.search).textFieldStyle(.roundedBorder).padding(12)
                HStack {Button(L("加入角色")) {let role=VoiceProfile(name:L("角色")+" \(m.voiceProfiles.count+1)");m.voiceProfiles.append(role);savedVoiceIDs=SavedVoiceLibrary.updating(savedVoiceIDs,id:role.id,saved:true);voiceLibraryCategory="saved";libraryOptions.selected=role.id}.disabled(m.busy);Spacer();Text("\(voiceLibraryRows.count)").foregroundStyle(.secondary)}.padding(12)
                Menu {
                    Button(L("刪除選中聲線"),role:.destructive) {clearLibraryVoices(Set([libraryOptions.selected]))}.disabled(!m.voiceProfiles.contains {$0.id==libraryOptions.selected})
                    Button(L("清空歷史參考"),role:.destructive) {clearLibraryVoices(Set(m.voiceProfiles.map(\.id)).subtracting(SavedVoiceLibrary.ids(savedVoiceIDs)))}.disabled(!m.voiceProfiles.contains {!SavedVoiceLibrary.ids(savedVoiceIDs).contains($0.id)})
                    Button(L("清空全部聲線"),role:.destructive) {clearLibraryVoices(Set(m.voiceProfiles.map(\.id)))}.disabled(m.voiceProfiles.isEmpty)
                } label:{Label(L("清理聲線"),systemImage:"trash")}.disabled(m.busy).padding(.horizontal,12).padding(.bottom,12)
                Divider()
                ScrollView {LazyVStack(spacing:1) {
                    ForEach(voiceLibraryRows) {role in
                        Button {libraryOptions.selected=role.id} label:{HStack(spacing:12) {Group {if let image=roleImage(role.avatar) {Image(nsImage:image).resizable().scaledToFit()} else {Image(systemName:"person.crop.rectangle").font(.system(size:30)).foregroundStyle(roleColor(role.id))}}.frame(width:65,height:80);VStack(alignment:.leading,spacing:5) {Text(localizedRoleName(role.name)).font(.system(size:15,weight:.medium));Text(L(role.ready ? "參考錄音已備妥":"未設定參考聲音")).font(.system(size:13)).foregroundStyle(.secondary)};Text(String(role.id.prefix(6))).font(.system(size:10,design:.monospaced)).foregroundStyle(.secondary)}.padding(12).frame(maxWidth:.infinity,alignment:.leading).background(libraryOptions.selected==role.id ? accent.opacity(0.14):.clear)}.buttonStyle(.plain)
                    }
                }}
                Text(L(voiceLibraryCategory == "saved" ? "只顯示你主動保存嘅聲線；每條片仍需分析對白同角色。":"歷史參考可能來自唔同影片或重試；同名角色唔代表同一人。")).font(.system(size:12)).foregroundStyle(.secondary).padding(12)
                CompanionDock(model:m)
            }.frame(width:280).background(FrameChrome(sidebar:true))
            Divider()
            ScrollView {
                VStack(alignment:.leading,spacing:22) {
                    if let index=m.voiceProfiles.firstIndex(where:{$0.id==libraryOptions.selected}) {
                        HStack {Text(localizedRoleName(m.voiceProfiles[index].name)).font(.title2.bold());Spacer();Button(L(voiceLibraryCategory == "saved" ? "移回歷史參考":"保存為常用聲線")) {let save=voiceLibraryCategory != "saved";savedVoiceIDs=SavedVoiceLibrary.updating(savedVoiceIDs,id:m.voiceProfiles[index].id,saved:save);voiceLibraryCategory=save ? "saved":"history"}.disabled(m.busy)}
                        voiceCard(index)
                    } else {
                        Text(L(voiceLibraryCategory == "saved" ? "建立你嘅常用聲線":"選擇歷史參考")).font(.title2.bold())
                        Text(L("每條片會自行分析角色。呢度只用嚟保存你想跨影片重用嘅參考錄音，例如同一角色下一集沿用同一把聲。"))
                        Button(L("瀏覽歷史參考")) {voiceLibraryCategory="history";selectLibraryVoice()}
                        Button(L("返回工作區修改本片角色")) {m.section = .studio}.foregroundStyle(.secondary)
                    }
                }.padding(24).frame(maxWidth:.infinity,alignment:.leading)
            }.frame(maxWidth:.infinity)
            Divider()
            ScrollView {
                VStack(alignment:.leading,spacing:22) {
                    Text(L("試聽設定")).font(.headline)
                    Picker(L("配音引擎"),selection:$m.ttsBackend) {ForEach(VoiceEngineChoice.all) {Text($0.title).tag($0.id)}}
                    Picker(L("試聽語言"),selection:$m.voicePreviewLanguage) {Text(L("廣東話")).tag("yue");Text(L("英文")).tag("en")}.pickerStyle(.segmented)
                    TextField(L("試聽台詞"),text:$m.auditionText,axis:.vertical).textFieldStyle(.roundedBorder).lineLimit(3...6)
                    Button(L("停止試聽")) {m.audioPlayer.pause()}
                    if !m.audioPreviewLabel.isEmpty {Text(m.audioPreviewLabel).foregroundStyle(accent)}
                    if let gpt=m.comparisonGSV,let cosy=m.comparisonCosy {Button("GPT-SoVITS") {m.audition(gpt,label:"GPT-SoVITS")};Button("CosyVoice") {m.audition(cosy,label:"CosyVoice")}}
                    Divider()
                    Text(L("影片參考取樣")).font(.headline)
                    Text(m.video?.lastPathComponent ?? L("未選擇影片")).font(.system(size:13)).lineLimit(2)
                    TextField(L("參考開始時間（分:秒）"),text:$m.referenceStart).textFieldStyle(.roundedBorder)
                    Stepper(L("取樣秒數")+" \(Int(m.referenceSeconds))",value:$m.referenceSeconds,in:3...10,step:1)
                    if m.ttsBackend=="gpt-sovits" {Picker(L("配音裝置"),selection:$m.gsvDevice) {Text("Apple Silicon GPU · MPS").tag("mps");Text(L("CPU · 相容模式，較慢")).tag("cpu")}}
                    Divider()
                    Toggle(L("新轉換根據原聲自動配對全部角色"),isOn:$m.autoSpeakers)
                    if m.reviewURL != nil {Button(L("重新自動配對目前稿件")) {m.autoAssignReview()}}
                    Button(L("返回剪輯工作區")) {m.section = .studio}
                    Button(L("開啟模型中心")) {m.section = .environment}
                }.padding(24).frame(maxWidth:.infinity,alignment:.leading).disabled(m.busy)
            }.frame(width:380).background(StudioPalette.panel)
        }.onAppear {selectLibraryVoice()}
        .onChange(of:voiceLibraryCategory) {_ in selectLibraryVoice()}
        .onChange(of:libraryOptions.search) {_ in selectLibraryVoice()}
        .onChange(of:m.voiceProfiles.map(\.id)) {_ in selectLibraryVoice()}
    }
}
