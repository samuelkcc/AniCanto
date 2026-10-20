import SwiftUI
import AppKit
import CryptoKit

@main struct SimpleProjectRemovalTests {
 @MainActor static func main() throws {
  let qa=URL(fileURLWithPath:FileManager.default.currentDirectoryPath+"/.build/qa263")
  let root=qa.appendingPathComponent("native-data")
  precondition(ProcessInfo.processInfo.environment["SAM_CANTO_DATA"]==root.path)
  NSApplication.shared.setActivationPolicy(.prohibited)
  UserDefaults.standard.set("zh-HK",forKey:"studioLanguage")
  UserDefaults.standard.set("simple",forKey:"studioInterfaceMode")
  UserDefaults.standard.set(false,forKey:"showStudioCompanion")
  func write(_ object:Any,_ path:URL) throws {try FileManager.default.createDirectory(at:path.deletingLastPathComponent(),withIntermediateDirectories:true);try JSONSerialization.data(withJSONObject:object).write(to:path,options:.atomic)}
  func touch(_ file:URL) throws {try FileManager.default.createDirectory(at:file.deletingLastPathComponent(),withIntermediateDirectories:true);try Data(file.lastPathComponent.utf8).write(to:file)}
  func exists(_ file:URL)->Bool {FileManager.default.fileExists(atPath:file.path)}
  let data=root.appendingPathComponent(UUID().uuidString),a=data.appendingPathComponent("甲-AniCanto.mp4"),b=data.appendingPathComponent("other.mkv")
  try touch(a);try touch(b)
  let jobA=data.appendingPathComponent("jobs/a"),partial=data.appendingPathComponent("jobs/partial"),jobB=data.appendingPathComponent("jobs/b")
  let ownCache=data.appendingPathComponent("separations/own"),sharedCache=data.appendingPathComponent("separations/shared")
  for cache in [ownCache,sharedCache] {try write([a.path,10],cache.appendingPathComponent("complete.json"));try touch(cache.appendingPathComponent("dialogue.wav"))}
  let ref=jobA.appendingPathComponent("role.wav");try touch(ref)
  let internalOutput=jobA.appendingPathComponent("one-AniCanto.mp4"),externalOutput=data.appendingPathComponent("finished-AniCanto.mp4"),custom=jobA.appendingPathComponent("versions/v1/custom-name.mp4")
  for file in [internalOutput,externalOutput,custom] {try touch(file)}
  try write(["config":["video":a.path,"backgroundPath":ownCache.appendingPathComponent("dialogue.wav").path],"cues":[]],jobA.appendingPathComponent("review.json"))
  try write(["video":a.path],partial.appendingPathComponent("processing-preview.json"));try touch(partial.appendingPathComponent("draft.wav"))
  try write(["output":internalOutput.path,"exportedOutput":externalOutput.path],jobA.appendingPathComponent("report.json"))
  try write(["output":custom.path,"status":"complete"],custom.deletingLastPathComponent().appendingPathComponent("version.json"))
  try write(["config":["video":b.path,"dialoguePath":sharedCache.appendingPathComponent("dialogue.wav").path,"voiceProfiles":[["reference":ref.path]]]],jobB.appendingPathComponent("review.json"))
  let ownReference=data.appendingPathComponent("engine-references/drama3/own")
  try write(["source":ref.path],ownReference.appendingPathComponent("reference.json"));try touch(ownReference.appendingPathComponent("reference.wav"))
  try write([["id":"saved-role","reference":ref.path]],data.appendingPathComponent("voice-profiles.json"))
  let model=data.appendingPathComponent("models/model.bin");try touch(model)
  let request=data.appendingPathComponent("request-only.json"),groupRequest=data.appendingPathComponent("request-group.json")
  try write(["video":a.path],request)
  let grouped=try JSONSerialization.data(withJSONObject:["video":a.path,"videos":[["id":"a","video":a.path],["id":"b","video":b.path]],"selectedEngines":["drama3"]])
  try grouped.write(to:groupRequest)
  let kept=SimpleProjectRemovalPlan.prune(grouped,video:a.path,ids:["a"])!
  let cfg=try JSONSerialization.jsonObject(with:kept) as! [String:Any]
  precondition(cfg["video"] as? String==b.path && (cfg["videos"] as? [[String:Any]])?.count==1)
  let db=try ProjectDatabase(root:data);try db.sync(review:jobA.appendingPathComponent("review.json"),output:externalOutput)
  // A symlinked job must never authorize deleting anything outside jobs.
  let outside=data.appendingPathComponent("outside");try write(["config":["video":a.path]],outside.appendingPathComponent("review.json"))
  try FileManager.default.createSymbolicLink(at:data.appendingPathComponent("jobs/link"),withDestinationURL:outside)
  // Match Python's existing opening-cache identity, including a Unicode path.
  let python=Process();python.executableURL=URL(fileURLWithPath:"/usr/bin/python3")
  python.arguments=["-c","import pathlib,json,hashlib,sys; p=pathlib.Path(sys.argv[1]); s=p.stat(); print(hashlib.sha256(json.dumps([str(p.resolve()),s.st_size,s.st_mtime_ns,3]).encode()).hexdigest()[:20])",a.path]
  let pipe=Pipe();python.standardOutput=pipe;try python.run();let key=String(data:pipe.fileHandleForReading.readDataToEndOfFile(),encoding:.utf8)!.trimmingCharacters(in:.whitespacesAndNewlines);python.waitUntilExit();precondition(python.terminationStatus==0)
  let opening=data.appendingPathComponent("openings").appendingPathComponent(key);try write([],opening.appendingPathComponent("result.json"))
  let plan=try SimpleProjectRemovalPlan(root:data,video:a.path,knownOutputs:[externalOutput.path])
  precondition(plan.caches.map(\.path).contains(opening.path),"Legacy OP/ED data belongs to the exact source, including Unicode file names")
  precondition(Set(plan.folders.map(\.lastPathComponent))==["a","partial"])
  precondition(plan.caches.map(\.path).contains(ownCache.path) && !plan.caches.map(\.path).contains(sharedCache.path) && plan.caches.map(\.path).contains(ownReference.path))
  let trash=data.appendingPathComponent("test-trash");try FileManager.default.createDirectory(at:trash,withIntermediateDirectories:true)
  let retained=try plan.execute {file in try FileManager.default.moveItem(at:file,to:trash.appendingPathComponent(UUID().uuidString+"-"+file.lastPathComponent))}
  precondition(!exists(jobA) && !exists(partial) && exists(jobB) && exists(outside))
  let otherReview=SimpleProjectRemovalPlan.json(jobB.appendingPathComponent("review.json")) as! [String:Any]
  let otherCfg=otherReview["config"] as! [String:Any]
  let sharedRole=(otherCfg["voiceProfiles"] as! [[String:Any]])[0]["reference"] as! String
  precondition(sharedRole != ref.path && exists(URL(fileURLWithPath:sharedRole)),"Other episodes must not lose a role borrowed from the removed project")
  precondition(exists(a) && exists(b) && exists(model) && exists(externalOutput))
  precondition(!exists(ownCache) && !exists(ownReference) && exists(sharedCache) && !exists(request))
  precondition(retained.count==3 && retained.allSatisfy(exists))
  precondition(retained.contains {$0.lastPathComponent=="custom-name.mp4"} && retained.contains {$0.lastPathComponent=="one-AniCanto.mp4"})
  let profiles=try JSONSerialization.jsonObject(with:Data(contentsOf:data.appendingPathComponent("voice-profiles.json"))) as! [[String:Any]]
  precondition(exists(URL(fileURLWithPath:profiles[0]["reference"] as! String)))
  let indexed=try db.rows("SELECT path FROM outputs").compactMap(\.first)
  precondition(retained.allSatisfy {indexed.contains($0.path)})
  let updated=try JSONSerialization.jsonObject(with:Data(contentsOf:groupRequest)) as! [String:Any]
  precondition(updated["video"] as? String==b.path && (updated["videos"] as? [[String:Any]])?.count==1)
  let second=try SimpleProjectRemovalPlan(root:data,video:a.path)
  precondition(second.folders.isEmpty && !second.caches.map(\.path).contains(sharedCache.path),"Retry must not widen cleanup")
  // Failed cleanup must leave source and original finished outputs intact.
  let failureData=root.appendingPathComponent(UUID().uuidString),failureSource=failureData.appendingPathComponent("source.mkv"),failureJob=failureData.appendingPathComponent("jobs/job"),failureOutput=failureJob.appendingPathComponent("failed-AniCanto.mp4")
  try touch(failureSource);try touch(failureOutput);try write(["config":["video":failureSource.path]],failureJob.appendingPathComponent("review.json"))
  let failing=try SimpleProjectRemovalPlan(root:failureData,video:failureSource.path)
  do {_=try failing.execute {_ in throw AppFailure(message:"Injected trash failure")};preconditionFailure("Failure must surface")} catch {}
  precondition(exists(failureSource) && exists(failureOutput) && exists(failureJob))
  let protectedSource=failureJob.appendingPathComponent("other-original.mkv");try touch(protectedSource)
  try write(["config":["video":protectedSource.path]],failureData.appendingPathComponent("jobs/other/review.json"))
  do {_=try SimpleProjectRemovalPlan(root:failureData,video:failureSource.path);preconditionFailure("A different source inside the selected job must be protected")} catch {}
  try runCleanupChecks(root:qa)
  // Real AppKit render with long names, eight queue entries, and a one-item list.
  let modelView=AppModel(),editor=modelView.projectEditor,live=LiveVideoPreview(),video=qa.appendingPathComponent("preview.mp4")
  modelView.selectSimpleEngine("drama3")
  modelView.batchItems=(0..<8).map {i in BatchItem(video:i==0 ? video.path:qa.appendingPathComponent("Example Anime Series 2026 S01E0\(i)-[1080p][BDRIP][x265.OPUS]-very-long-filename.mkv").path,status:i==1 ? "完成":"待處理")}
  editor.refresh(modelView);if let first=editor.projects.first {editor.open(first)};live.refresh(modelView,video:video.path)
  func render<V:View>(_ view:V,_ name:String,_ width:CGFloat,_ height:CGFloat) throws {
   let host=NSHostingView(rootView:view.frame(width:width,height:height).environment(\.locale,Locale(identifier:"zh-HK")).environment(\.colorScheme,.light).background(StudioPalette.base).foregroundStyle(ink).tint(accent));host.frame=NSRect(x:0,y:0,width:width,height:height)
   let window=NSWindow(contentRect:host.frame,styleMask:[.borderless],backing:.buffered,defer:false);window.contentView=host
   host.layoutSubtreeIfNeeded();RunLoop.main.run(until:Date().addingTimeInterval(0.3));host.layoutSubtreeIfNeeded()
   let bitmap=host.bitmapImageRepForCachingDisplay(in:host.bounds)!;host.cacheDisplay(in:host.bounds,to:bitmap)
   try bitmap.representation(using:.png,properties:[:])!.write(to:qa.appendingPathComponent(name));window.close()
  }
  try render(SimpleWorkspace(model:modelView,editor:editor,preview:live).batchList,"five-visible-rows.png",1000,390)
  try render(VStack(spacing:0) {SimpleStudioHeader(model:modelView);SimpleWorkspace(model:modelView,editor:editor,preview:live)},"simple-list.png",1280,1000)
  modelView.batchItems=Array(modelView.batchItems.prefix(1))
  try render(SimpleWorkspace(model:modelView,editor:editor,preview:live).batchList,"single-item-removal.png",1000,180)
  live.resetForRemoval();precondition(live.player.currentItem==nil && live.takes.isEmpty && live.cues.isEmpty)
  live.refresh(modelView,video:video.path);precondition(live.player.currentItem != nil,"Preview must reopen after cleanup reset")
  print("PASS per-source complete and partial project cleanup, verified internal/custom/external output preservation, source/model/other-project/shared-cache protection, queue pruning, saved voices, symlink safety, retry scope, existing cleanup checks, five-row and sole-item remove UI")
 }
}
