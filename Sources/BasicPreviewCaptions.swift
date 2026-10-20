import Foundation

/// Resolve the frozen engine once, before comparing cues with available takes.
/// A clock tick must not parse the submitted JSON for every pair of recordings.
enum BasicPreviewCaptions {
    private struct Key:Hashable {let language:String,start:Int,end:Int}
    static func rows(cues:[LiveSubtitleCue],takes:[ProcessingVoiceTake],engine:String,languages:[String],offset:Double)->[PreviewCaption] {
        var indexed:[Key:[(Int,ProcessingVoiceTake)]]=[:]
        for (index,take) in takes.enumerated() where take.engine==engine {
            let key=Key(language:take.language,start:Int((take.start*1000).rounded()),end:Int((take.end*1000).rounded()))
            indexed[key,default:[]].append((index,take))
        }
        return languages.flatMap {language in
            cues.compactMap {cue -> PreviewCaption? in
                let start=Int((cue.start*1000).rounded()),end=Int((cue.end*1000).rounded())
                var matching:(Int,ProcessingVoiceTake)?
                // Preserve the established sub-millisecond matching tolerance,
                // including times on opposite sides of a rounding boundary.
                for a in (start-1)...(start+1) {for b in (end-1)...(end+1) {
                    for row in indexed[Key(language:language,start:a,end:b)] ?? [] where abs(row.1.start-cue.start)<0.001 && abs(row.1.end-cue.end)<0.001 {
                        if matching==nil || row.0<matching!.0 {matching=row}
                    }
                }}
                let text=matching?.1.text ?? cue.text(language)
                return text.isEmpty ? nil:PreviewCaption(start:cue.start+offset,end:cue.end+offset,text:text)
            }
        }
    }
}
