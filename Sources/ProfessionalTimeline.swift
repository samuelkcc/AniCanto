import SwiftUI

struct TimelineAudioRegion {
    let start:Double,end:Double
    let warning:Bool
    var speakerId:String?=nil
    var segmentID:String?=nil
}
struct TimelineMissingRegion {
    let start:Double,end:Double
    var segmentID:String?
    var reason:String
}
struct StudioLane:Identifiable {
    let id:String,title:String,kind:String,color:Color
    var engine:String?=nil
    var language:String?=nil
}
final class StudioTimelineDrag:ObservableObject {
    var lane:String?
    var id:String?
    var edge=0
    var recorded=false
    func clear(){lane=nil;id=nil;edge=0;recorded=false}
}
struct ProfessionalTimeline:View {
    @AppStorage("studioLanguage") private var interfaceLanguage="system"
    @ObservedObject var model:AppModel
    @ObservedObject var editor:ProjectEditor
    @ObservedObject var live:LiveVideoPreview
    @Binding var allTracks:Bool
    var showCuts:()->Void
    @StateObject private var drag=StudioTimelineDrag()
    @StateObject private var navigation=TimelineNavigation()
    var duration:Double {max(1,editor.document==nil ? live.duration:editor.duration)}
    var seconds:Double {usesProcessingPreview(model,editor,live) ? live.seconds:editor.seconds}
    func roleCode(_ id:String)->String {editor.profiles.firstIndex(where:{$0.id==id}).map {String(format:"R%02d",$0+1)} ?? "R?"}
    func laneHeight(_ lane:StudioLane)->Double {lane.kind=="captions" ? 56:lane.kind=="audio" ? 30:24}
    func laneTop(_ index:Int)->Double {32+lanes.prefix(index).reduce(0) {$0+laneHeight($1)}}
    func laneIndex(at y:Double)->Int? {TimelineHitTest.lane(at:y,heights:lanes.map {laneHeight($0)})}
    func selectedTrack(_ lane:StudioLane)->Bool {lane.kind=="audio" && lane.engine==editor.previewEngine && lane.language==editor.previewLanguage}
    func regions(_ lane:StudioLane)->[TimelineAudioRegion] {
        if usesProcessingPreview(model,editor,live) {return live.takes.filter {$0.engine==lane.engine && $0.language==lane.language}.map {TimelineAudioRegion(start:$0.start,end:$0.end,warning:false,speakerId:$0.speakerID,segmentID:$0.editorID)}}
        return editor.timelineAudioRegions[lane.id] ?? []
    }
    func detailZoom()->Double {min(80,max(1,duration/45))}
    func tile(at time:Double,width:Double)->Int {max(0,min(Int(ceil(width/1200))-1,Int(max(0,min(duration,time))/duration*width/1200)))}
    var lanes:[StudioLane] {
        var rows=[StudioLane(id:"video",title:L("影片"),kind:"video",color:.blue),StudioLane(id:"ja",title:L("日語原聲"),kind:"original",color:.teal),StudioLane(id:"background",title:L("背景音樂／音效"),kind:"background",color:.gray),StudioLane(id:"captions",title:L("字幕"),kind:"captions",color:accent),StudioLane(id:"speech",title:L("配音時段 · 可 trim"),kind:"speech",color:.orange)]
        let selection=editor.document==nil ? nil:editor.productionSelection(model)
        let submitted=model.submittedVoiceSelection(video:editor.selectedRow?.video)
        let processing=usesProcessingPreview(model,editor,live)
        let savedLanguages=submitted?.languages ?? (processing ? live.requestedLanguages:nil) ?? (editor.document==nil ? model.dubLanguages:editor.availableDubLanguages)
        let languages=allTracks ? ["yue","en"].filter {savedLanguages.contains($0) || (submitted==nil && selection?.languages.contains($0)==true)}:[savedLanguages.contains(editor.previewLanguage) ? editor.previewLanguage:savedLanguages.first ?? "yue"]
        let available=submitted?.engines ?? (processing ? live.requestedEngines:nil) ?? (editor.document==nil ? model.selectedEngines:editor.availableVoiceEngines)
        let requested=(VoiceEngineChoice.all.map(\.id)+["gpt-sovits-v3","qwen-tts"]).filter {available.contains($0) || (submitted==nil && selection?.engines.contains($0)==true)}
        let retained=requested.filter {$0 != "qwen-tts" || languages.contains {!(editor.timelineAudioRegions["qwen-tts:"+$0] ?? []).isEmpty}}
        let engines=retained.isEmpty ? model.selectedEngines:retained
        for language in languages {for engine in engines where VoiceEngineChoice.all.first(where:{$0.id==engine})?.languages.contains(language) ?? true {
            let name=editor.recordedTrackTitle(engine,language:language)
            rows.append(StudioLane(id:engine+":"+language,title:L(language=="en" ? "英文":"廣東話")+" · "+name,kind:"audio",color:language=="en" ? .green:.purple,engine:engine,language:language))
        }}
        return rows
    }
    var body:some View {
        VStack(spacing:0) {
            HStack(spacing:10) {
                Text(L("時間軸")).font(.system(size:14,weight:.semibold))
                Button {editor.bladeClip();showCuts()} label:{Label(L("分割影片"),systemImage:"scissors")}.disabled(editor.document==nil)
                Button(action:showCuts) {Label(L("剪接設定"),systemImage:"crop")}.disabled(editor.document==nil)
                Button(L("新增對白")) {editor.addDialogue()}.disabled(editor.document==nil)
                Image(systemName:"questionmark.circle").foregroundStyle(.secondary).help(L("拖時間尺移動；點字幕跳轉；點配音試聽"))
                Divider().frame(height:18)
                Toggle(L("全部配音軌"),isOn:$allTracks).toggleStyle(.checkbox)
                Spacer()
                Button {editor.timelineZoom=1} label:{Image(systemName:"arrow.left.and.right.righttriangle.left.righttriangle.right")}.help(L("顯示全片"))
                Image(systemName:"minus.magnifyingglass")
                Slider(value:$editor.timelineZoom,in:1...80).frame(width:140)
                Image(systemName:"plus.magnifyingglass")
                Text(String(format:"%.1f×",editor.timelineZoom)).font(.system(size:13,design:.monospaced)).frame(width:48)
            }.padding(.horizontal,12).frame(height:46).background(StudioPalette.panel)
            Divider()
            GeometryReader {g in
                let width=max(300,g.size.width-240)*editor.timelineZoom
                let canvasHeight=32+lanes.reduce(0) {$0+laneHeight($1)}
                ScrollView(.vertical) {
                    HStack(alignment:.top,spacing:0) {
                        VStack(spacing:0) {
                            HStack {Text(studioTimecode(seconds)).font(.system(size:13,weight:.medium,design:.monospaced));Spacer()}.padding(.horizontal,10).frame(height:32)
                            ForEach(lanes) {lane in
                                Button {
                                    guard let engine=lane.engine,let language=lane.language else{return}
                                    editor.selectVoiceTrack(engine,language:language);live.stopInspection()
                                } label:{
                                    HStack(spacing:8) {RoundedRectangle(cornerRadius:2).fill(lane.color).frame(width:4,height:18);Group {
                                        if let engine=lane.engine {
                                            VStack(alignment:.leading,spacing:0) {
                                                Text(editor.recordedTrackTitle(engine,language:lane.language ?? "yue")).font(.system(size:12,weight:.semibold)).lineLimit(1)
                                                Text(L(lane.language=="en" ? "英文":"廣東話")).font(.system(size:10)).foregroundStyle(.secondary).lineLimit(1)
                                            }
                                        } else {Text(lane.title).font(.system(size:12)).lineLimit(1)}
                                    }.help(lane.title);Spacer(minLength:0);if selectedTrack(lane) {Image(systemName:"speaker.wave.2.fill").foregroundStyle(accent)}}.padding(.horizontal,10).frame(height:laneHeight(lane)).contentShape(Rectangle())
                                }.buttonStyle(.plain).disabled(lane.engine==nil)
                                    .background(selectedTrack(lane) ? accent.opacity(0.14):Color.primary.opacity(0.025)).overlay(alignment:.bottom) {Divider()}
                                    .accessibilityLabel(lane.title).accessibilityIdentifier("timeline-track-"+lane.id)
                            }
                        }.frame(width:240).background(StudioPalette.panel)
                        ScrollViewReader {proxy in
                            ScrollView(.horizontal) {
                                // Render visible tiles only. A long episode at editing
                                // zoom must not create one enormous backing texture.
                                LazyHStack(spacing:0) {
                                    ForEach(0..<max(1,Int(ceil(width/1200))),id:\.self) {index in
                                        let origin=Double(index)*1200
                                        let tileWidth=min(1200,width-origin)
                                        Canvas(rendersAsynchronously:true) {context,size in draw(context:&context,size:size,fullWidth:width,origin:origin)}
                                            .frame(width:tileWidth,height:canvasHeight).id(index)
                                            .contentShape(Rectangle())
                                            .gesture(DragGesture(minimumDistance:0).onChanged {value in handle(value,width:width,origin:origin)}.onEnded {value in if value.startLocation.y<32 && abs(value.translation.width)<4 {let t=min(duration,max(0,(value.location.x+origin)/width*duration));editor.seek(t);live.seek(t)} else {audition(value,width:width,origin:origin)};navigation.endPan();drag.clear()})
                                            .accessibilityLabel(L("影片、字幕及配音時間軸。拖動字幕或配音時段邊界可以裁切。"))
                                            .onDrop(of:["public.utf8-plain-text"],isTargeted:nil) {providers,point in assignRole(providers,at:CGPoint(x:point.x+origin,y:point.y),width:width)}
                                    }
                                }.background(TimelineScrollProbe(navigation:navigation))
                            }
                            .frame(height:canvasHeight+20)
                            .onChange(of:seconds) {time in
                                let following=usesProcessingPreview(model,editor,live) ? live.follow:editor.followPlaybackText
                                if following {navigation.reveal(time:time,duration:duration,width:width)}
                            }
                            .onChange(of:live.follow) {follow in if follow {editor.followPlaybackText=true;navigation.reveal(time:seconds,duration:duration,width:width,force:true)}}
                            .onChange(of:editor.manualNavigation) {_ in navigation.reveal(time:editor.seconds,duration:duration,width:width,force:true)}
                            .onChange(of:editor.timelineZoom) {_ in proxy.scrollTo(tile(at:seconds,width:width),anchor:.leading)}
                        }
                    }
                }
            }
        }.background(StudioPalette.base)
        .onAppear {editor.timelineZoom=detailZoom();navigation.onUserScroll={live.follow=false;editor.followPlaybackText=false}}
        .onChange(of:editor.selected) {_ in editor.timelineZoom=detailZoom()}
        .onChange(of:editor.document?.review) {_ in editor.timelineZoom=detailZoom()}
        .onChange(of:live.duration) {_ in if editor.document==nil {editor.timelineZoom=detailZoom()}}
    }
    func draw(context:inout GraphicsContext,size:CGSize,fullWidth:Double,origin:Double) {
        let width=fullWidth
        context.translateBy(x:-origin,y:0)
        context.fill(Path(CGRect(x:origin,y:0,width:size.width,height:size.height)),with:.color(StudioPalette.base))
        let step=[1.0,2,5,10,15,30,60,120,300,600,1800].first {$0>=duration/max(1,width/110)} ?? 3600
        for t in stride(from:0.0,through:duration,by:step) {
            let x=t/duration*width
            guard x>=origin-110,x<=origin+size.width else {continue}
            var line=Path();line.move(to:CGPoint(x:x,y:26));line.addLine(to:CGPoint(x:x,y:size.height));context.stroke(line,with:.color(Color.primary.opacity(0.10)),lineWidth:1)
            if x+90<width {context.draw(Text(studioTimecode(t)).font(.system(size:12,design:.monospaced)),at:CGPoint(x:x+4,y:14),anchor:.leading)}
        }
        for (i,lane) in lanes.enumerated() {
            let y=laneTop(i),height=laneHeight(lane)
            if selectedTrack(lane) {context.fill(Path(CGRect(x:origin,y:y,width:size.width,height:height)),with:.color(accent.opacity(0.08)))}
            context.stroke(Path(CGRect(x:0,y:y+height,width:width,height:0.5)),with:.color(StudioPalette.border),lineWidth:0.5)
            func block(_ start:Double,_ end:Double,_ title:String,_ selected:Bool=false,_ available:Bool=true,_ warning:Bool=false,_ role:String?=nil) {
                let tint=role.map {roleColor($0)} ?? lane.color
                let a=max(0,start),b=min(duration,end);guard b>a else{return}
                let rect=CGRect(x:a/duration*width,y:y+3,width:max(2,(b-a)/duration*width),height:height-6)
                guard rect.maxX>=origin,rect.minX<=origin+size.width else{return}
                let path=Path(roundedRect:rect,cornerRadius:3)
                context.fill(path,with:.color(tint.opacity(available ? 0.50:0.10)))
                context.stroke(path,with:.color(warning ? .red:selected ? .orange:tint.opacity(0.7)),style:StrokeStyle(lineWidth:selected ? 2:1,dash:available ? []:[3,3]))
                if rect.width>28 && (!title.isEmpty || role != nil) {
                    let contextCopy=context
                    context.clip(to:Path(rect))
                    let label=(role.map {roleCode($0)+(title.isEmpty ? "":" · ")} ?? "")+title
                    context.draw(Text(label).font(.system(size:12)).foregroundColor(.primary),in:rect.insetBy(dx:4,dy:2))
                    // Each label has its own clip; restore the tile clip for the next block.
                    context=contextCopy
                }
            }
            switch lane.kind {
            case "video":
                if let doc=editor.document {for (n,clip) in doc.clips.enumerated() {block(clip.start,clip.end,L("片段")+" \(n+1)",false,clip.enabled)}}
                else if !model.batchItems.isEmpty {block(0,duration,editor.selectedRow?.name ?? L("原片"))}
            case "captions","speech":
                if let document=editor.document {
                    for segment in document.segments {
                        let text=lane.kind=="captions" ? (editor.previewLanguage=="en" ? segment.english ?? "":segment.captionText.isEmpty ? segment.text:segment.captionText):""
                        block(lane.kind=="captions" ? segment.captionStart:segment.start,lane.kind=="captions" ? segment.captionEnd:segment.end,text,segment.id==editor.selectedSegment,segment.enabled,editor.flaggedSegments.contains(segment.id),segment.speakerId)
                    }
                } else if lane.kind=="captions" {
                    for cue in live.cues {let translated=cue.text(editor.previewLanguage);block(cue.start,cue.end,translated.isEmpty ? cue.original:translated,cue.start<=seconds && seconds<cue.end,true)}
                }
            case "original","background":
                let values=editor.waveforms[lane.kind=="original" ? "dialoguePath":"backgroundPath"] ?? []
                if !values.isEmpty {
                    var path=Path()
                    for (n,value) in values.enumerated() {let x=Double(n)/Double(max(1,values.count-1))*width;path.move(to:CGPoint(x:x,y:y+12-Double(value)*8));path.addLine(to:CGPoint(x:x,y:y+12+Double(value)*8))}
                    context.stroke(path,with:.color(lane.color),lineWidth:1)
                } else if lane.kind=="original",!model.batchItems.isEmpty || editor.document != nil {block(0,duration,L("原聲"))}
                else {context.draw(Text(L("未有分離音軌")).font(.system(size:12)).foregroundColor(.secondary),at:CGPoint(x:10,y:y+12),anchor:.leading)}
            default:
                for missing in editor.timelineMissingRegions[lane.id] ?? [] {
                    block(missing.start,missing.end,L("缺聲"),selectedTrack(lane) && missing.segmentID==editor.selectedSegment,false,true)
                }
                let available=regions(lane)
                if !available.isEmpty {for region in available {
                    let segment=region.segmentID.flatMap {id in editor.document?.segments.first {$0.id==id}}
                    block(region.start,region.end,"",selectedTrack(lane) && segment?.id==editor.selectedSegment,true,region.warning,segment?.speakerId ?? region.speakerId)
                }}
                else {context.draw(Text(editor.audioStatus(lane.id)).font(.system(size:12)).foregroundColor(.secondary),at:CGPoint(x:10,y:y+12),anchor:.leading)}
            }
        }
        let x=min(width,max(0,seconds/duration*width))
        var playhead=Path();playhead.move(to:CGPoint(x:x,y:0));playhead.addLine(to:CGPoint(x:x,y:size.height));context.stroke(playhead,with:.color(.red),lineWidth:1.5)
    }
    func handle(_ value:DragGesture.Value,width:Double,origin:Double=0) {
        let t=min(duration,max(0,(value.location.x+origin)/width*duration))
        if value.startLocation.y<32 {
            live.follow=false;editor.followPlaybackText=false
            if abs(value.translation.width)>=4 {navigation.pan()}
            return
        }
        guard let document=editor.document else {
            live.follow=false;live.player.pause()
            let initial=(value.startLocation.x+origin)/width*duration
            if value.translation == .zero,let cue=live.cues.first(where:{$0.start<=initial && initial<$0.end}) {live.seek(cue.start)} else {live.seek(t)}
            return
        }
        live.follow=false;live.player.pause()
        if editor.playingVersion != nil {editor.playSource()}
        let index=laneIndex(at:value.startLocation.y) ?? -1
        guard value.startLocation.y>=32,lanes.indices.contains(index) else {editor.seek(t);live.seek(t);return}
        let lane=lanes[index]
        // Audio selection happens on release. Selecting a cue on mouse-down
        // used to force-scroll the canvas out from underneath the pointer.
        if lane.kind=="audio" {
            editor.followPlaybackText=false
            if !TimelineHitTest.isClick(value.startLocation,value.location) {editor.seek(t);live.seek(t)}
            return
        }
        let initial=(value.startLocation.x+origin)/width*duration
        if drag.lane==nil {
            drag.lane=lane.kind
            if lane.kind=="video",let clip=document.clips.first(where:{$0.start<=initial && $0.end>=initial}) {drag.id=clip.id;drag.edge=abs(initial-clip.start)/duration*width<8 ? -1:abs(initial-clip.end)/duration*width<8 ? 1:0}
            else if let s=document.segments.first(where:{(lane.kind=="captions" ? $0.captionStart:$0.start)<=initial && (lane.kind=="captions" ? $0.captionEnd:$0.end)>=initial}) {
                editor.followPlaybackText=false;editor.selectSegment(s.id,reveal:false);live.seek(s.start);drag.id=s.id
                let a=lane.kind=="captions" ? s.captionStart:s.start,b=lane.kind=="captions" ? s.captionEnd:s.end
                if ["captions","speech"].contains(lane.kind) {drag.edge=abs(initial-a)/duration*width<8 ? -1:abs(initial-b)/duration*width<8 ? 1:0}
                if let engine=lane.engine {editor.previewEngine=engine;editor.previewLanguage=lane.language ?? "yue"}
            }
        }
        if drag.edge != 0 {
            if drag.lane=="video",let i=document.clips.firstIndex(where:{$0.id==drag.id}) {editor.update(recordUndo:!drag.recorded) {doc in if drag.edge<0 {doc.clips[i].start=min(t,doc.clips[i].end-0.05)} else {doc.clips[i].end=max(t,doc.clips[i].start+0.05)}}}
            else {editor.updateSegment(recordUndo:!drag.recorded) {s in if drag.lane=="captions" {if drag.edge<0 {s.captionStart=min(t,s.captionEnd-0.05)} else {s.captionEnd=max(t,s.captionStart+0.05)}} else {if drag.edge<0 {s.start=min(t,s.end-0.05)} else {s.end=max(t,s.start+0.05)}}}}
            editor.followPlaybackText=false;drag.recorded=true
        } else {
            if value.translation == .zero,let id=drag.id,let s=document.segments.first(where:{$0.id==id}) {editor.seek(s.start);live.seek(s.start)}
            else {editor.seek(t);live.seek(t)}
        }
    }
    func assignRole(_ providers:[NSItemProvider],at point:CGPoint,width:Double)->Bool {
        guard !model.busy,let doc=editor.document,let provider=providers.first,
              let index=laneIndex(at:point.y),
              ["captions","speech","audio"].contains(lanes[index].kind) else{return false}
        let time=point.x/width*duration,lane=lanes[index]
        guard let segment=doc.segments.first(where:{(lane.kind=="captions" ? $0.captionStart:$0.start)<=time && time<(lane.kind=="captions" ? $0.captionEnd:$0.end)}) else{return false}
        provider.loadObject(ofClass:NSString.self) {object,_ in
            guard let value=object as? String,value.hasPrefix("anicanto-role:") else{return}
            let role=String(value.dropFirst("anicanto-role:".count))
            DispatchQueue.main.async {guard editor.profiles.contains(where:{$0.id==role}) else{return};editor.update {d in if let i=d.segments.firstIndex(where:{$0.id==segment.id}) {d.segments[i].speakerId=role;d.segments[i].audioTake=nil}}}
        };return true
    }
    func audition(_ value:DragGesture.Value,width:Double,origin:Double=0) {
        guard let index=laneIndex(at:value.startLocation.y),let engine=lanes[index].engine,let language=lanes[index].language else{return}
        let click=TimelineHitTest.isClick(value.startLocation,value.location)
        let time=TimelineHitTest.time(at:click ? value.startLocation.x:value.location.x,origin:origin,width:width,duration:duration)
        if usesProcessingPreview(model,editor,live) {
            editor.selectVoiceTrack(engine,language:language);editor.followPlaybackText=false;live.follow=false;live.stopInspection()
            if click,let take=live.takes.first(where:{$0.engine==engine && $0.language==language && $0.start<=time && time<$0.end}) {live.playTake(take)}
            else {live.stopAudition();live.seek(time)}
        } else {live.stopInspection();_ = editor.selectTimelineVoice(engine,language:language,at:time,play:click)}
    }

}
