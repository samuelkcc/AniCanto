import SwiftUI

/// Tile-local coordinates share one half-open layout for drawing and input.
enum TimelineHitTest {
    static func lane(at y:Double,heights:[Double])->Int? {
        guard y.isFinite,y>=32 else{return nil}
        var top=32.0
        for (i,height) in heights.enumerated() {if y<top+height {return i};top += height}
        return nil
    }
    static func time(at x:Double,origin:Double,width:Double,duration:Double)->Double {
        min(duration,max(0,(x+origin)/max(1,width)*duration))
    }
    static func isClick(_ start:CGPoint,_ end:CGPoint)->Bool {abs(end.x-start.x)<6 && abs(end.y-start.y)<6}
}

extension ProjectEditor {
    func matchesVersionPreview(_ take:ProcessingVoiceTake,segment:EditSegment)->Bool {
        let expected=take.language=="en" ? segment.english ?? "":segment.text
        return !expected.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty && take.text==expected &&
            abs(take.start-segment.start)<0.001 && abs(take.end-segment.end)<0.001 &&
            (take.editorID.map {$0==segment.id} ?? (take.speakerID==segment.speakerId)) &&
            take.seed==segment.take && take.rate==segment.rate && take.trimStart==segment.trimStart && take.trimEnd==segment.trimEnd &&
            ProcessingAudioIndex.length(take.path) != nil
    }
    /// All completed takes visible to playback also belong on their timeline
    /// lane, including earlier engines while the current version is rendering.
    func mergePreviewTimelineRegions() {
        guard let document else{return}
        let ids=Dictionary(document.segments.map {($0.id,$0)},uniquingKeysWith:{first,_ in first})
        for take in versionPreviewTakes {
            let segment=take.editorID.flatMap {ids[$0]} ?? document.segments.first {abs($0.start-take.start)<0.001 && abs($0.end-take.end)<0.001}
            guard let segment,matchesVersionPreview(take,segment:segment) else{continue}
            let key=take.engine+":"+take.language
            guard !(timelineAudioRegions[key] ?? []).contains(where:{$0.segmentID==segment.id || (abs($0.start-take.start)<0.001 && abs($0.end-take.end)<0.001)}) else{continue}
            timelineAudioRegions[key,default:[]].append(TimelineAudioRegion(start:take.start,end:take.end,warning:false,speakerId:take.speakerID,segmentID:segment.id))
        }
    }
    func selectVoiceTrack(_ engine:String,language:String) {
        player.pause();audio.pause();clearAuditionStop();auditionLabel=""
        previewEngine=engine;previewLanguage=language
    }
    /// Resolve the clicked audio region before selecting a dialogue. A click
    /// in a gap changes tracks without playing the previously selected cue.
    @discardableResult func selectTimelineVoice(_ engine:String,language:String,at time:Double,play:Bool=true)->Bool {
        selectVoiceTrack(engine,language:language);followPlaybackText=false
        let regions=timelineAudioRegions[engine+":"+language] ?? []
        guard let region=regions.last(where:{$0.start<=time && time<$0.end}),
              let segment=document?.segments.first(where:{$0.id==region.segmentID || (region.segmentID==nil && abs($0.start-region.start)<0.001 && abs($0.end-region.end)<0.001)}) else {
            if let gap=(timelineMissingRegions[engine+":"+language] ?? []).first(where:{$0.start<=time && time<$0.end}),let segment=document?.segments.first(where:{$0.id==gap.segmentID}) {
                selectSegment(segment.id,reveal:false);auditionLabel=L("缺聲原因：")+gap.reason
            }
            player.pause();seek(time);return false
        }
        selectSegment(segment.id,reveal:false)
        if play,cueVoiceAvailable(engine,language:language) {playCueVoice(engine,language:language);return true}
        seek(time);return false
    }
}
