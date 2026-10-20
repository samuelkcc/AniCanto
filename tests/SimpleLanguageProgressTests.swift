import SwiftUI
import AppKit

@main struct SimpleLanguageProgressTests {
 @MainActor static func main() throws {
  let qa=URL(fileURLWithPath:FileManager.default.currentDirectoryPath+"/.build/qa261")
  let root=qa.appendingPathComponent("native-data")
  precondition(ProcessInfo.processInfo.environment["SAM_CANTO_DATA"]==root.path)
  NSApplication.shared.setActivationPolicy(.prohibited)
  UserDefaults.standard.set("zh-HK",forKey:"studioLanguage")
  UserDefaults.standard.set("simple",forKey:"studioInterfaceMode")
  UserDefaults.standard.set("drama3",forKey:"simpleVoiceEngine")
  UserDefaults.standard.set("yue",forKey:"simpleDubLanguage")
  UserDefaults.standard.set("yue,original",forKey:"simpleSubtitleModes")
  UserDefaults.standard.set(false,forKey:"showStudioCompanion")
  for languages in [["yue"],["en"],["yue","en"]] {
   let choices=SimpleVoicePlaybackOption.choices(takes:[],seconds:0,selected:"drama3",languages:languages)
   precondition(Set(choices.map(\.language))==Set(languages))
   precondition(choices.allSatisfy {$0.engine.id=="drama3"})
  }
  precondition(SimpleVoicePlaybackOption.choices(takes:[],seconds:0,selected:"wsyue",languages:["yue","en"]).map(\.language)==["yue"])
  let takes=[ProcessingVoiceTake(engine:"cosyvoice3",language:"yue",path:"ready.wav",text:"出發啦",speakerID:"role",start:1,end:3,length:2),ProcessingVoiceTake(engine:"drama3",language:"en",path:"other.wav",text:"Go",speakerID:"role",start:1,end:3,length:2)]
  let choices=SimpleVoicePlaybackOption.choices(takes:takes,seconds:2,selected:"drama3",languages:["yue"])
  precondition(Set(choices.map(\.id))==Set(["cosyvoice3:yue","drama3:yue"]),"No phantom English waiting button, even with older English takes")
  precondition(SimpleVoicePlaybackOption.choices(takes:takes,seconds:10,selected:"drama3",languages:["yue"]).map(\.id)==["drama3:yue"])
  precondition(SimpleProgressStatus(stage:"分離",detail:"拆開人聲",busy:true,paused:false,error:nil).title==L("正在分離日文人聲同背景音樂"))
  precondition(SimpleProgressStatus(stage:"配音",detail:"84/250",busy:true,paused:false,error:nil,languages:["en"]).title.contains(L("英文")))
  precondition(SimpleProgressStatus(stage:"輸出驗證",detail:"檢查音軌",busy:true,paused:false,error:nil).title==L("正在檢查最終影片同音軌"))
  precondition(SimpleProgressStatus(stage:"配音",detail:"",busy:false,paused:true,error:nil).title==L("已暫停並保存"))
  for theme in StudioThemeChoice.all where theme.id != "ensemble" {precondition(PetArtwork.frames(theme.id).count==12,"Each theme assistant must have all walking poses")}
  func write(_ value:Any,_ url:URL) throws {try FileManager.default.createDirectory(at:url.deletingLastPathComponent(),withIntermediateDirectories:true);try JSONSerialization.data(withJSONObject:value).write(to:url,options:.atomic)}
  let video=qa.appendingPathComponent("preview.mp4"),job=root.appendingPathComponent("jobs/test"),review=job.appendingPathComponent("review.json")
  let cfg:[String:Any]=["video":video.path,"duration":12.0,"selectedEngines":["drama3"],"ttsBackend":"drama3","dubLanguages":["yue"]]
  let cues:[[String:Any]]=[["start":1.0,"end":3.0,"text":"行こう","japanese":"行こう","cantonese":"我哋一齊出發啦。","speakerId":"role"]]
  try write(["config":cfg,"cues":cues,"status":"pending","meta":["streams":[["codec_type":"video","width":960,"height":540]]]],review)
  try write(["video":video.path,"duration":12.0],job.appendingPathComponent("processing-preview.json"))
  let model=AppModel(),editor=model.projectEditor
  model.busy=true;model.progress=0.58;model.stage="配音";model.detail="音軌 1/1 · Drama 3 · 已生成 84/250 段香港廣東話配音。"
  model.currentBatchRequest=try JSONSerialization.data(withJSONObject:cfg)
  model.activePreviewJob=job.path
  editor.refresh(model)
  if let row=editor.projects.first {editor.open(row)}
  let live=LiveVideoPreview();live.refresh(model,video:video.path,preferredJob:job.path)
  precondition(live.requestedLanguages==["yue"] && editor.availableDubLanguages==["yue"])
  // Before review.json exists, the immutable submitted request is authoritative.
  let early=LiveVideoPreview();early.refresh(model,video:video.path,preferredJob:root.appendingPathComponent("not-ready").path)
  precondition(early.requestedLanguages==["yue"])
  func render<V:View>(_ view:V,_ name:String,_ width:CGFloat,_ height:CGFloat) throws {
   let host=NSHostingView(rootView:view.frame(width:width,height:height).environment(\.locale,Locale(identifier:"zh-HK")).environment(\.colorScheme,.light).background(StudioPalette.base).foregroundStyle(ink).tint(accent))
   host.frame=NSRect(x:0,y:0,width:width,height:height)
   let window=NSWindow(contentRect:host.frame,styleMask:[.borderless],backing:.buffered,defer:false);window.contentView=host
   host.layoutSubtreeIfNeeded();RunLoop.main.run(until:Date().addingTimeInterval(0.35));host.layoutSubtreeIfNeeded()
   if let bitmap=host.bitmapImageRepForCachingDisplay(in:host.bounds) {host.cacheDisplay(in:host.bounds,to:bitmap);try bitmap.representation(using:.png,properties:[:])!.write(to:qa.appendingPathComponent(name))}
   window.close()
  }
  try render(VStack(spacing:0) {SimpleStudioHeader(model:model);Divider();SimpleWorkspace(model:model,editor:editor,preview:live)},"simple-running.png",1280,1000)
  try render(VStack(spacing:20) {SimpleLanguageSelector(selection:.constant("yue"));SimpleProcessingProgress(model:model,ready:84)}.padding(24),"progress-and-language.png",960,320)
  try render(HStack {ForEach(0..<6,id:\.self) {frame in ThemeProgressAssistant(frame:8+frame%4,completed:false)}}.padding(20),"assistant-frames.png",760,150)
  UserDefaults.standard.set("professional",forKey:"studioInterfaceMode")
  try render(StudioHeader(model:model,editor:editor,options:model.workspaceOptions),"professional-header.png",1280,80)
  try render(CueVoicePlaybackMatrix(editor:editor).padding(20),"professional-yue-only.png",260,330)
  live.stopInspection();model.busy=false
  print("PASS single-language buttons, bilingual and Wenet choices, frozen request languages, clear stage status, bundled clay animation and consistent mode menu; native UI rendered")
 }
}
