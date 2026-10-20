import SwiftUI
import AppKit

@main struct WorkspaceSynchronizationTests {
 @MainActor static func main() throws {
  runManagedToolIfNeeded()
  let qa=URL(fileURLWithPath:FileManager.default.currentDirectoryPath+"/.build/qa262")
  let root=qa.appendingPathComponent("native-data")
  precondition(ProcessInfo.processInfo.environment["SAM_CANTO_DATA"]==root.path)
  NSApplication.shared.setActivationPolicy(.prohibited)
  UserDefaults.standard.set("zh-HK",forKey:"studioLanguage")
  UserDefaults.standard.set("simple",forKey:"studioInterfaceMode")
  UserDefaults.standard.set("drama3",forKey:"simpleVoiceEngine")
  UserDefaults.standard.set("yue",forKey:"simpleDubLanguage")
  UserDefaults.standard.set("yue,original",forKey:"simpleSubtitleModes")
  UserDefaults.standard.set(false,forKey:"showStudioCompanion")
  UserDefaults.standard.set(false,forKey:"sharedWorkspaceVoiceSelection")
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
  precondition(model.ttsBackend=="drama3" && model.dubMode=="yue","Migrate old simple preferences once")
  model.ttsBackend="gpt-sovits";model.extraEngines=["cosyvoice3"];model.dubMode="both"
  let frozen=model.currentBatchRequest!
  precondition(model.submittedVoiceSelection(video:video.path)?.engines==["drama3"])
  precondition(model.submittedVoiceSelection(video:"unrelated.mp4")==nil)
  let live=LiveVideoPreview();live.refresh(model,video:video.path,preferredJob:job.path)
  precondition(live.requestedLanguages==["yue"] && editor.availableDubLanguages==["yue"])
  // Before review.json exists, the immutable submitted request is authoritative.
  let early=LiveVideoPreview();early.refresh(model,video:video.path,preferredJob:root.appendingPathComponent("not-ready").path)
  precondition(early.requestedLanguages==["yue"] && early.requestedEngines==["drama3"])
  var all=true
  let timeline=ProfessionalTimeline(model:model,editor:editor,live:live,allTracks:Binding(get:{all},set:{all=$0}),showCuts:{})
  precondition(timeline.lanes.filter {$0.kind=="audio"}.map(\.id)==["drama3:yue"],"Pro timeline must follow the frozen request, not GPT defaults")
  precondition(ConversionInspectorSnapshot(model).submitted?.primary=="drama3")
  let simple=SimpleWorkspace(model:model,editor:editor,preview:live)
  precondition(simple.selectedEngine=="drama3" && simple.displayedLanguage=="yue")
  precondition(simple.plan.engine=="drama3" && simple.plan.languageMode=="yue","A frozen selection must also be used when adding more waiting videos")
  precondition(model.currentBatchRequest==frozen,"Mode display must not rewrite a running request")
  model.busy=false;model.currentBatchRequest=nil
  model.selectSimpleEngine("cosyvoice3")
  precondition(model.selectedEngines==["cosyvoice3"])
  precondition(SimpleWorkspace(model:model,editor:editor).selectedEngine=="cosyvoice3")
  model.ttsBackend="drama3"
  precondition(SimpleWorkspace(model:model,editor:editor).selectedEngine=="drama3","Pro changes must appear in Simple too")
  model.migrateSimpleVoiceSelection()
  model.extraEngines=["cosyvoice3"];model.includeOriginal=false
  let reloaded=AppModel()
  precondition(reloaded.ttsBackend=="drama3" && reloaded.extraEngines==["cosyvoice3"] && !reloaded.includeOriginal,"Shared choices survive a restart")
  model.includeOriginal=true
  precondition(model.ttsBackend=="drama3","Migration must not replay old defaults")
  model.pendingBatchRequests=[frozen]
  precondition(model.submittedVoiceSelection(video:video.path)?.primary=="drama3","Paused queues retain their engine")
  model.pendingBatchRequests=[]
  let taskFile=root.appendingPathComponent("editor-submission.json")
  try write(["settings":["selectedEngines":["cosyvoice3"],"defaultAudioEngine":"cosyvoice3","dubLanguages":["en"]]],taskFile)
  model.editorTasks=[EditorialTask(id:"editor-task",review:review.path,submission:taskFile.path)]
  precondition(model.submittedVoiceSelection(video:video.path)?.engines==["cosyvoice3"] && model.submittedVoiceSelection(video:video.path)?.languages==["en"])
  model.editorTasks=[]
  var batchPlan=SimpleProductionPlan(engine:"drama3",languageMode:"both",subtitles:["yue","english","original"],originalStreams:[2])
  let items=[BatchItem(video:"episode-a.mkv"),BatchItem(video:"episode-b.mkv")]
  let requests=try SimpleBatchRequests.make(plan:batchPlan,items:items,base:["video":"stale.mkv","selectedEngines":["gpt-sovits"],"limit":60],selectedVideo:"episode-a.mkv",originalStreams:["episode-b.mkv":[5,6]])
  let decoded=try requests.map {try JSONSerialization.jsonObject(with:$0) as! [String:Any]}
  precondition(decoded.count==2 && decoded[0]["video"] as? String=="episode-a.mkv" && decoded[1]["video"] as? String=="episode-b.mkv")
  precondition(decoded.allSatisfy {$0["selectedEngines"] as? [String]==["drama3"] && $0["dubLanguages"] as? [String]==["yue","en"] && $0["burnOutputCaptions"] as? Bool==false})
  precondition(decoded[0]["originalSubtitleStreams"] as? [Int]==[2] && decoded[1]["originalSubtitleStreams"] as? [Int]==[5,6],"Each video has its own subtitle indices")
  batchPlan.engine="wsyue"
  do {_=try SimpleBatchRequests.make(plan:batchPlan,items:items,base:[:],selectedVideo:nil,originalStreams:[:]);preconditionFailure("Unsupported language must fail before enqueuing")} catch {}
  model.batchItems=items+[BatchItem(video:"done.mkv",status:"完成",output:"done.mp4"),BatchItem(video:"review.mkv",review:"review.json")]
  model.pendingBatchRequests=requests
  precondition(model.submittedVoiceSelection(video:"episode-b.mkv")?.engines==["drama3"] && model.submittedVoiceSelection(video:"unrelated.mkv")==nil)
  model.pendingBatchRequests=[]
  precondition(model.simpleBatchPending.count==2,"Never automatically redo completed or existing reviewed projects")
  model.busy=true;model.currentBatchRequest=frozen;model.dubMode="both";model.ttsBackend="gpt-sovits"

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
  try render(ProfessionalConversionControls(model:model,snapshot:ConversionInspectorSnapshot(model)).padding(20),"pro-frozen-settings.png",420,1100)
  try render(ProfessionalTimeline(model:model,editor:editor,live:live,allTracks:.constant(true),showCuts:{}),"pro-frozen-timeline.png",1280,310)
  UserDefaults.standard.set("en",forKey:"studioLanguage")
  precondition(L("介面語言")=="Interface language")
  try render(SimpleStudioHeader(model:model),"simple-english-header.png",1280,60)
  UserDefaults.standard.set("zh-HK",forKey:"studioLanguage")
  model.showAbout=true;precondition(model.showAbout)
  try render(AboutAniCanto().padding(20),"about.png",800,900)
  try render(CueVoicePlaybackMatrix(editor:editor).padding(20),"professional-yue-only.png",260,330)
  live.stopInspection();model.busy=false
  print("PASS shared engine and language defaults, frozen active and paused requests, video isolation, Drama timeline and inspector, simple batch snapshots and per-video subtitles, language picker and About; native UI rendered")
 }
}
