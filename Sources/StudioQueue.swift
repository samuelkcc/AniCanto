import SwiftUI

struct StudioQueuedVideo:Identifiable {
    var id:String
    var video:String
    var engine:String
    var languages:[String]
    var active:Bool
    static func rows(_ requests:[Data],active:Data?)->[Self] {
        let entries=active.map {[$0]} ?? []
        return (entries+requests).enumerated().flatMap {index,data->[Self] in
            guard let cfg=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any] else{return []}
            let videos=cfg["videos"] as? [[String:Any]] ?? [cfg]
            return videos.enumerated().compactMap {offset,item in
                guard let video=item["video"] as? String else{return nil}
                return Self(id:"\(index)-\(offset)",video:video,engine:cfg["ttsBackend"] as? String ?? "",languages:cfg["dubLanguages"] as? [String] ?? ["yue"],active:active != nil && index==0)
            }
        }
    }
}
struct StudioQueueView:View {
    @ObservedObject var model:AppModel
    @AppStorage("studioLanguage") private var language="system"
    @AppStorage("studioInterfaceMode") private var mode="simple"
    var rows:[StudioQueuedVideo] {StudioQueuedVideo.rows(model.pendingBatchRequests,active:model.busy ? model.currentBatchRequest:nil)}
    var tasks:[EditorialTask] {model.editorTasks.filter {["queued","running","failed"].contains($0.status)}}
    var body:some View {
        VStack(alignment:.leading,spacing:24) {
            HStack {
                VStack(alignment:.leading,spacing:6) {
                    Text(L("已保存嘅製作工作")).font(.title2.bold())
                    Text(L("影片轉換同單句重錄會喺同一個排程依次執行。")).foregroundStyle(.secondary)
                }
                Spacer()
                if mode=="simple" && (model.busy || model.hasSavedWork) {ProcessingQueueButton(model:model,iconOnly:false)}
            }
            if rows.isEmpty && tasks.isEmpty {
                VStack(spacing:12) {
                    Image(systemName:"checklist").font(.system(size:38)).foregroundStyle(accent)
                    Text(L("未有待處理工作")).font(.headline)
                    Text(L("加入影片並開始製作後，工作會顯示喺呢度。")).foregroundStyle(.secondary)
                    Button(L("返回工作區")) {model.section = .studio;model.projectEditor.workspacePage="edit"}
                }.frame(maxWidth:.infinity).padding(.vertical,64)
            }
            if !rows.isEmpty {
                Text(L("影片轉換")).font(.headline)
                ForEach(rows) {row in
                    HStack(spacing:16) {
                        Image(systemName:row.active ? "circle.dotted":"film").foregroundStyle(accent)
                        VStack(alignment:.leading,spacing:6) {
                            Text(URL(fileURLWithPath:row.video).lastPathComponent).font(.headline).lineLimit(2)
                            Text((VoiceEngineChoice.all.first {$0.id==row.engine}?.title ?? row.engine)+" · "+row.languages.map {L($0=="en" ? "英文":"廣東話")}.joined(separator:" + ")).font(.callout).foregroundStyle(.secondary)
                        }
                        Spacer()
                        Text(L(row.active ? "處理中":model.queuePaused ? "已暫停":"待處理")).foregroundStyle(.secondary)
                        Button(L("檢視")) {
                            if let project=model.projectEditor.projects.first(where:{$0.video==row.video}) {model.projectEditor.open(project)}
                            model.section = .studio;model.projectEditor.workspacePage="edit"
                        }
                    }.padding(18).background(StudioPalette.panel,in:RoundedRectangle(cornerRadius:12))
                }
            }
            if !tasks.isEmpty {
                Text(L("編輯排程")).font(.headline)
                ForEach(tasks) {task in
                    HStack(spacing:16) {
                        Image(systemName:"waveform").foregroundStyle(accent)
                        VStack(alignment:.leading,spacing:6) {
                            Text(String(format:L("版本 %@ · %@"),String(task.id.prefix(8)),L(editorStatus(task.status)))).font(.headline)
                            if !task.message.isEmpty {Text(localizedProgressDetail(task.message)).font(.callout).foregroundStyle(.orange)}
                        }
                        Spacer()
                        if task.status=="failed" {Button(L("重試")) {if let i=model.editorTasks.firstIndex(where:{$0.id==task.id}) {model.editorTasks[i].status="queued";model.saveEditorQueue();model.pumpEditorQueue()}}.disabled(model.busy)}
                        if task.status=="queued" {Button(L("取消排隊")) {model.editorTasks.removeAll {$0.id==task.id};model.saveEditorQueue()}}
                    }.padding(18).background(StudioPalette.panel,in:RoundedRectangle(cornerRadius:12))
                }
            }
        }.frame(maxWidth:.infinity,alignment:.leading)
    }
}
