import Foundation

enum BasicPreviewCaptionsTests {
    @MainActor static func run() throws {
        let cues=(0..<300).map {i in LiveSubtitleCue(id:i,start:Double(i)*4,end:Double(i)*4+3,original:"原聲",cantonese:"台詞",english:"Script")}
        var takes=cues.map {cue in ProcessingVoiceTake(engine:"drama3",language:"yue",path:"",text:"錄音 \(cue.id)",speakerID:"R1",start:cue.start,end:cue.end,length:3)}
        takes.insert(ProcessingVoiceTake(engine:"cosyvoice3",language:"yue",path:"",text:"另一引擎",speakerID:"R1",start:0,end:3,length:3),at:0)
        takes[1]=ProcessingVoiceTake(engine:"drama3",language:"yue",path:"",text:"邊界",speakerID:"R1",start:0.0006,end:3.0006,length:3)
        let rows=BasicPreviewCaptions.rows(cues:cues,takes:takes,engine:"drama3",languages:["yue","en"],offset:12)
        precondition(rows.count==600 && rows[0].text=="邊界" && rows[0].start==12)
        precondition(rows[1].text=="錄音 1" && rows[300].text=="Script","Engine, language, timing and missing-take fallback must match the monitor")
        let request=try JSONSerialization.data(withJSONObject:["video":"fixture","selectedEngines":["drama3"],"cues":Array(repeating:["text":"台詞","start":1.0],count:300)])
        let changed=try JSONSerialization.data(withJSONObject:["video":"fixture","selectedEngines":["gpt-sovits"]])
        precondition(WorkspaceRequestCache.decode(request)?["selectedEngines"] as? [String]==["drama3"])
        precondition(WorkspaceRequestCache.decode(changed)?["selectedEngines"] as? [String]==["gpt-sovits"])
        let start=Date()
        for _ in 0..<100 {
            precondition(WorkspaceRequestCache.decode(request)?["selectedEngines"] as? [String]==["drama3"])
            precondition(BasicPreviewCaptions.rows(cues:cues,takes:takes,engine:"drama3",languages:["yue","en"],offset:12).count==600)
        }
        let elapsed=Date().timeIntervalSince(start)
        precondition(elapsed<1,"Basic preview caption rebuilding is too expensive: \(elapsed)s")
        print("PASS Basic preview: 300 cues, two languages, 301 takes, 100 clock refreshes in \(elapsed)s; engine isolation, sub-millisecond tolerance and immutable request changes")
    }
}
