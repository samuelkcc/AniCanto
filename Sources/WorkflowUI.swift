import SwiftUI

struct ConversionQuest:View {
    let step:JourneyStep
    let visited:Set<JourneyStep>
    let running:Bool
    let failed:Bool
    let finished:Bool
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase
    var body:some View {
        TimelineView(.animation(minimumInterval:0.45,paused:!running || reduceMotion || scenePhase != .active)) { context in
            let bounce=running && !reduceMotion && scenePhase == .active && Int(context.date.timeIntervalSinceReferenceDate/0.45)%2 == 0
            HStack(spacing:0) {
                ForEach(JourneyStep.allCases,id:\.rawValue) { station in
                    let active=station == step && !finished
                    let cleared=finished || (visited.contains(station) && station != step)
                    VStack(spacing:3) {
                        ZStack(alignment:.bottomTrailing) {
                            Image(systemName:station.icon).font(.system(size:17,weight:.semibold))
                                .frame(width:38,height:32)
                                .background((active ? accent : cleared ? Color.green : Color.secondary).opacity(0.1),in:RoundedRectangle(cornerRadius:10))
                                .foregroundStyle(active ? accent : cleared ? .green : .secondary)
                            if active {
                                QuestBuddy(warning:failed).frame(width:29,height:32)
                                    .offset(x:-25,y:bounce ? -5 : -2)
                            } else if cleared {Image(systemName:"checkmark.circle.fill").font(.system(size:10)).foregroundStyle(.green).background(.background,in:Circle()).offset(x:3,y:2)}
                        }
                        Text(LocalizedStringKey(station.title)).font(.system(size:10,weight:active ? .bold : .regular)).foregroundStyle(active ? .primary : .secondary).lineLimit(1)
                    }.frame(maxWidth:.infinity)
                    if station != .export {
                        Image(systemName:"chevron.right").font(.system(size:9,weight:.bold)).foregroundStyle(.tertiary)
                    }
                }
            }.padding(.top,6).padding(.bottom,3)
        }.accessibilityElement(children:.ignore)
            .accessibilityLabel(Text(L("製作路線")))
            .accessibilityValue(Text(LocalizedStringKey(finished ? "完成" : step.title)))
    }
}

/// Small native mascot; no extra image, model or inference required.
struct QuestBuddy:View {
    let warning:Bool
    var body:some View {
        Canvas { context,size in
            let color=warning ? Color.orange : accent
            context.fill(Path(roundedRect:CGRect(x:4,y:2,width:21,height:20),cornerRadius:7),with:.color(color))
            context.fill(Path(roundedRect:CGRect(x:7,y:6,width:15,height:11),cornerRadius:4),with:.color(.white))
            for x in [10.0,18.0] {context.fill(Path(ellipseIn:CGRect(x:x,y:9,width:2,height:3)),with:.color(color))}
            context.fill(Path(roundedRect:CGRect(x:8,y:23,width:13,height:6),cornerRadius:3),with:.color(color))
            for x in [7.0,18.0] {context.fill(Path(roundedRect:CGRect(x:x,y:29,width:5,height:3),cornerRadius:1),with:.color(color))}
            for x in [1.0,25.0] {context.fill(Path(roundedRect:CGRect(x:x,y:9,width:3,height:8),cornerRadius:1),with:.color(color))}
        }.accessibilityHidden(true)
    }
}

struct StudioProgressBar:View {
    let value:Double?
    var body:some View {
        if let value {
            GeometryReader { geometry in
                ZStack(alignment:.leading) {
                    Capsule().fill(accent.opacity(0.13))
                    Capsule().fill(LinearGradient(colors:[accent,AnimeStyle.current.secondary],startPoint:.leading,endPoint:.trailing))
                        .frame(width:geometry.size.width*min(1,max(0,value)))
                }
            }.frame(height:7).accessibilityElement(children:.ignore)
                .accessibilityLabel(Text(L("流程進度"))).accessibilityValue(Text("\(Int(value*100))%"))
        } else {
            ProgressView().progressViewStyle(.linear).tint(accent).frame(maxWidth:.infinity)
        }
    }
}

extension ContentView {
    var workflowAdvanced:some View {
        Button {m.advancedSettings=WorkflowDraft(model:m,topic:.translation)} label:{
            HStack {
                Image(systemName:"slider.horizontal.3")
                Text(L("更多轉換設定"))
                Spacer()
                Image(systemName:"chevron.right").font(.caption)
            }.font(.system(size:12,weight:.semibold)).padding(11)
                .background(accent.opacity(0.08),in:RoundedRectangle(cornerRadius:10))
                .overlay(RoundedRectangle(cornerRadius:10).stroke(accent.opacity(0.2)))
        }.buttonStyle(.plain).disabled(m.busy).accessibilityIdentifier("workflow-settings")
    }
}
final class TerminalOptions: ObservableObject {
    @Published var search=""
    @Published var errorsOnly=false
    @Published var follow=true
    @Published var source="summary"
    @Published var raw=""
    @Published var jobLogs:[String]=[]
    func discover(root:URL,job:String?) {
        guard let job else {jobLogs=[];return}
        let folder=URL(fileURLWithPath:job).standardizedFileURL
        guard folder.path.hasPrefix(root.appendingPathComponent("jobs").path+"/") else {jobLogs=[];return}
        jobLogs=((try? FileManager.default.contentsOfDirectory(at:folder,includingPropertiesForKeys:nil)) ?? [])
            .filter {$0.pathExtension == "log"}.map {String($0.path.dropFirst(root.path.count+1))}.sorted()
    }
    func refresh(root:URL) {
        guard source != "summary" else { return }
        guard let file=try? FileHandle(forReadingFrom:root.appendingPathComponent(source)) else {raw="";return}
        defer {try? file.close()}
        let end=(try? file.seekToEnd()) ?? 0
        try? file.seek(toOffset:end > 262144 ? end-262144:0)
        raw=String(decoding:(try? file.readToEnd()) ?? Data(),as:UTF8.self)
    }
}
struct TerminalLogView: View {
    @ObservedObject var model:AppModel
    var embedded=false
    @StateObject private var options=TerminalOptions()
    private var lines:[String] {options.source == "summary" ? model.logs:options.raw.replacingOccurrences(of:"\r",with:"\n").components(separatedBy:"\n")}
    private let refreshTimer=Timer.publish(every:2,on:.main,in:.common).autoconnect()
    private var bg:Color {StudioPalette.base}
    var body: some View {
        VStack(spacing:0) {
            HStack(spacing:10) {
                Image(systemName:"terminal.fill").foregroundStyle(accent)
                Text("AniCanto / " + L("終端機")).font(.system(.headline,design:.monospaced))
                Spacer()
                Button(L("複製全部")) { NSPasteboard.general.clearContents();NSPasteboard.general.setString(lines.joined(separator:"\n"),forType:.string) }
                Button(L("紀錄資料夾")) { NSWorkspace.shared.open(model.engine.root) }
                Button(L("關閉紀錄")) {if embedded {model.projectEditor.workspacePage="edit"} else {model.showLogs=false}}.keyboardShortcut(.cancelAction)
            }.padding(16).background(StudioPalette.panel)
            if !model.resultSummary.isEmpty {ScrollView {Text(model.resultSummary).font(.system(.caption,design:.monospaced)).textSelection(.enabled).frame(maxWidth:.infinity,alignment:.leading)}.frame(maxHeight:150).padding(12).background(Color.orange.opacity(0.12))}
            HStack {
                Picker(L("紀錄來源"),selection:$options.source) {
                    Text(L("流程摘要")).tag("summary")
                    Text(L("程序原始輸出 · stdout / stderr")).tag("developer-process.log")
                    Text(L("MLX 文字服務")).tag("mlx-text.log")
                    Text(L("Ollama 服務")).tag("ollama.log")
                    ForEach(options.jobLogs,id:\.self) {path in Text(URL(fileURLWithPath:path).lastPathComponent).tag(path)}
                }.frame(width:360)
                Text(L("最近 256 KB · 每 2 秒更新")).font(.caption).foregroundStyle(.secondary)
                Spacer()
            }.padding(.horizontal,12).padding(.top,12)
            HStack {
                TextField(L("搜尋紀錄"),text:$options.search).textFieldStyle(.roundedBorder)
                Toggle(L("只睇錯誤"),isOn:$options.errorsOnly)
                Toggle(L("跟隨最新"),isOn:$options.follow)
            }.font(.caption).padding(12)
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment:.leading,spacing:5) {
                        if lines.allSatisfy({$0.isEmpty}) { Text(L("$ 等待所選程序輸出…")).foregroundStyle(accent) }
                        ForEach(Array(lines.enumerated()),id:\.offset) { i,line in
                            if (options.search.isEmpty || line.localizedCaseInsensitiveContains(options.search)) && (!options.errorsOnly || line.contains("錯誤") || line.contains("失敗") || line.contains("缺") || line.contains("需修正") || line.lowercased().contains("error")) {
                                HStack(alignment:.top,spacing:14) {
                                    Text(String(format:"%03d",i+1)).foregroundStyle(.secondary).frame(width:30)
                                    Text(line).foregroundStyle(line.contains("錯誤") || line.contains("失敗") || line.contains("缺") || line.contains("需修正") || line.lowercased().contains("error") ? Color.orange : Color.primary).textSelection(.enabled).frame(maxWidth:.infinity,alignment:.leading)
                                }
                            }
                        }
                        Color.clear.frame(height:1).id("tail")
                    }.font(.system(size:14,design:.monospaced)).padding(16)
                }.onChange(of:lines.last) { _ in if options.follow { proxy.scrollTo("tail",anchor:.bottom) } }
            }
            HStack { Circle().fill(model.busy ? accent : .gray).frame(width:6,height:6);Text(L(model.busy ? "程序運行中":"閒置"));Spacer();Text(String(format:L("%d 行 · 只喺本機"),lines.count)) }.font(.system(size:10,design:.monospaced)).foregroundStyle(.secondary).padding(12)
        }.frame(minWidth:760,maxWidth:.infinity,minHeight:520,maxHeight:.infinity).background(bg).foregroundStyle(.primary)
        .onAppear {options.source="developer-process.log";options.discover(root:model.engine.root,job:model.developerJob);options.refresh(root:model.engine.root)}
        .onChange(of:options.source) { _ in options.refresh(root:model.engine.root) }
        .onReceive(refreshTimer) { _ in options.discover(root:model.engine.root,job:model.developerJob);options.refresh(root:model.engine.root) }
    }
}
