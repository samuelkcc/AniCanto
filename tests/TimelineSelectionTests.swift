import SwiftUI
import AppKit
import AVFoundation

/// Build with Sources/*.swift -D PREVIEW_QA; SAM_CANTO_DATA must point to
/// .build/qa257/data. All writable fixtures stay under that isolated directory.
@main struct TimelineSelectionTests {
 @MainActor static func main() throws {
  let project=URL(fileURLWithPath:FileManager.default.currentDirectoryPath),qa=project.appendingPathComponent(".build/qa257"),data=qa.appendingPathComponent("data")
  precondition(ProcessInfo.processInfo.environment["SAM_CANTO_DATA"]==data.path,"Isolated SAM_CANTO_DATA is required before creating AppModel")
  if FileManager.default.fileExists(atPath:data.path) {try FileManager.default.removeItem(at:data)}
  NSApplication.shared.setActivationPolicy(.prohibited)
  UserDefaults.standard.set("zh-HK",forKey:"studioLanguage");UserDefaults.standard.set(false,forKey:"showStudioCompanion")
  try FileManager.default.createDirectory(at:data,withIntermediateDirectories:true)
  func write(_ obj:Any,_ url:URL) throws {try FileManager.default.createDirectory(at:url.deletingLastPathComponent(),withIntermediateDirectories:true);try JSONSerialization.data(withJSONObject:obj,options:.sortedKeys).write(to:url,options:.atomic)}
  let job=data.appendingPathComponent("jobs/fixture"),review=job.appendingPathComponent("review.json"),wav=job.appendingPathComponent("ready.wav"),pending=job.appendingPathComponent("late.wav")
  try FileManager.default.createDirectory(at:job,withIntermediateDirectories:true)
  let format=AVAudioFormat(standardFormatWithSampleRate:24000,channels:1)!,buffer=AVAudioPCMBuffer(pcmFormat:format,frameCapacity:24000)!
  buffer.frameLength=24000
  for i in 0..<24000 {buffer.floatChannelData![0][i]=Float(sin(Double(i)*0.1)*0.01)}
  do {let file=try AVAudioFile(forWriting:wav,settings:format.settings);try file.write(from:buffer)}
  let video=job.appendingPathComponent("missing.mp4").path
  let cfg:[String:Any]=["video":video,"duration":12.0,"selectedEngines":["gpt-sovits-v2"],"dubLanguages":["yue"],"gsvVersion":"v2ProPlus"]
  let segments=[EditSegment(id:"cue1",sources:[0],start:1,end:4,captionStart:1,captionEnd:4,text:"出發啦。",original:"行こう",speakerId:"old-role",english:"Let's go."),EditSegment(id:"cue2",sources:[1],start:6,end:9,captionStart:6,captionEnd:9,text:"準備好未？",original:"準備は？",speakerId:"old-role",english:"Ready?")]
  let cues=segments.map {s in ["editorID":s.id,"start":s.start,"end":s.end,"cantonese":s.text,"english":s.english!,"speakerId":"new-role","_seed":42] as [String:Any]}
  try write(["config":cfg,"cues":cues],review)
  let doc=EditDocument(review:review.path,segments:segments,clips:[EditClip(start:0,end:12)],pendingChanges:false,dubLanguages:["yue"])
  try JSONEncoder().encode(doc).write(to:job.appendingPathComponent("editor-draft.json"))
  let old=job.appendingPathComponent("versions/old"),new=job.appendingPathComponent("versions/new")
  try write(["status":"complete","created":"2026-10-14T10:00:00Z"],old.appendingPathComponent("version.json"))
  try write(["status":"running","created":"2026-10-15T10:00:00Z"],new.appendingPathComponent("version.json"))
  func track(_ parent:URL,_ engine:String,_ language:String,_ rows:[[String:Any]]) throws -> URL {
   let folder=parent.appendingPathComponent("tracks/"+engine+"-"+language)
   let translated=cues.map {cue in cue.merging(["cantonese":language=="en" ? cue["english"]!:cue["cantonese"]!]) {_,value in value}}
   try write(["config":cfg.merging(["ttsBackend":engine,"targetLanguage":language]) {_,v in v},"cues":translated],folder.appendingPathComponent("review.json"))
   try write(["engine":engine,"language":language,"rows":rows],folder.appendingPathComponent("audio-preview.json"));return folder
  }
  _ = try track(old,"cosyvoice3","en",[cues[0].merging(["cantonese":"Let's go.","audio":wav.path]) {_,v in v}])
  let newestEnglish=try track(new,"cosyvoice3","en",[]) // Newest folder must not hide an older ready take.
  let active=try track(new,"gpt-sovits-v2","yue",[cues[0].merging(["audio":wav.path]) {_,v in v},cues[1].merging(["audio":pending.path]) {_,v in v}])
  try write(["tracks":[["engine":"cosyvoice3","language":"en","folder":newestEnglish.path,"state":"preparing"],["engine":"gpt-sovits-v2","language":"yue","folder":active.path,"state":"running"]]],new.appendingPathComponent("track-progress.json"))
  let skipped=job.appendingPathComponent("skipped-cosyvoice3.wav");try FileManager.default.copyItem(at:wav,to:skipped)
  let broken=try track(job,"cosyvoice3","yue",[])
  try write([["start":1.0,"end":4.0,"skipped":true,"audio":skipped.path]],broken.appendingPathComponent("timing.json"))
  let editor=ProjectEditor();editor.readOnlyPreview=true;editor.configure(root:data)
  let row=ProjectRow(id:"fixture",video:video,review:review,status:"生成中");editor.projects=[row];editor.open(row)
  precondition(editor.error==nil,editor.error ?? "")
  precondition(editor.timelineAudioRegions["cosyvoice3:en"]?.count==1,"Older ready English take must be visible")
  precondition(editor.timelineAudioRegions["gpt-sovits-v2:yue"]?.count==1)
  precondition(editor.timelineAudioRegions["cosyvoice3:yue"]?.isEmpty==true,"Skipped silence must not draw a completed block")
  precondition(editor.availableDubLanguages.contains("en") && editor.availableVoiceEngines.contains("cosyvoice3"))
  let nav=editor.manualNavigation,before=editor.document!
  editor.audio.isMuted=true
  precondition(editor.selectTimelineVoice("cosyvoice3",language:"en",at:2))
  precondition(editor.previewEngine=="cosyvoice3" && editor.previewLanguage=="en" && editor.selectedSegment=="cue1")
  precondition(editor.manualNavigation==nav && !editor.followPlaybackText,"Selecting audio must not force-scroll")
  precondition((editor.audio.currentItem?.asset as? AVURLAsset)?.url==wav)
  editor.audio.pause()
  precondition(!editor.selectTimelineVoice("cosyvoice3",language:"en",at:5),"Clicking a gap must not play the previous dialogue")
  precondition(editor.audio.rate==0 && editor.seconds==5)
  precondition(!editor.selectTimelineVoice("gpt-sovits-v2",language:"yue",at:7),"An unpublished WAV stays empty")
  try FileManager.default.copyItem(at:wav,to:pending);editor.refreshEvidence()
  precondition(editor.timelineAudioRegions["gpt-sovits-v2:yue"]?.count==2,"A late final WAV adds a block without track completion")
  precondition(editor.selectTimelineVoice("gpt-sovits-v2",language:"yue",at:7))
  precondition(editor.selectedSegment=="cue2" && editor.previewLanguage=="yue")
  editor.audio.pause()
  editor.playCueVoice("cosyvoice3",language:"en");precondition(editor.previewEngine=="cosyvoice3" && editor.previewLanguage=="en");editor.audio.pause()
  precondition(editor.document==before,"Track selection must not alter draft roles or settings")
  // Drawing and input share row heights, ruler offset, half-open boundaries,
  // tile origins and a small tolerance for real mouse/trackpad movement.
  let heights=[24.0,24,24,56,24,30,30]
  precondition(TimelineHitTest.lane(at:31.99,heights:heights)==nil)
  precondition(TimelineHitTest.lane(at:184,heights:heights)==5)
  precondition(TimelineHitTest.lane(at:213.99,heights:heights)==5)
  precondition(TimelineHitTest.lane(at:214,heights:heights)==6)
  precondition(TimelineHitTest.lane(at:244,heights:heights)==nil)
  precondition(TimelineHitTest.isClick(CGPoint(x:100,y:190),CGPoint(x:104,y:193)))
  precondition(!TimelineHitTest.isClick(CGPoint(x:100,y:190),CGPoint(x:109,y:190)))
  precondition(TimelineHitTest.time(at:20,origin:1200,width:2400,duration:120)==61)
  precondition(TimelineHitTest.time(at:0,origin:0,width:2400,duration:120)==0)
  precondition(TimelineHitTest.time(at:1200,origin:1200,width:2400,duration:120)==120)
  // Render a real native timeline with a selected English track.
  let model=AppModel();precondition(model.engine.root.path==data.path);model.busy=true;model.queuePaused=true;model.editorTasks=[];model.batchItems=[]
  let live=LiveVideoPreview()
  let timeline=ProfessionalTimeline(model:model,editor:editor,live:live,allTracks:.constant(true),showCuts:{})
  precondition(timeline.lanes.contains {$0.id=="cosyvoice3:en"})
  let english=timeline.lanes.first {$0.id=="cosyvoice3:en"}!
  precondition(timeline.selectedTrack(english) && timeline.regions(english).count==1)
  let host=NSHostingView(rootView:timeline.frame(width:1100,height:520))
  let window=NSWindow(contentRect:NSRect(x:0,y:0,width:1100,height:520),styleMask:[.borderless],backing:.buffered,defer:false);window.contentView=host
  RunLoop.main.run(until:Date().addingTimeInterval(0.8));host.layoutSubtreeIfNeeded()
  let pixels=host.bitmapImageRepForCachingDisplay(in:host.bounds)!;host.cacheDisplay(in:host.bounds,to:pixels)
  try pixels.representation(using:.png,properties:[:])!.write(to:qa.appendingPathComponent("timeline-selection.png"))
  // Optional read-only replay against a user-specified project. The data root
  // remains isolated, and opening a project is forbidden if it needs a base file.
  if let actual=ProcessInfo.processInfo.environment["SAM_CANTO_QA_REAL_PROJECT"] {
   let root=URL(fileURLWithPath:actual),realReview=root.appendingPathComponent("review.json")
   precondition(FileManager.default.fileExists(atPath:root.appendingPathComponent("editor-base.json").path))
   let paths=["review.json","editor-base.json","editor-draft.json","editor-voices.json"].map {root.appendingPathComponent($0)}
   let protected=try paths.map {try Data(contentsOf:$0)}
   let realEditor=ProjectEditor();realEditor.readOnlyPreview=true;realEditor.configure(root:data);realEditor.audio.isMuted=true
   let raw=ProcessingAudioIndex.read(realReview),realConfig=raw["config"] as! [String:Any]
   let realRow=ProjectRow(id:"real-read-only",video:realConfig["video"] as! String,review:realReview,status:"已暫停")
   realEditor.projects=[realRow];realEditor.open(realRow);precondition(realEditor.document != nil,realEditor.error ?? "")
   realEditor.selectedSegment=ProcessInfo.processInfo.environment["SAM_CANTO_QA_REAL_CUE"] ?? realEditor.document!.segments[0].id
   let original=realEditor.document!,selected=realEditor.selectedSegment!
   let ready=realEditor.versionPreviewTakes.filter {take in original.segments.contains {$0.id==selected && realEditor.matchesVersionPreview(take,segment:$0)}}
   precondition(!ready.isEmpty)
   for take in ready {
    let key=take.engine+":"+take.language
    precondition((realEditor.timelineAudioRegions[key] ?? []).contains {$0.segmentID==selected},"Playable real take missing on timeline: "+key)
    precondition(realEditor.selectTimelineVoice(take.engine,language:take.language,at:take.start+0.01),"Real track cannot be selected: "+key)
    precondition(realEditor.previewEngine==take.engine && realEditor.previewLanguage==take.language)
    realEditor.audio.pause()
   }
   if let english=ready.first(where:{$0.language=="en"}) {realEditor.selectVoiceTrack(english.engine,language:"en")}
   let realTimeline=ProfessionalTimeline(model:model,editor:realEditor,live:live,allTracks:.constant(true),showCuts:{})
   let realHost=NSHostingView(rootView:realTimeline.frame(width:1300,height:680))
   let realWindow=NSWindow(contentRect:NSRect(x:0,y:0,width:1300,height:680),styleMask:[.borderless],backing:.buffered,defer:false);realWindow.contentView=realHost
   RunLoop.main.run(until:Date().addingTimeInterval(0.8));realHost.layoutSubtreeIfNeeded()
   let image=realHost.bitmapImageRepForCachingDisplay(in:realHost.bounds)!;realHost.cacheDisplay(in:realHost.bounds,to:image)
   try image.representation(using:.png,properties:[:])!.write(to:qa.appendingPathComponent("real-timeline.png"))
   let after=try paths.map {try Data(contentsOf:$0)};precondition(after==protected && realEditor.document==original)
   realEditor.player.pause();realEditor.audio.pause()
   print("PASS real timeline: \(ready.count) ready language/engine combinations visible and selectable; metadata unchanged")
  }
  editor.player.pause();editor.audio.pause();live.stopInspection();model.busy=false
  print("PASS timeline regression: older bilingual ready takes, skipped/missing WAVs, late publication, engine/language selection, gaps do not replay, no forced scrolling, immutable draft, tiled half-open hit testing, click tolerance, native selected-row render")
 }
}
