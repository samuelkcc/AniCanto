import SwiftUI
import AppKit
import AVKit
import UniformTypeIdentifiers

@MainActor final class RoleManagerState:ObservableObject {
    @Published var roleID=""
    @Published var search=""
    @Published var replacing=false
    @Published var wholeRole=false
    @Published var cropping=false
    @Published var frame:NSImage?
    @Published var frameLoading=false
    @Published var frameKey=""
    @Published var unused=false
    @Published var mode="album"
    @Published var photoSize=170.0
    @Published var previewPortrait:RolePortrait?
    @Published var frameTime:Double?
    @Published var observations:[ObservedCharacterHead]=[]
    var draftURL:URL?
    @Published var draftError:String?
    @Published var draft=RoleAssignmentDraft() {didSet {
        guard let draftURL else{return}
        do {try JSONEncoder().encode(draft).write(to:draftURL,options:.atomic);draftError=nil}
        catch {draftError=error.localizedDescription}
    }}
    func configureDraft(_ url:URL) {
        guard draftURL != url else{return}
        let saved=(try? Data(contentsOf:url)).flatMap {try? JSONDecoder().decode(RoleAssignmentDraft.self,from:$0)}
        draftURL=url
        if let saved {draft=saved}
    }
    @Published var selectedTarget=""
    @Published var reviewingChanges=false
    @Published var regenerate=true
}
struct ObservedCharacterHead:Decodable,Identifiable {
    var avatar:String
    var sourceFrame:String
    var time:Double
    var visualId:String
    var id:String {avatar}
}
private struct ObservedCharacterAtlas:Decodable {
    struct Entry:Decodable {var visualId:String;var observations:[ObservedCharacterHead]?}
    var gallery:[Entry]
}
@MainActor final class RoleCropState:ObservableObject {
    @Published var area=CGRect(x:0.25,y:0.15,width:0.5,height:0.7)
}

@MainActor enum RoleManagerWindow {
    private static var controller:NSWindowController?
    static func present(model:AppModel,editor:ProjectEditor,live:LiveVideoPreview?=nil,roleID:String?=nil) {
        guard let prepared=preparedEditor(model:model,editor:editor,live:live) else{return}
        editor.rolePageEditor=prepared === editor ? nil:prepared
        if let roleID {editor.rolePageState.roleID=roleID}
        withAnimation(.easeInOut(duration:0.2)) {editor.workspacePage="roles"}
    }
}
@MainActor private final class RoleManagerController:NSWindowController,NSWindowDelegate {
    let editor:ProjectEditor
    let options:RoleManagerState
    init(window:NSWindow,editor:ProjectEditor,options:RoleManagerState) {self.editor=editor;self.options=options;super.init(window:window);window.delegate=self}
    func windowShouldClose(_ sender:NSWindow)->Bool {
        guard !options.draft.changes.isEmpty else{return true}
        let alert=NSAlert();alert.messageText=L("仍有未提交角色修改")
        alert.informativeText=L("返回檢視修改，或放棄待提交修改。影片配音尚未改動。")
        alert.addButton(withTitle:L("返回"));alert.addButton(withTitle:L("放棄修改"))
        if alert.runModal() == .alertSecondButtonReturn {options.draft.clear();return true}
        return false
    }
    required init?(coder:NSCoder) {fatalError("init(coder:) has not been implemented")}
    func windowWillClose(_ notification:Notification) {
        editor.audio.pause();editor.player.pause()
        do {try editor.save()} catch {editor.error=error.localizedDescription}
        window?.contentView=nil
    }
}

struct RoleManager:View {
    @ObservedObject var model:AppModel
    @ObservedObject var editor:ProjectEditor
    var close:()->Void
    var fullscreen:()->Void
    @StateObject private var state:RoleManagerState
    @StateObject private var referenceOptions=ProjectWorkspaceOptions()
    @StateObject private var thumbnails=RoleFrameThumbnails()
    @AppStorage("savedVoiceProfileIDs") private var savedVoiceIDs=""
    @AppStorage("studioLanguage") private var language="system"
    @AppStorage("studioTheme") private var appearance="system"
    @MainActor init(model:AppModel,editor:ProjectEditor,close:@escaping ()->Void,fullscreen:@escaping ()->Void,options:RoleManagerState?=nil) {
        self.model=model;self.editor=editor;self.close=close;self.fullscreen=fullscreen
        _state=StateObject(wrappedValue:options ?? RoleManagerState())
    }
    private var profile:VoiceProfile? {editor.profiles.first {$0.id==state.roleID}}
    private var rows:[EditSegment] {roleRows(state.roleID)}
    private func roleRows(_ id:String)->[EditSegment] {editor.document?.segments.filter {state.draft.role(for:$0)==id} ?? []}
    private var profileIndex:Int? {editor.profiles.firstIndex {$0.id==state.roleID}}
    private var selectedIsOwn:Bool {editor.document?.segments.first {$0.id==editor.selectedSegment}.map{state.draft.role(for:$0)==state.roleID} ?? false}
    private var independent:Bool {editor.isIndependentVoiceMapping}
    var body:some View {
        VStack(spacing:0) {
            VStack(spacing:10) {
                HStack(spacing:12) {
                    Label(L(editor.voiceManagerTitle),systemImage:independent ? "waveform":"person.3.sequence.fill").font(.title2.bold())
                    Text(editor.selectedRow?.name ?? "").lineLimit(1).foregroundStyle(.secondary)
                    Spacer()
                    if !independent {
                        Picker(L("檢視"),selection:$state.mode) {Text(L("角色總覽")).tag("album");Text(L("配對與修改")).tag("matching")}.labelsHidden().pickerStyle(.segmented).frame(width:240)
                        Button(L(state.mode=="observations" ? "返回總覽":"畫面素材庫")) {state.mode=state.mode=="observations" ? "album":"observations"}
                    }
                    Button(action:fullscreen) {Image(systemName:"arrow.up.left.and.arrow.down.right")}.help(L("全螢幕"))
                    Button(L("完成")) {if state.draft.changes.isEmpty {save();close()} else {state.reviewingChanges=true}}.buttonStyle(StudioButtonStyle(prominent:true))
                }
                HStack(spacing:12) {
                    Button {if !state.draft.history.isEmpty {state.draft.undo()} else {editor.undo()}} label:{Label(L("撤銷"),systemImage:"arrow.uturn.backward")}.disabled((state.draft.history.isEmpty && editor.undoStack.isEmpty) || model.busy || editor.readOnlyPreview)
                    Button {do {try editor.restoreRoleCommit()} catch {editor.error=error.localizedDescription}} label:{Label(L("復原上次角色修改"),systemImage:"clock.arrow.circlepath")}.disabled(!state.draft.changes.isEmpty || !editor.canRestoreRoleCommit || model.busy || editor.readOnlyPreview)
                    Button(L("儲存")) {if state.draft.changes.isEmpty {save()} else {state.reviewingChanges=true}}.disabled(model.busy || editor.readOnlyPreview)
                    Spacer()
                    HStack {Text(L("試聽語言"));Picker(L("試聽語言"),selection:$editor.previewLanguage) {Text(L("廣東話")).tag("yue");Text(L("英文")).tag("en")}.pickerStyle(.segmented).labelsHidden().frame(width:200)}
                    if !state.draft.changes.isEmpty {
                        Button(L("取消待提交修改")) {state.draft.clear()}
                        Button(String(format:L("檢視修改（%d）"),state.draft.changes.count)) {state.reviewingChanges=true}.buttonStyle(StudioButtonStyle(prominent:true))
                    }
                }
            }.padding(14).background(StudioPalette.panel)
            Divider()
            VStack(alignment:.leading,spacing:6) {
                HStack {Text(String(format:L(independent ? "%d 個逐句參考 · %d 段對白":"%d 個聲線角色 · %d 段對白"),editor.profiles.count,editor.document?.segments.count ?? 0));Spacer();Text(String(format:L("待提交修改 %d"),state.draft.changes.count)).foregroundStyle(accent)}
                Text(L(independent ? (editor.voiceStyleMode=="natural" ? "每句獨立配對自然聲線，沒有共用角色分組；選一句試聽或調整聲線。":"每句只用自己的原聲參考，沒有共用角色卡；選一句試聽或修改參考原文。") : "先選角色檢視對白。拖對白到角色卡：改配對；拖角色卡到對白：指定角色；拖角色到另一角色：合併。修改先加入草稿，再檢視及提交。")).font(.caption).foregroundStyle(.secondary)
                if state.mode=="observations" {Text(L("畫面素材庫只用來選封面，圖片不代表聲線身份。")).font(.caption).foregroundStyle(.secondary)}
            }.padding(.horizontal,14).padding(.vertical,8)
            if editor.readOnlyPreview {Text(L("已分析角色預覽 · 完成校稿後可修改配對")).foregroundStyle(.secondary).padding(8)}
            if independent {independentMapping} else {GeometryReader {g in
                VStack(spacing:0) {
                    if state.mode=="matching" {castStrip;Divider()}
                    HStack(spacing:0) {
                        if state.mode != "matching" {
                            Group {if state.mode=="observations" {observationsLibrary} else {library}}.frame(width:min(600,max(370,g.size.width*0.29)))
                            Divider()
                        }
                        VStack(spacing:0) {
                            if let p=profile,let i=profileIndex {
                                identity(p,index:i).frame(maxHeight:.infinity)
                                Divider()
                                auditions(p,index:i)
                            } else {ContentUnavailableView(L("未有角色"),systemImage:"person.crop.rectangle")}
                        }.frame(maxWidth:.infinity,maxHeight:.infinity).background(StudioPalette.panel)
                        Divider()
                        dialogueList.frame(width:min(460,max(300,g.size.width*0.25)))
                    }
                }
            }}
            if let error=state.draftError {Text(error).foregroundStyle(.red).padding(8)}
            if let error=editor.error {Text(error).foregroundStyle(.red).lineLimit(2).padding(8)}
        }.background(StudioPalette.panel).font(.system(size:14)).buttonStyle(StudioButtonStyle()).tint(accent)
        .id(language)
        .preferredColorScheme(appearance=="dark" ? .dark:appearance=="light" ? .light:nil)
        .onAppear {if !editor.profiles.contains(where:{$0.id==state.roleID}) {state.roleID=editor.document?.segments.first {$0.id==editor.selectedSegment}?.speakerId ?? editor.profiles.first?.id ?? ""};if !independent {loadObservations()}}
        .onChange(of:state.roleID) {_ in state.previewPortrait=nil;if !independent {loadFrame()}}
        .onChange(of:editor.document?.review) {_ in state.roleID=editor.profiles.first?.id ?? "";state.replacing=false;state.previewPortrait=nil;state.draft.clear();if !independent {loadObservations()}}
        .onChange(of:editor.profiles) {_ in editor.dirty=true;editor.scheduleSave()}
        .onDisappear {editor.audio.pause();editor.player.pause();save()}
        .onReceive(Timer.publish(every:5,on:.main,in:.common).autoconnect()) {_ in
            if editor.readOnlyPreview,model.busy,let row=editor.selectedRow {_ = RoleManagerWindow.loadPreparedRoles(model:model,row:row,into:editor);if !independent {loadObservations()}}
        }
        .sheet(isPresented:$state.replacing) {replacementPicker}
        .sheet(isPresented:$state.reviewingChanges) {changeReview}
        .sheet(isPresented:$state.cropping) {
            if let frame=state.frame {RolePortraitCrop(image:frame,apply:{rect in savePortrait(frame,rect:rect);state.cropping=false},cancel:{state.cropping=false})}
        }
    }
    private var filteredProfiles:[VoiceProfile] {
        editor.profiles.filter {p in (state.unused || editor.readOnlyPreview || editor.document?.segments.contains(where:{state.draft.role(for:$0)==p.id})==true) && (state.search.isEmpty || localizedRoleName(p.name).localizedCaseInsensitiveContains(state.search))}
    }
    private func loadObservations() {
        state.observations=[]
        guard let review=editor.document?.review else{return}
        let path=URL(fileURLWithPath:review).deletingLastPathComponent().appendingPathComponent("visual-photo-atlas.json")
        guard let data=try? Data(contentsOf:path),let atlas=try? JSONDecoder().decode(ObservedCharacterAtlas.self,from:data) else{return}
        state.observations=atlas.gallery.flatMap {$0.observations ?? []}
    }
    private var observationsLibrary:some View {
        VStack(alignment:.leading,spacing:12) {
            Text(L("全片頭像")).font(.headline)
            Picker(L("角色"),selection:$state.roleID) {ForEach(editor.profiles) {p in Text(localizedRoleName(p.name)).tag(p.id)}}
            ScrollView {LazyVGrid(columns:[GridItem(.adaptive(minimum:state.photoSize),spacing:12)],spacing:12) {
                ForEach(state.observations) {head in
                    Button {state.previewPortrait=RolePortrait(avatar:head.avatar,sourceFrame:head.sourceFrame,time:head.time);loadFrame(time:head.time,source:head.sourceFrame)} label:{
                        VStack(spacing:8) {
                            if let image=roleImage(head.avatar) {Image(nsImage:image).resizable().scaledToFit().frame(height:state.photoSize)}
                            Text(head.visualId+" · "+studioTimecode(head.time)).font(.system(size:12,design:.monospaced))
                        }.padding(8).background(state.previewPortrait?.avatar==head.avatar ? accent.opacity(0.16):Color.primary.opacity(0.04),in:RoundedRectangle(cornerRadius:8))
                    }.buttonStyle(.plain)
                }
            }}
            if state.observations.isEmpty {Text(L("尚未有可辨識頭像")).foregroundStyle(.secondary)}
        }.padding(14)
    }
    private var library:some View {
        VStack(spacing:0) {
            HStack {Text(L("角色與聲線配對")).font(.headline);Spacer();Text("\(filteredProfiles.count)").foregroundStyle(.secondary)}.padding(14)
            TextField(L("搜尋角色"),text:$state.search).textFieldStyle(.roundedBorder).padding(.horizontal,14).padding(.bottom,12)
            HStack {
                Text(L("相片大小")).font(.caption)
                Slider(value:$state.photoSize,in:140...220).frame(maxWidth:180)
                Spacer()
            }.padding(.horizontal,14).padding(.bottom,10)
            Toggle(L("顯示未使用角色"),isOn:$state.unused).toggleStyle(.checkbox).padding(.horizontal,14).padding(.bottom,8)
            Divider()
            ScrollView {
                VStack(alignment:.leading,spacing:14) {
                    photoGroup(L("聲音與畫面支持"),profiles:filteredProfiles.filter {$0.identityStatus=="audiovisual"})
                    photoGroup(L("只按聲音配對"),profiles:filteredProfiles.filter {$0.identityStatus=="acoustic"})
                    photoGroup(L("待確認聲線"),profiles:filteredProfiles.filter {$0.identityStatus==nil || $0.identityStatus=="provisional"})
                }.padding(12)
            }
        }.background(StudioPalette.panel)
    }
    @ViewBuilder private func photoGroup(_ title:String,profiles:[VoiceProfile])->some View {
        if !profiles.isEmpty {
            HStack {Text(title).font(.headline);Text("\(profiles.count)").foregroundStyle(.secondary)}
            LazyVGrid(columns:[GridItem(.adaptive(minimum:state.photoSize),spacing:12)],spacing:12) {
                ForEach(profiles) {p in Button {state.roleID=p.id} label:{portraitCard(p,selected:p.id==state.roleID)}.buttonStyle(.plain).onDrag {drag("role",id:p.id)}.onDrop(of:[UTType.text],isTargeted:nil) {drop($0,onto:p.id)}}
            }
        }
    }
    private var castStrip:some View {
        ScrollView(.horizontal) {
            HStack(spacing:12) {ForEach(filteredProfiles) {p in
                Button {state.roleID=p.id} label:{portraitCard(p,selected:p.id==state.roleID).frame(width:150)}.buttonStyle(.plain).onDrag {drag("role",id:p.id)}.onDrop(of:[UTType.text],isTargeted:nil) {drop($0,onto:p.id)}
            }}.padding(12)
        }.frame(height:180)
    }
    private var independentMapping:some View {
        HStack(spacing:0) {
            VStack(alignment:.leading,spacing:10) {
                TextField(L("搜尋逐句參考"),text:$state.search).textFieldStyle(.roundedBorder).padding(12)
                ScrollView {LazyVStack(spacing:6) {
                    ForEach(editor.profiles.filter {state.search.isEmpty || $0.name.localizedCaseInsensitiveContains(state.search) || roleRows($0.id).contains {($0.text+" "+$0.original).localizedCaseInsensitiveContains(state.search)}}) {p in
                        Button {
                            state.roleID=p.id
                            if let row=roleRows(p.id).first {editor.selectSegment(row.id)}
                        } label:{
                            HStack(alignment:.top,spacing:10) {
                                Image(systemName:"waveform").foregroundStyle(roleColor(p.id))
                                VStack(alignment:.leading,spacing:5) {
                                    Text(localizedRoleName(p.name)).font(.headline)
                                    if let row=roleRows(p.id).first {Text(studioTimecode(row.start)).font(.caption.monospacedDigit());Text(row.text).font(.caption).lineLimit(2)}
                                    if p.shortReference==true {Text(L("短句參考，需試聽")).font(.caption).foregroundStyle(.orange)}
                                    if !p.ready {Text(L("參考未完成")).font(.caption).foregroundStyle(.orange)}
                                }.frame(maxWidth:.infinity,alignment:.leading)
                            }.padding(12).background(p.id==state.roleID ? roleColor(p.id).opacity(0.16):Color.primary.opacity(0.025),in:RoundedRectangle(cornerRadius:8))
                        }.buttonStyle(.plain)
                    }
                }.padding(12)}
            }.frame(width:310)
            Divider()
            ScrollView {VStack(alignment:.leading,spacing:18) {
                if let p=profile,let i=profileIndex {
                    Text(localizedRoleName(p.name)).font(.title2.bold())
                    Text(L(editor.voiceStyleMode=="natural" ? "本句獨立自然聲線":"本句獨立原聲參考")).font(.caption).foregroundStyle(.secondary)
                    if editor.voiceStyleMode=="clone",p.shortReference==true {Text(L("只補靜音達到引擎所需錄音長度，未借用相鄰對白；有效語音太短時需重新試聽或換參考。")).font(.caption).foregroundStyle(.orange)}
                    ForEach(rows) {row in
                        Text(studioTimecode(row.start)+" – "+studioTimecode(row.end)).font(.caption.monospacedDigit())
                        Text(row.original).foregroundStyle(.secondary).textSelection(.enabled)
                        Text(editor.previewLanguage=="en" ? row.english ?? "":row.text).textSelection(.enabled)
                        HStack {
                            Button(L("原聲（含前後）")) {editor.selectSegment(row.id);editor.playSegment(context:true);if !independent {loadFrame()}}
                            Button(L("分離（含前後）")) {editor.selectSegment(row.id);editor.playDialogue(context:true);if !independent {loadFrame()}}.disabled(editor.dialoguePath==nil)
                            ForEach(VoiceEngineChoice.all) {engine in
                                Button("▶ "+engine.shortTitle) {editor.selectSegment(row.id);editor.previewEngine=engine.id;editor.playEngine(engine.id)}.disabled(editor.deliveredTake(engine.id,segmentID:row.id)==nil)
                            }
                        }
                    }
                    Divider();auditions(p,index:i)
                } else {Text(L("選擇一句檢視原聲參考。"))}
            }.padding(20).frame(maxWidth:.infinity,alignment:.leading)}
        }
    }
    private func portraitCard(_ p:VoiceProfile,selected:Bool)->some View {
        VStack(spacing:8) {
            portrait(p,height:state.mode=="matching" ? 95:state.photoSize)
            Text(String(format:"R%02d",(editor.profiles.firstIndex {$0.id==p.id} ?? 0)+1)+" · "+localizedRoleName(p.name)).font(.system(size:14,weight:.semibold)).lineLimit(2)
            Text(p.identityLabel).font(.caption).foregroundStyle(.secondary)
            if roleImage(p.avatar)==nil {Text(L("候選畫面")).font(.caption).foregroundStyle(.secondary)}
            Text(String(format:L("%d 段對白"),roleRows(p.id).count)).font(.caption).foregroundStyle(.secondary)
        }.padding(10).frame(maxWidth:.infinity).background(roleColor(p.id).opacity(selected ? 0.22:0.08),in:RoundedRectangle(cornerRadius:10))
        .overlay(RoundedRectangle(cornerRadius:10).stroke(selected ? roleColor(p.id):.clear,lineWidth:2))
    }
    @ViewBuilder private func portrait(_ p:VoiceProfile,height:Double)->some View {
        if let image=roleImage(p.avatar) {Image(nsImage:image).resizable().scaledToFit().frame(maxWidth:.infinity).frame(height:height)}
        else if let image=roleImage(p.sourceFrame) {Image(nsImage:image).resizable().scaledToFit().frame(maxWidth:.infinity).frame(height:height)}
        else {
            let originals=editor.document?.segments.filter{$0.speakerId==p.id} ?? []
            sourceThumbnail((originals.isEmpty ? roleRows(p.id):originals).max(by:{$0.end-$0.start<$1.end-$1.start}),height:height)
        }
    }
    private func identity(_ p:VoiceProfile,index:Int)->some View {
        VStack(alignment:.leading,spacing:14) {
            if state.mode != "matching" {
            HStack(alignment:.top,spacing:18) {
                VStack(spacing:8) {
                    portrait(p,height:190).frame(width:170)
                    Button(L("更換大頭相")) {state.cropping=true}.disabled(state.frame==nil || model.busy || editor.readOnlyPreview)
                    if p.avatar != nil {Button(L("移除封面")) {editor.profiles[index].avatar=nil;state.previewPortrait=nil;save()}.disabled(model.busy || editor.readOnlyPreview)}
                }
                VStack(alignment:.leading,spacing:12) {
                    TextField(L("角色名稱"),text:Binding(get:{localizedRoleName(editor.profiles[index].name)},set:{editor.profiles[index].name=$0})).font(.title2.bold()).textFieldStyle(.roundedBorder).disabled(model.busy || editor.readOnlyPreview)
                    Text(String(format:L("%d 段對白"),rows.count)).foregroundStyle(.secondary)
                    HStack {
                        Button(L("重新配對呢段")) {state.wholeRole=false;state.replacing=true}.disabled(!selectedIsOwn || model.busy || editor.readOnlyPreview)
                        Button(L("合併到其他角色")) {state.wholeRole=true;state.replacing=true}.disabled(rows.isEmpty || model.busy || editor.readOnlyPreview)
                    }
                    Button(L(SavedVoiceLibrary.ids(savedVoiceIDs).contains(p.id) ? "已存入常用聲線":"保存為常用聲線")) {
                        do {try model.saveProjectVoice(p);savedVoiceIDs=SavedVoiceLibrary.updating(savedVoiceIDs,id:p.id,saved:true)} catch {editor.error=error.localizedDescription}
                    }.disabled(model.busy || !p.ready)
                    if let portraits=p.portraits,!portraits.isEmpty {
                        ScrollView(.horizontal) {HStack(spacing:8) {ForEach(portraits) {item in
                            if let image=roleImage(item.avatar) {
                                Button {state.previewPortrait=item;loadFrame(time:item.time,source:item.sourceFrame)} label:{
                                    VStack(spacing:4) {Image(nsImage:image).resizable().scaledToFit().frame(width:85,height:88);Text(studioTimecode(item.time)).font(.system(size:10,design:.monospaced))}
                                        .padding(4).background(state.previewPortrait?.id==item.id ? accent.opacity(0.16):.clear,in:RoundedRectangle(cornerRadius:6))
                                }.buttonStyle(.plain)
                            }
                        }}}
                    }
                    if let item=state.previewPortrait {
                        Button(L(item.avatar==p.avatar ? "目前封面":"設為封面")) {
                            editor.profiles[index].avatar=item.avatar;editor.profiles[index].sourceFrame=item.sourceFrame;editor.profiles[index].avatarTime=item.time;save()
                        }.disabled(item.avatar==p.avatar || model.busy || editor.readOnlyPreview)
                    }
                }
            }
            } else {
                HStack(spacing:12) {
                    RoleAvatarBadge(profile:p)
                    Spacer()
                    Button(L("重新配對呢段")) {state.wholeRole=false;state.replacing=true}.disabled(!selectedIsOwn || model.busy || editor.readOnlyPreview)
                    Button(L("角色相簿")) {state.mode="album"}
                }
            }
            HStack {Text(L("原片畫面")).font(.headline);Spacer();if let time=state.frameTime {Text(studioTimecode(time+editor.offset)).font(.system(size:13,design:.monospaced))}}
            ZStack {
                Color.black
                if let frame=state.frame {Image(nsImage:frame).resizable().scaledToFit()}
                else if state.frameLoading {ProgressView()}
                else {Text(L("未有角色畫面")).foregroundStyle(.white.opacity(0.7))}
            }.frame(maxWidth:.infinity,maxHeight:.infinity).clipShape(RoundedRectangle(cornerRadius:8))
        }.padding(18)
    }
    private func auditions(_ p:VoiceProfile,index:Int)->some View {
        VStack(alignment:.leading,spacing:12) {
            HStack {Text(L(independent ? "本句參考設定":"角色聲音設定")).font(.headline);Spacer();Button(L("停止")) {editor.audio.pause();editor.player.pause();editor.auditionLabel=""}}
            if !independent {Text(L("逐句試聽在右側對白清單；此區只設定角色參考聲音。")).font(.caption).foregroundStyle(.secondary)}
            if independent {Button(L("聽參考")) {editor.playReference(p,engine:editor.previewEngine)}.disabled(!p.ready)}
            if editor.voiceStyleMode=="natural" {NaturalRoleVoiceControls(editor:editor,profileID:p.id)}
            if editor.voiceStyleMode=="clone",!independent,selectedIsOwn,let s=editor.document?.segments.first(where:{$0.id==editor.selectedSegment}) {
                Button(L("用這句分離原聲作角色參考")) {editor.useOriginalReference(segment:s,profileID:p.id,ffmpeg:model.engine.ffmpeg)}
                    .disabled(editor.dialoguePath==nil || s.end-s.start<3 || s.end-s.start>10 || model.busy || editor.readOnlyPreview)
                Text(L("先聽分離對白，選同角色 3–10 秒單人清晰句子。音效殘留仍需覆聽；圖片不能產生聲線。")).font(.caption).foregroundStyle(.secondary)
            }
            if !editor.auditionLabel.isEmpty {Text(editor.auditionLabel).foregroundStyle(roleColor(p.id))}
            DisclosureGroup(L("參考錄音設定")) {
                TextField(L("參考聲音原文"),text:$editor.profiles[index].promptText).textFieldStyle(.roundedBorder)
                Button(L("更換 WAV")) {let panel=NSOpenPanel();panel.allowedContentTypes=[.wav];if panel.runModal() == .OK,let url=panel.url {editor.profiles[index].reference=url.path;editor.profiles[index].shortReference=nil;editor.profiles[index].mixedReference=nil;editor.profiles[index].referenceQuality=nil;editor.profiles[index].referenceCandidates=nil;editor.profiles[index].referenceRanges=nil;editor.profiles[index].transcriptSource=nil;editor.profiles[index].originalReference=nil}}
                EngineReferenceControls(editor:editor,index:index,options:referenceOptions)
            }.disabled(model.busy || editor.readOnlyPreview)
        }.padding(18)
    }
    private var dialogueList:some View {
        VStack(spacing:0) {
            HStack {Text(L("角色對白")).font(.headline);Spacer();Text("\(rows.count)")}.padding(14)
            Divider()
            ScrollView {LazyVStack(spacing:6) {ForEach(rows) {s in
                VStack(alignment:.leading,spacing:10) {
                    HStack(alignment:.top,spacing:10) {
                        sourceThumbnail(s,height:60).frame(width:96)
                        VStack(alignment:.leading,spacing:6) {
                            Text(studioTimecode(s.start)).font(.system(size:12,design:.monospaced)).foregroundStyle(.secondary)
                            Text(s.original).lineLimit(2).foregroundStyle(.secondary)
                            Text(editor.previewLanguage=="en" ? s.english ?? "":s.text).lineLimit(3)
                        }.frame(maxWidth:.infinity,alignment:.leading)
                    }
                    HStack(spacing:6) {
                        Button(L("參考")) {editor.selectSegment(s.id);if let p=profile {editor.playReference(p,engine:editor.previewEngine)};loadFrame(time:s.start)}.disabled(profile?.ready != true)
                        Button(L("原聲")) {editor.selectSegment(s.id);editor.playSegment(context:true);if !independent {loadFrame()}}.help(L("原聲（含前後）"))
                        Button(L("分離")) {editor.selectSegment(s.id);editor.playDialogue(context:true);if !independent {loadFrame()}}.disabled(editor.dialoguePath==nil).help(L("分離（含前後）"))
                    }.controlSize(.small)
                    LazyVGrid(columns:[GridItem(.adaptive(minimum:85))],alignment:.leading,spacing:6) {
                        ForEach(VoiceEngineChoice.all) {engine in
                            Button {editor.selectSegment(s.id);editor.previewEngine=engine.id;editor.playEngine(engine.id)} label:{Label(engine.shortTitle,systemImage:"play.fill").font(.caption).frame(maxWidth:.infinity,alignment:.leading)}
                                .disabled(editor.deliveredTake(engine.id,segmentID:s.id)==nil || state.draft.changes[s.id] != nil)
                        }
                    }.controlSize(.small)
                    if editor.deliveredTake(editor.previewEngine,segmentID:s.id)==nil {Text(editor.cueAudioStatus(editor.previewEngine,segmentID:s.id)).font(.caption).foregroundStyle(.secondary)}
                    if state.draft.changes[s.id] != nil {Text(L("待提交配對")).font(.caption).foregroundStyle(accent)}
                }.padding(12).background(roleColor(state.roleID).opacity(editor.selectedSegment==s.id ? 0.2:0.06),in:RoundedRectangle(cornerRadius:8))
                .contentShape(Rectangle()).onTapGesture {editor.selectSegment(s.id);state.previewPortrait=nil;loadFrame(time:s.start)}
                .onDrag {drag("line",id:s.id)}
                .onDrop(of:[UTType.text],isTargeted:nil) {drop($0,onLine:s.id)}
            }}.padding(12)}
        }.background(StudioPalette.panel)
    }
    private var replacementPicker:some View {
        VStack(spacing:12) {
            HStack {Text(L(state.wholeRole ? "合併到其他角色":"重新配對呢段")).font(.title2.bold());Spacer();Button(L("取消")) {state.replacing=false}}
            ScrollView {LazyVGrid(columns:[GridItem(.adaptive(minimum:155),spacing:12)],spacing:12) {
                ForEach(editor.profiles.filter {$0.id != state.roleID}) {p in
                    Button {state.selectedTarget=p.id} label:{portraitCard(p,selected:state.selectedTarget==p.id)}.buttonStyle(.plain)
                }
            }}
            Button(L("加入待提交修改")) {
                let lines=state.wholeRole ? rows:rows.filter{$0.id==editor.selectedSegment}
                state.draft.stage(state.selectedTarget,segments:lines);state.replacing=false;state.selectedTarget=""
            }.buttonStyle(StudioButtonStyle(prominent:true)).disabled(state.selectedTarget.isEmpty || model.busy || editor.readOnlyPreview)
        }.padding(20).frame(width:850,height:650).background(StudioPalette.panel)
        .onAppear {state.selectedTarget=""}
    }
    private var changeReview:some View {
        VStack(spacing:14) {
            HStack {Text(L("提交角色修改")).font(.title2.bold());Spacer();Button(L("返回編輯")) {state.reviewingChanges=false}}
            ScrollView {LazyVStack(alignment:.leading,spacing:10) {
                ForEach((editor.document?.segments ?? []).filter{state.draft.changes[$0.id] != nil}) {s in
                    if let change=state.draft.changes[s.id] {
                        HStack(alignment:.top,spacing:12) {
                            sourceThumbnail(s,height:55).frame(width:95)
                            VStack(alignment:.leading,spacing:5) {
                                Text(studioTimecode(s.start)+" · "+roleName(change.source)+" → "+roleName(change.target)).bold()
                                Text(s.text).lineLimit(2)
                            }
                            Spacer()
                            changePortrait(change.source)
                            Image(systemName:"arrow.right").foregroundStyle(.secondary)
                            changePortrait(change.target)
                        }.frame(maxWidth:.infinity,alignment:.leading).padding(10).background(accent.opacity(0.07),in:RoundedRectangle(cornerRadius:8))
                    }
                }
            }}
            Toggle(L("提交後重新配音並輸出影片"),isOn:$state.regenerate)
            Button(L("確認提交")) {commitChanges()}.buttonStyle(StudioButtonStyle(prominent:true)).disabled(state.draft.changes.isEmpty || model.busy || editor.readOnlyPreview)
        }.padding(22).frame(width:900,height:min(760,max(320,Double(state.draft.changes.count)*100+200))).background(StudioPalette.panel)
    }
    @ViewBuilder private func changePortrait(_ id:String)->some View {
        if let p=editor.profiles.first(where:{$0.id==id}) {
            VStack(spacing:4) {portrait(p,height:55);Text(roleName(id)).font(.caption).lineLimit(1)}.frame(width:85)
        }
    }
    private func roleName(_ id:String)->String {localizedRoleName(editor.profiles.first{$0.id==id}?.name ?? id)}
    private func commitChanges() {
        do {
            try editor.commitRoles(Array(state.draft.changes.values));state.draft.clear();state.reviewingChanges=false
            if state.regenerate {model.submitEditor(preserveProjectEngines:true)}
        } catch {editor.error=error.localizedDescription}
    }
    private func drag(_ kind:String,id:String)->NSItemProvider {NSItemProvider(object:RoleDragPayload(kind:kind,id:id,review:editor.document?.review ?? "").text as NSString)}
    private func drop(_ providers:[NSItemProvider],onto role:String?=nil,onLine line:String?=nil)->Bool {
        guard !model.busy,!editor.readOnlyPreview,let provider=providers.first else{return false}
        let review=editor.document?.review
        provider.loadObject(ofClass:NSString.self) {object,_ in
            guard let raw=object as? String else{return}
            Task {@MainActor in
                guard !model.busy,!editor.readOnlyPreview,editor.document?.review==review,let payload=RoleDragPayload.parse(raw,review:review) else{return}
                if payload.kind=="line",let role,let s=editor.document?.segments.first(where:{$0.id==payload.id}) {
                    state.draft.stage(role,segments:[s])
                } else if payload.kind=="role" {
                    let dragged=payload.id
                    guard editor.profiles.contains(where:{$0.id==dragged}) else{return}
                    if let line,let s=editor.document?.segments.first(where:{$0.id==line}) {state.draft.stage(dragged,segments:[s])}
                    else if let role,role != dragged {state.draft.stage(role,segments:roleRows(dragged))}
                }
            }
        }
        return true
    }
    @ViewBuilder private func sourceThumbnail(_ segment:EditSegment?,height:Double)->some View {
        if let segment {
            let video=editor.document?.videoOverride ?? editor.config["video"] as? String ?? ""
            let time=editor.offset+segment.start+(segment.end-segment.start)*0.5
            let key=thumbnails.key(video:video,time:time)
            Group {
                if let image=thumbnails.images[key] {Image(nsImage:image).resizable().scaledToFit()}
                else {Image(systemName:"photo").foregroundStyle(.secondary)}
            }.frame(maxWidth:.infinity).frame(height:height)
                .onAppear {thumbnails.request(video:video,time:time,ffmpeg:model.engine.ffmpeg,folder:editor.draftURL?.deletingLastPathComponent())}
                .onChange(of:key) {_ in thumbnails.request(video:video,time:time,ffmpeg:model.engine.ffmpeg,folder:editor.draftURL?.deletingLastPathComponent())}
        } else {Image(systemName:"person.crop.rectangle").foregroundStyle(.secondary).frame(maxWidth:.infinity).frame(height:height)}
    }
    private func save() {do {try editor.save()} catch {editor.error=error.localizedDescription}}
    private func loadFrame(time:Double?=nil,source:String?=nil) {
        guard let p=profile else{state.frame=nil;return}
        state.frame=nil;state.frameLoading=false;state.frameKey=UUID().uuidString;let key=state.frameKey
        let base=time ?? p.avatarTime ?? p.referenceRanges?.first?.first ?? rows.first?.start ?? 0
        state.frameTime=base
        if let image=roleImage(source ?? (time==nil ? p.sourceFrame:nil)) {state.frame=image;return}
        let at=base+editor.offset
        let video=editor.document?.videoOverride ?? editor.config["video"] as? String ?? ""
        let ffmpeg=model.engine.ffmpeg
        state.frameLoading=true
        Task {
            let bytes=await Task.detached(priority:.utility) { ()->Data? in
                let process=Process(),pipe=Pipe();process.executableURL=ffmpeg
                process.arguments=["-v","error","-ss",String(at),"-i",video,"-frames:v","1","-vf","scale=1280:-2","-f","image2pipe","-c:v","mjpeg","pipe:1"]
                process.standardOutput=pipe;process.standardError=FileHandle.nullDevice
                do {try process.run();let data=pipe.fileHandleForReading.readDataToEndOfFile();process.waitUntilExit();return process.terminationStatus==0 ? data:nil} catch {return nil}
            }.value
            if state.frameKey==key {state.frame=bytes.flatMap {NSImage(data:$0)};state.frameLoading=false}
        }
    }
    private func savePortrait(_ image:NSImage,rect:CGRect) {
        guard !editor.readOnlyPreview,let i=profileIndex,let folder=editor.draftURL?.deletingLastPathComponent(),let cg=image.cgImage(forProposedRect:nil,context:nil,hints:nil),
              let crop=cg.cropping(to:CGRect(x:rect.minX*Double(cg.width),y:rect.minY*Double(cg.height),width:rect.width*Double(cg.width),height:rect.height*Double(cg.height))) else{return}
        do {
            let directory=folder.appendingPathComponent("role-images");try FileManager.default.createDirectory(at:directory,withIntermediateDirectories:true)
            let key=UUID().uuidString,portrait=directory.appendingPathComponent(key+".jpg"),source=directory.appendingPathComponent(key+"-frame.jpg")
            guard let cropData=NSBitmapImageRep(cgImage:crop).representation(using:.jpeg,properties:[:]),let original=NSBitmapImageRep(cgImage:cg).representation(using:.jpeg,properties:[:]) else{return}
            try cropData.write(to:portrait,options:.atomic);try original.write(to:source,options:.atomic)
            let time=state.frameTime ?? editor.profiles[i].avatarTime ?? rows.first?.start ?? 0
            let item=RolePortrait(avatar:portrait.path,sourceFrame:source.path,time:time)
            editor.profiles[i].avatar=item.avatar;editor.profiles[i].sourceFrame=item.sourceFrame
            editor.profiles[i].avatarTime=time
            editor.profiles[i].portraits=(editor.profiles[i].portraits ?? [])+[item];save()
        } catch {editor.error=error.localizedDescription}
    }
}

struct RolePortraitCrop:View {
    let image:NSImage
    var apply:(CGRect)->Void
    var cancel:()->Void
    @StateObject private var crop=RoleCropState()
    var body:some View {
        VStack(spacing:16) {
            HStack {Text(L("框選角色大頭相")).font(.title2.bold());Spacer();Button(L("取消"),action:cancel);Button(L("使用呢張大頭相")) {apply(crop.area)}.buttonStyle(StudioButtonStyle(prominent:true))}
            GeometryReader {g in
                let scale=min(g.size.width/image.size.width,g.size.height/image.size.height)
                let width=image.size.width*scale,height=image.size.height*scale
                ZStack(alignment:.topLeading) {
                    Image(nsImage:image).resizable().frame(width:width,height:height)
                    Rectangle().fill(.black.opacity(0.16))
                    Rectangle().stroke(.white,lineWidth:3).background(.purple.opacity(0.12)).frame(width:crop.area.width*width,height:crop.area.height*height).offset(x:crop.area.minX*width,y:crop.area.minY*height)
                }.frame(width:width,height:height).contentShape(Rectangle()).gesture(DragGesture().onChanged {v in
                    let x=min(1,max(0,v.startLocation.x/width)),y=min(1,max(0,v.startLocation.y/height))
                    let endX=min(1,max(0,v.location.x/width)),endY=min(1,max(0,v.location.y/height))
                    crop.area=CGRect(x:min(x,endX),y:min(y,endY),width:max(0.03,abs(endX-x)),height:max(0.03,abs(endY-y))).intersection(CGRect(x:0,y:0,width:1,height:1))
                }).frame(maxWidth:.infinity,maxHeight:.infinity)
            }
        }.padding(20).frame(width:1000,height:700).background(StudioPalette.panel)
    }
}
