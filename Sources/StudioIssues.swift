import SwiftUI

struct StudioIssue:Identifiable {
    var id:String,engine:String,language:String,index:Int,start:Double,title:String,detail:String
    var repaired:Bool=false
}
extension ProjectEditor {
    var studioIssues:[StudioIssue] {
        if let cached=studioIssueCache {return cached}
        var rows:[String:StudioIssue]=[:]
        func add(_ engine:String,_ language:String,_ index:Int,_ title:String,_ detail:String,_ time:Double?=nil) {
            guard index>0 else{return}
            let key=engine+":"+language+":"+String(index)
            let segment=document?.segments.first {$0.sources.contains(index-1)}
            if rows[key]==nil {rows[key]=StudioIssue(id:key,engine:engine,language:language,index:index,start:time ?? segment?.start ?? 0,title:title,detail:detail)}
            else if !detail.isEmpty {rows[key]!.detail += " · "+detail}
        }
        for issue in segmentIssues+channelGenerationIssues {add(issue["engine"] as? String ?? "cosyvoice3",issue["language"] as? String ?? "yue",issue["index"] as? Int ?? 0,"生成失敗",issue["message"] as? String ?? "",issue["start"] as? Double)}
        for quality in trackQuality {
            let engine=quality["engine"] as? String ?? "cosyvoice3",language=quality["language"] as? String ?? "yue"
            for (key,title) in [("languageReviewIndices","語言待覆核"),("contentReviewIndices","內容待覆核"),("timingReviewIndices","時間待覆核"),("voiceReviewIndices","聲線待覆核"),("levelReviewIndices","音量待覆核"),("originalSpeechIndices","多人原聲保留")] {
                for index in quality[key] as? [Int] ?? [] {
                    add(engine,language,index,title,L(title))
                    if key=="originalSpeechIndices" {rows[engine+":"+language+":"+String(index)]?.title=title}
                }
            }
        }
        for key in fallbackEvidence.keys {
            let parts=key.split(separator:":");guard parts.count==2 else{continue}
            for fallback in fallbackEvidence[key] ?? [] {
                let engine=String(parts[0]),language=String(parts[1]),index=fallback["index"] as? Int ?? 0
                let title=fallback["sourceLanguage"] as? String=="ja" ? "已用日文補聲":"已用其他引擎補聲"
                add(engine,language,index,title,"",fallback["start"] as? Double)
                let id=key+":"+String(index)
                if var row=rows[id] {row.title=title;row.repaired=true;row.detail=L("補聲來源")+": "+(fallback["sourceEngine"] as? String ?? "")+" · "+L("原生成問題保留供追溯");rows[id]=row}
            }
        }
        for (key,var issue) in rows {
            if let segment=document?.segments.first(where:{$0.sources.contains(issue.index-1)}),segment.audioAcceptedHistoryID != nil,let path=segment.audioTake {
                let receipt=ProcessingAudioIndex.read(URL(fileURLWithPath:path).deletingLastPathComponent().appendingPathComponent("acceptance.json"))
                if receipt["engine"] as? String==issue.engine,receipt["language"] as? String==issue.language,receipt["text"] as? String==(issue.language=="en" ? segment.english ?? "":segment.text) {
                    issue.title="已接受錄音，待輸出";issue.repaired=false;rows[key]=issue
                }
            }
        }
        let result=rows.values.sorted {($0.start,$0.language,$0.engine)<($1.start,$1.language,$1.engine)}
        studioIssueCache=result;return result
    }
    func selectIssue(_ issue:StudioIssue) {
        guard let segment=document?.segments.first(where:{$0.sources.contains(issue.index-1) || abs($0.start-issue.start)<0.001}) else{return}
        selectSegment(segment.id);previewLanguage=issue.language;previewEngine=issue.engine;tab="edit"
    }
}
extension ProjectEditor {
    var activeTrackTitle:String {L(previewLanguage=="en" ? "英文":"廣東話")+" · "+(VoiceEngineChoice.all.first {$0.id==previewEngine}?.title ?? previewEngine)}
    var activeTrackIssues:[StudioIssue] {studioIssues.filter {$0.engine==previewEngine && $0.language==previewLanguage && $0.title != "多人原聲保留"}}
    var flaggedSegments:Set<String> {
        let key=previewEngine+":"+previewLanguage
        if let cached=warningSegmentCache[key] {return cached}
        let indices=Set(activeTrackIssues.filter {!$0.repaired}.map {$0.index-1})
        let result=Set((document?.segments ?? []).filter {$0.sources.contains(where:{indices.contains($0)})}.map(\.id))
        warningSegmentCache[key]=result;return result
    }
    var repairedSegments:Set<String> {
        let key="repaired:"+previewEngine+":"+previewLanguage
        if let cached=warningSegmentCache[key] {return cached}
        let indices=Set(activeTrackIssues.filter { $0.repaired }.map {$0.index-1})
        let result=Set((document?.segments ?? []).filter {$0.sources.contains(where:{indices.contains($0)})}.map(\.id))
        warningSegmentCache[key]=result;return result
    }
    var sharedReviewSummary:[(String,Int)] {
        var result:[(String,Int)]=[]
        for (key,title) in [("sourceReviewIndices","原字幕與日文核對"),("speakerReviewIndices","角色配對"),("originalSpeechIndices","多人原聲保留")] {
            let count=Set(trackQuality.flatMap {$0[key] as? [Int] ?? []}).count
            if count>0 {result.append((title,count))}
        }
        for language in ["yue","en"] {
            let count=Set(trackQuality.filter {($0["language"] as? String ?? "yue")==language}.flatMap {$0["scriptReviewIndices"] as? [Int] ?? []}).count
            if count>0 {result.append((L(language=="en" ? "英文":"廣東話")+" · "+L("翻譯台詞"),count))}
        }
        return result
    }
}

struct StudioTrackSummary:View {
    @ObservedObject var model:AppModel
    @ObservedObject var editor:ProjectEditor
    var compact=false
    var body:some View {
        VStack(alignment:.leading,spacing:10) {
            if !compact {
                Text(L("音軌品質摘要")).font(.headline)
                ForEach(editor.document==nil ? model.dubLanguages:editor.availableDubLanguages,id:\.self) {language in
                    ForEach(VoiceEngineChoice.all.filter {(editor.document==nil ? model.selectedEngines:editor.availableVoiceEngines).contains($0.id) && $0.languages.contains(language)}) {engine in
                        let issues=editor.studioIssues.filter {$0.engine==engine.id && $0.language==language && $0.title != "多人原聲保留"}
                        let failed=issues.filter {!$0.repaired && $0.title=="生成失敗"}.count
                        let review=issues.filter {!$0.repaired && $0.title != "生成失敗"}.count
                        let repaired=issues.filter { $0.repaired }.count
                        Button {editor.previewEngine=engine.id;editor.previewLanguage=language;editor.cueFilter="all"} label:{
                            VStack(alignment:.leading,spacing:4) {
                                HStack {Text(L(language=="en" ? "英文":"廣東話")+" · "+engine.title);Spacer();if editor.previewEngine==engine.id && editor.previewLanguage==language {Image(systemName:"checkmark.circle.fill")}}
                                Text(String(format:L("%d 段生成失敗 · %d 段需試聽 · %d 段已補聲"),failed,review,repaired)).font(.caption).foregroundStyle(.secondary)
                                Text(editor.audioStatus(engine.id+":"+language)).font(.caption).foregroundStyle(.secondary)
                            }.padding(8).frame(maxWidth:.infinity,alignment:.leading)
                        }.buttonStyle(.plain).background(editor.previewEngine==engine.id && editor.previewLanguage==language ? accent.opacity(0.10):Color.primary.opacity(0.025),in:RoundedRectangle(cornerRadius:7))
                    }
                }
                if !editor.sharedReviewSummary.isEmpty {
                    DisclosureGroup(L("共用字幕及角色提示")) {ForEach(Array(editor.sharedReviewSummary.enumerated()),id:\.offset) {_,item in Text(L(item.0)+" · \(item.1) "+L("段")).font(.caption)};Text(L("共用提示不代表每條配音軌生成失敗。")).font(.caption).foregroundStyle(.secondary)}
                }
            }
            Text(editor.activeTrackTitle).font(.system(size:13,weight:.semibold))
            if compact {Text(String(format:L("%d 項待覆核 · %d 項已補聲"),editor.activeTrackIssues.filter {!$0.repaired}.count,editor.activeTrackIssues.filter {$0.repaired}.count)).font(.caption).foregroundStyle(.secondary)}
            HStack {
                Button(L("補回此音軌缺少配音")) {model.repairMissingTracks(currentTrackOnly:true)}.disabled(model.busy || !editor.activeTrackIssues.contains {$0.title=="生成失敗" && !$0.repaired})
                Button(L("重試選中對白")) {model.generateAndPlayEditor(editor.previewEngine)}.disabled(model.busy || editor.selectedSegment==nil)
            }
            Text(L("智能修復沿用已批核台詞，有限次重試原引擎；啟用互相補聲先會採用已選同語言引擎。未完成片段分音軌列出，不自動用日文補聲。")).font(.caption).foregroundStyle(.secondary)
        }
    }
}
final class StudioIssueOptions:ObservableObject {
    @Published var filter="all"
    @Published var limit=30
}
struct StudioIssueList:View {
    @ObservedObject var model:AppModel
    @ObservedObject var editor:ProjectEditor
    var edit:()->Void
    @StateObject private var options=StudioIssueOptions()
    var rows:[StudioIssue] {editor.activeTrackIssues.filter {options.filter=="all" || (options.filter=="failed" ? $0.title=="生成失敗" && !$0.repaired : options.filter=="fallback" ? $0.repaired:!$0.repaired && $0.title != "生成失敗")}}
    var body:some View {
        VStack(alignment:.leading,spacing:12) {
            Text(L("轉換校對報告")).font(.title2.bold())
            Text(L("生成失敗表示缺少有效配音；其餘項目是自動檢查提示，需要試聽確認。字幕識別差異不一定代表讀錯。點選編輯可返回時間軸比較原聲、字幕及配音。")).foregroundStyle(.secondary)
            StudioTrackSummary(model:model,editor:editor)
            Picker(L("問題篩選"),selection:$options.filter) {Text(L("全部")).tag("all");Text(L("生成失敗")).tag("failed");Text(L("待覆核")).tag("pending");Text(L("已補聲")).tag("fallback")}.pickerStyle(.segmented)
            Text(String(format:L("%d 項待覆核 · %d 項已補聲"),editor.activeTrackIssues.filter {!$0.repaired}.count,editor.activeTrackIssues.filter {$0.repaired}.count)).font(.caption).foregroundStyle(.secondary)
            ForEach(Array(rows.prefix(options.limit))) {issue in
                VStack(alignment:.leading,spacing:8) {
                    Label(L(issue.title),systemImage:issue.repaired ? "arrow.triangle.2.circlepath":"exclamationmark.triangle").font(.system(size:14,weight:.semibold)).foregroundStyle(issue.repaired ? Color.blue:Color.orange)
                    Text(String(format:L("第 %d 段 · %@ · %@"),issue.index,L(issue.language=="en" ? "英文":"廣東話"),VoiceEngineChoice.all.first {$0.id==issue.engine}?.title ?? issue.engine)).font(.caption)
                    Text(studioTimecode(issue.start)).font(.caption.monospaced())
                    if let segment=editor.document?.segments.first(where:{$0.sources.contains(issue.index-1)}) {Text(issue.language=="en" ? segment.english ?? "":segment.text).lineLimit(3)}
                    if issue.title=="生成失敗" {Text(issue.detail).font(.caption).foregroundStyle(.secondary).textSelection(.enabled)}
                    Text(L(issue.title=="生成失敗" ? "建議：重錄此段；仍失敗時，在角色頁更換同一角色的乾淨參考，或比較另一引擎。":issue.title=="時間待覆核" ? "建議：比較配音結尾與下一句，調整時間或語速。":issue.title=="聲線待覆核" ? "建議：比較同角色前後句，確認是否變聲；需要時重新生成。":"建議：先比較原聲及配音；讀字正確可以保留，需要時改稿或重錄。")).font(.callout)
                    DisclosureGroup(L("檢查詳情")) {Text(issue.detail).font(.caption).textSelection(.enabled)}
                    HStack {
                        Button(L("原聲")) {editor.selectIssue(issue);editor.playSegment(context:true)}
                        Button(L("分離")) {editor.selectIssue(issue);editor.playDialogue(context:true)}.disabled(editor.dialoguePath==nil)
                        Button(L("配音")) {editor.selectIssue(issue);editor.playEngine(issue.engine,native:true)}.disabled(editor.document?.segments.first(where:{$0.sources.contains(issue.index-1)}).flatMap {editor.engineTake(issue.engine,segmentID:$0.id)}==nil)
                        Button(L("編輯")) {editor.selectIssue(issue);edit()}
                        Button(L("重錄此段")) {editor.selectIssue(issue);model.generateAndPlayEditor(issue.engine)}.disabled(model.busy || issue.title=="多人原聲保留")
                    }
                    RecordingHistoryPanel(editor:editor,model:model,engine:issue.engine,language:issue.language,index:issue.index)
                }.padding(10).frame(maxWidth:.infinity,alignment:.leading).background(Color.primary.opacity(0.035),in:RoundedRectangle(cornerRadius:8))
            }
            if rows.count>options.limit {Button(L("顯示更多")) {options.limit+=30}}
        }
    }
}
