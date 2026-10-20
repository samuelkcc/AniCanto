import Foundation
import AVFoundation
struct RecordingHistoryTests {
 @MainActor static func run(_ root:URL) throws {
  let fm=FileManager.default,base=root.appendingPathComponent("history-fixture-"+UUID().uuidString)
  try fm.createDirectory(at:base,withIntermediateDirectories:true)
  defer {try? fm.removeItem(at:base)}
  func write(_ name:String,_ object:Any) throws {try JSONSerialization.data(withJSONObject:object).write(to:base.appendingPathComponent(name))}
  let original=base.appendingPathComponent("old.rejected.raw.wav")
  try fm.copyItem(at:root.appendingPathComponent("sample.wav"),to:original)
  let source=try Data(contentsOf:original)
  try write("review.json",["config":["ttsBackend":"drama3","targetLanguage":"yue"],"cues":[["start":1.0,"end":2.0,"cantonese":"唔該。","editorID":"cue-a","reviewIndex":101]]])
  try write("drama3-request.json",["items":[["output":base.appendingPathComponent("old.wav").path,"reviewIndex":101,"text":"唔該。"]]])
  try write("old.failure.json",["error":"generation-limit"])
  precondition(ProcessingAudioIndex.length(original.path)==nil,"Normal playback must continue to exclude rejected files")
  let records=RecordingHistoryReader.load(root:base,engine:"drama3",language:"yue",index:102,segmentID:"cue-a")
  precondition(records.count==1 && records[0].length != nil && records[0].start==1,"Legacy raw discovered by original reviewIndex")
  precondition(RecordingHistoryReader.load(root:base,engine:"drama3",language:"en",index:102,segmentID:"cue-a").isEmpty)
  let editor=ProjectEditor()
  let segment=EditSegment(id:"cue-a",sources:[101],start:1,end:2,captionStart:1,captionEnd:2,text:"唔該。",original:"ありがとう",speakerId:"actor")
  editor.document=EditDocument(review:base.appendingPathComponent("review.json").path,segments:[segment],clips:[])
  editor.adoptHistoricalRecording(records[0]);editor.audio.pause()
  guard let copied=editor.document?.segments[0].audioTake else{preconditionFailure("Acceptance not saved")}
  precondition(copied != original.path && (try! Data(contentsOf:URL(fileURLWithPath:copied)))==source)
  precondition(editor.document?.segments[0].audioAcceptedHistoryID==records[0].id)
  // A later generation can overwrite the legacy file but never the accepted copy.
  try Data("new generation".utf8).write(to:original)
  let acceptedBytes=try Data(contentsOf:URL(fileURLWithPath:copied));precondition(acceptedBytes==source)
  let accepted=editor.document
  var fragment=records[0];fragment.text="唔該，等陣先。";fragment.spokenText="唔該，"
  precondition(fragment.isFragment,"A phrase sample must not be labeled a full-line take")
  editor.adoptHistoricalRecording(fragment);precondition(editor.document==accepted)
  var stale=records[0];stale.text="另一句"
  editor.adoptHistoricalRecording(stale);precondition(editor.document==accepted)
  let decoded=try JSONDecoder().decode(EditDocument.self,from:JSONEncoder().encode(accepted!))
  precondition(decoded.segments[0].audioAcceptedHistoryID==records[0].id)
  print("PASS legacy rejected recording, cue identity, language isolation, immutable user acceptance and stale-script protection")
 }
 static func episode(_ root:URL) {
  for index in [102,116,117,160,167,270] {
   let rows=RecordingHistoryReader.load(root:root,engine:"drama3",language:"yue",index:index,segmentID:nil)
   precondition(!rows.isEmpty && rows.contains {$0.length != nil},"Missing EP07 diagnostic recording \(index)")
   print("PASS EP07 read-only history \(index): \(rows.count) takes; latest \(rows[0].length ?? -1)s")
  }
 }
}
