import Foundation

/// Recover worker-completed scripts into an older editor snapshot. A global
/// dirty bit can describe an unrelated volume/playhead edit, so ownership is
/// checked for each segment against its original baseline instead.
enum EditorScriptSync {
    static func merge(_ document:inout EditDocument,base:[[String:Any]],current:[[String:Any]])->Int {
        var count=0
        for i in document.segments.indices {
            let s=document.segments[i]
            guard s.manual != true,s.sources.count==1,let n=s.sources.first,
                  base.indices.contains(n),current.indices.contains(n) else{continue}
            let old=base[n],new=current[n]
            func owns(_ c:[String:Any])->Bool {
                abs((c["start"] as? Double ?? -1)-s.start)<0.001 && abs((c["end"] as? Double ?? -1)-s.end)<0.001 &&
                    c["speakerId"] as? String==s.speakerId && (c["japanese"] as? String ?? c["text"] as? String ?? "")==s.original
            }
            let untouched=s.scriptSyncSource.map {$0==s.text} ?? (s.text==(old["cantonese"] as? String ?? ""))
            guard owns(old),owns(new),untouched,
                  let text=new["cantonese"] as? String,text != s.text,!text.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty else{continue}
            document.segments[i].text=text
            document.segments[i].scriptSyncSource=text
            document.segments[i].audioTake=nil
            if s.sourceNote==old["reviewNote"] as? String {document.segments[i].sourceNote=new["reviewNote"] as? String}
            count += 1
        }
        return count
    }
}
