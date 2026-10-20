import SwiftUI
import AppKit
@main struct RepairTargetTests {
 @MainActor static func main() throws {
  let qa=URL(fileURLWithPath:FileManager.default.currentDirectoryPath+"/.build/qa258"),data=qa.appendingPathComponent("native-data")
  precondition(ProcessInfo.processInfo.environment["SAM_CANTO_DATA"]==data.path)
  NSApplication.shared.setActivationPolicy(.prohibited)
  try FileManager.default.createDirectory(at:data,withIntermediateDirectories:true)
  let metadata=Data("{\"id\":\"role\",\"name\":\"role\",\"reference\":\"original.wav\",\"promptText\":\"日本語の原文\",\"language\":\"ja\",\"referenceRanges\":[[1,2],[3,4]],\"transcriptSource\":\"original-japanese-words\",\"originalReference\":\"previous.wav\"}".utf8)
  let profile=try JSONDecoder().decode(VoiceProfile.self,from:metadata)
  let frozen=try JSONDecoder().decode(VoiceProfile.self,from:JSONEncoder().encode(profile))
  precondition(frozen.transcriptSource=="original-japanese-words" && frozen.originalReference=="previous.wav" && frozen.referenceRanges?.count==2,"Editor snapshots must preserve automatic reference provenance")
  let failures=VoiceFailureEvidence.rows(timing:[["index":40,"start":254.61,"end":257.29,"skipped":true,"renderedSeconds":0.0]],issues:[["index":40,"kind":"reference","message":"角色參考未符合要求","status":"skipped"]],engine:"voxcpm2",language:"yue")
  precondition(failures.count==1 && failures[0]["message"] as? String=="角色參考未符合要求")
  precondition(VoiceFailureEvidence.rows(timing:[],issues:[],engine:"voxcpm2",language:"yue").isEmpty,"Pending work is not a failed recording")
  precondition(VoiceFailureEvidence.rows(timing:[["index":2,"renderedSeconds":1.0,"renderedAudio":data.appendingPathComponent("missing.wav").path]],issues:[],engine:"cosyvoice3",language:"en").count==1,"Deleted audio is missing")
  func write(_ row:Any,_ url:URL) throws {try FileManager.default.createDirectory(at:url.deletingLastPathComponent(),withIntermediateDirectories:true);try JSONSerialization.data(withJSONObject:row).write(to:url,options:.atomic)}
  let job=data.appendingPathComponent("jobs/synthetic"),review=job.appendingPathComponent("review.json")
  if FileManager.default.fileExists(atPath:job.path) {try FileManager.default.removeItem(at:job)}
  let cfg:[String:Any]=["video":"episode05.mkv","duration":10.0]
  let cue:[String:Any]=["start":1.0,"end":3.0,"text":"日本語","cantonese":"出發啦。"]
  try write(["config":cfg,"cues":[cue]],review)
  let editor=ProjectEditor();editor.readOnlyPreview=true;editor.configure(root:data)
  let row=ProjectRow(id:"synthetic",video:"episode05.mkv",review:review,status:"已輸出");editor.projects=[row];editor.open(row)
  precondition(editor.repairReview==review)
  for (id,date,video,status) in [("old","2026-10-14T10:00:00Z","episode05.mkv","complete"),("new","2026-10-15T10:00:00Z","episode05.mkv","partial"),("unrelated","2026-10-15T11:00:00Z","other.mkv","complete"),("preview","2026-10-15T12:00:00Z","episode05.mkv","preview")] {
   let folder=job.appendingPathComponent("versions/"+id)
   try write(["id":id,"created":date,"status":status],folder.appendingPathComponent("version.json"))
   try write(["config":["video":video,"duration":10.0],"cues":[cue]],folder.appendingPathComponent("review.json"));try write(["tracks":[]],folder.appendingPathComponent("report.json"))
  }
  editor.loadVersions();precondition(editor.repairReview==job.appendingPathComponent("versions/new/review.json"))
  let incompleteTrack=job.appendingPathComponent("versions/new/tracks/voxcpm2"),segmentID=editor.document!.segments[0].id
  try write(["config":cfg.merging(["ttsBackend":"voxcpm2"]) {_,v in v},"cues":[cue]],incompleteTrack.appendingPathComponent("review.json"))
  try write(["tracks":[["engine":"voxcpm2","language":"yue","folder":incompleteTrack.path,"state":"failed"]]],job.appendingPathComponent("versions/new/track-progress.json"))
  try write(["tracks":[["engine":"voxcpm2","language":"yue","rows":[["index":1,"editorID":segmentID,"start":1.0,"end":3.0,"available":false,"messages":["參考前置檢查失敗，未生成 timing row"],"logs":["timing":incompleteTrack.appendingPathComponent("timing.json").path]]]]]],job.appendingPathComponent("versions/new/dialogue-delivery-audit.json"))
  editor.refreshEvidence()
  precondition(editor.timelineMissingRegions["voxcpm2:yue"]?.first?.reason.contains("未生成 timing row")==true,"Expected dialogue without a timing record must still have a missing marker")
  try write(["id":"new","created":"2026-10-15T10:00:00Z","status":"failed"],job.appendingPathComponent("versions/new/version.json"))
  try FileManager.default.removeItem(at:job.appendingPathComponent("versions/new/report.json"));editor.loadVersions();editor.refreshEvidence()
  precondition(editor.repairReview==job.appendingPathComponent("versions/new/review.json"),"A failed export with a saved delivery audit is still the repair target")
  precondition(editor.timelineMissingRegions["voxcpm2:yue"]?.first?.reason.contains("未生成 timing row")==true,"Failed versions retain their generation evidence")
  if let path=ProcessInfo.processInfo.environment["SAM_CANTO_QA_REAL_PROJECT"] {
   let source=URL(fileURLWithPath:path),sourceReview=source.appendingPathComponent("review.json")
   precondition(FileManager.default.fileExists(atPath:source.appendingPathComponent("editor-base.json").path))
   let bytes=try Data(contentsOf:sourceReview),raw=try JSONSerialization.jsonObject(with:bytes) as! [String:Any],settings=raw["config"] as! [String:Any]
   let actual=ProjectEditor();actual.readOnlyPreview=true;actual.configure(root:data)
   let row=ProjectRow(id:"actual",video:settings["video"] as! String,review:sourceReview,status:"已輸出");actual.projects=[row];actual.open(row)
   precondition(actual.repairReview != sourceReview && actual.repairReview?.deletingLastPathComponent().lastPathComponent=="DFF7FAF2-07A3-4A52-A672-65D3E193155B")
   let gaps=actual.timelineMissingRegions["voxcpm2:yue"] ?? []
   precondition(gaps.contains {abs($0.start-254.61)<0.001 && $0.reason.contains("參考")},"Episode 05 cue 40 must expose its real reference error")
   precondition(!(actual.timelineMissingRegions["gpt-sovits:yue"] ?? []).contains {abs($0.start-254.61)<0.001},"A ready GPT recording is not missing")
   precondition(!actual.selectTimelineVoice("voxcpm2",language:"yue",at:255.0),"Missing marker cannot play a stale cue")
   precondition(actual.previewEngine=="voxcpm2" && actual.previewLanguage=="yue" && actual.auditionLabel.contains("參考"))
   precondition(actual.document?.segments.first {$0.id==actual.selectedSegment}.map {abs($0.start-254.61)<0.001}==true)
   let model=AppModel(),live=LiveVideoPreview()
   let timeline=ProfessionalTimeline(model:model,editor:actual,live:live,allTracks:.constant(true),showCuts:{})
   let height=32+timeline.lanes.reduce(0) {$0+timeline.laneHeight($1)}
   let labels=VStack(spacing:0) {Text("04:15").frame(height:32);ForEach(timeline.lanes) {lane in Text(lane.title).font(.system(size:12)).frame(width:180,height:timeline.laneHeight(lane),alignment:.leading)}}
   let canvas=Canvas {context,size in timeline.draw(context:&context,size:size,fullWidth:1100*actual.duration/45,origin:240/45*1100)}.frame(width:1100,height:height)
   let content=VStack(alignment:.leading,spacing:8) {Text("EP05 · 04:00–04:45").font(.headline);Text(actual.auditionLabel).font(.caption).foregroundStyle(.orange);HStack(alignment:.top,spacing:0) {labels;canvas}}.padding(12).frame(width:1320,height:height+85).background(StudioPalette.base)
   let host=NSHostingView(rootView:content),window=NSWindow(contentRect:NSRect(x:0,y:0,width:1320,height:height+85),styleMask:[.borderless],backing:.buffered,defer:false);window.contentView=host
   RunLoop.main.run(until:Date().addingTimeInterval(0.8));host.layoutSubtreeIfNeeded()
   if let pixels=host.bitmapImageRepForCachingDisplay(in:host.bounds) {host.cacheDisplay(in:host.bounds,to:pixels);try pixels.representation(using:.png,properties:[:])!.write(to:qa.appendingPathComponent("ep05-missing-timeline.png"))}
   let after=try Data(contentsOf:sourceReview);precondition(bytes==after);actual.player.pause()
   print("PASS actual episode 05 repair targets generated version, not initial import; source unchanged")
   print("PASS actual episode 05 missing marker explains cue 40, ready GPT has no false marker, clicking the gap selects the correct engine and dialogue without playing")
  }
  editor.player.pause();print("PASS repair target selection, latest partial version, different-video isolation, previews ignored, original-import fallback")
  print("PASS editor preserves reference provenance and exposes completed delivery failures without timing rows")
 }
}
