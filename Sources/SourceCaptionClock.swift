import Foundation

/// Original subtitles always use source-file time, independently of dub timing.
enum SourceCaptionClock {
    static func absolute(playhead:Double,offset:Double,spans:[[String:Any]]=[],previewStart:Double?=nil)->Double? {
        if let previewStart {return offset+previewStart+playhead}
        if spans.isEmpty {return offset+playhead}
        for span in spans {
            guard let start=span["start"] as? Double,let end=span["end"] as? Double,let output=span["outputStart"] as? Double,playhead>=output,playhead<output+end-start else{continue}
            return span["blank"] as? Bool==true ? nil:offset+start+playhead-output
        }
        return nil
    }
    static func active(_ captions:[PreviewCaption],at time:Double?)->[PreviewCaption] {
        guard let time else{return []}
        return captions.filter{$0.start<=time && time<$0.end}
    }
}
extension ProjectEditor {
    var originalPlaybackTime:Double? {
        guard let playingVersion,let version=versions.first(where:{$0.id==playingVersion}),let report=version.report,let bytes=try? Data(contentsOf:report),let metadata=try? JSONSerialization.jsonObject(with:bytes) as? [String:Any] else{return offset+seconds}
        let preview=metadata["preview"] as? Bool==true ? metadata["sourceStart"] as? Double:nil
        return SourceCaptionClock.absolute(playhead:seconds,offset:offset,spans:metadata["editSpans"] as? [[String:Any]] ?? [],previewStart:preview)
    }
}
