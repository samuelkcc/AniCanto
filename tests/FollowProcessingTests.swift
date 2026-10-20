import AppKit
import AVFoundation
import Foundation

@main struct FollowTests {
 @MainActor static func main() throws {
  NSApplication.shared.setActivationPolicy(.accessory)
  let qa=URL(fileURLWithPath:FileManager.default.currentDirectoryPath).appendingPathComponent(".build/qa284")
  precondition(ProcessInfo.processInfo.environment["SAM_CANTO_DATA"]==qa.appendingPathComponent("qa-data").path)
  try PreviewCommandQueueTests.run()
  let video=ProcessInfo.processInfo.environment["QA_VIDEO"]!
  let model=AppModel();model.busy=true
  model.currentBatchRequest=try JSONSerialization.data(withJSONObject:["video":video,"selectedEngines":["drama3"],"dubLanguages":["yue"]])
  let lock=NSLock();var reads=0
  let live=LiveVideoPreview(snapshotReader:{input in
   precondition(!Thread.isMainThread)
   lock.lock();reads += 1;lock.unlock()
   Thread.sleep(forTimeInterval:0.6) // Cloud disk / metadata wait simulation.
   return WorkspacePreviewSnapshot(path:input.video,job:nil,activeVideo:input.video,length:12,sourceExists:true,matches:true,config:["video":input.video!,"selectedEngines":["drama3"],"dubLanguages":["yue"]],rows:[["start":1.0,"end":3.0,"cantonese":"出發啦！"]])
  })
  live.configurePersistence(root:qa)
  live.follow=false
  let began=Date()
  for _ in 0..<1000 {live.refresh(model,video:video)}
  let submitSeconds=Date().timeIntervalSince(began)
  precondition(submitSeconds<0.25,"Preview refresh waited on file I/O")
  precondition(live.requestedEngines==["drama3"] && live.requestedLanguages==["yue"],"Frozen UI selections must remain immediate")
  live.seek(2.25)
  var beats=0
  let heartbeat=Timer.scheduledTimer(withTimeInterval:0.01,repeats:true) {_ in beats += 1}
  let deadline=Date().addingTimeInterval(3)
  while live.cues.isEmpty && Date()<deadline {RunLoop.main.run(until:Date().addingTimeInterval(0.01))}
  heartbeat.invalidate()
  lock.lock();let calls=reads;lock.unlock()
  precondition(calls==1 && !live.cues.isEmpty && beats>20,"Duplicate file scans or stalled UI")
  precondition(abs(live.seconds-2.25)<0.01,"A late snapshot overwrote the explicit pending seek")
  live.persistSession()
  let restored=LiveVideoPreview();restored.configurePersistence(root:qa)
  precondition(abs(restored.seconds-2.25)<0.01 && !restored.follow,"Preview position must restore before slow metadata finishes")
  live.refresh(model,video:video+"-other");live.resetForRemoval()
  RunLoop.main.run(until:Date().addingTimeInterval(0.8))
  precondition(live.cues.isEmpty && live.takes.isEmpty && live.processingVideo==nil,"An old scan resurrected the removed project")
  print("PASS 1,000 refreshes submitted in \(submitSeconds)s; one slow scan, UI heartbeat \(beats); removal invalidates late results")
  let player=CantoPlayer();player.isMuted=true
  let view=VLCVideoView(frame:NSRect(x:0,y:0,width:640,height:360));view.player=player;view.showsControls=false
  let window=NSWindow(contentRect:view.frame,styleMask:[.titled,.closable],backing:.buffered,defer:false);window.title="AniCanto · Preview stress test";window.contentView=view;window.orderFrontRegardless()
  player.replaceCurrentItem(with:AVPlayerItem(url:URL(fileURLWithPath:video)))
  player.seek(to:CMTime(seconds:5,preferredTimescale:1000))
  let loaded=Date().addingTimeInterval(15)
  while player.duration<10 && Date()<loaded {RunLoop.main.run(until:Date().addingTimeInterval(0.02))}
  precondition(player.duration>10,"VLC source did not load: \(player.failure ?? "unknown")")
  let duration=player.duration
  var last=Date(),maxGap=0.0,latency=0.0,count=0
  let beat=Timer.scheduledTimer(withTimeInterval:0.01,repeats:true) {_ in let now=Date();maxGap=max(maxGap,now.timeIntervalSince(last));last=now}
  let start=Date()
  while Date().timeIntervalSince(start)<4 {
   let t=Date();player.pause();player.seek(to:CMTime(seconds:Double(count%7)*min(3,duration/10),preferredTimescale:1000));_ = player.currentTime();_ = player.duration;_ = player.failure
   latency=max(latency,Date().timeIntervalSince(t));count += 1
   RunLoop.main.run(until:Date().addingTimeInterval(0.01))
  }
  // A source replacement must not strand a canceled in-flight poll.
  for _ in 0..<8 {player.replaceCurrentItem(with:AVPlayerItem(url:URL(fileURLWithPath:video)))}
  let target=min(duration-1,8.0);player.seek(to:CMTime(seconds:target,preferredTimescale:1000))
  RunLoop.main.run(until:Date().addingTimeInterval(4))
  beat.invalidate()
  precondition(latency<0.05 && maxGap<0.5,"Decoder blocked AppKit: latency \(latency), heartbeat \(maxGap)")
  precondition(player.duration>10 && abs(player.currentTime().seconds-target)<0.6,"Latest paused seek did not settle after source changes")
  precondition(player.failure==nil,player.failure ?? "")
  player.play();RunLoop.main.run(until:Date().addingTimeInterval(0.6));player.pause();RunLoop.main.run(until:Date().addingTimeInterval(0.3))
  precondition(player.currentTime().seconds>=target,"Play did not resume")
  player.replaceCurrentItem(with:nil);window.orderOut(nil)
  let result:[String:Any]=["refreshSubmissions":1000,"refreshSeconds":submitSeconds,"metadataScans":calls,"uiHeartbeats":beats,"seekRequests":count,"maxSeekSubmissionSeconds":latency,"maxUIHeartbeatGapSeconds":maxGap,"sourceReplacements":8,"nativePlaybackPassed":true]
  try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:qa.appendingPathComponent("follow-stress-result.json"))
  print("PASS native VLC stress: \(count) rapid seeks, 8 source replacements, play/pause; submission max \(latency)s, heartbeat max \(maxGap)s")
 }
}
