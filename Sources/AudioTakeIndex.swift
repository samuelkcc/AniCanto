import Foundation
import CryptoKit

/// Recover exact native records from older workers that overwrote their preview
/// manifest. No synthesis, no filesystem mutation, and no speaker guess by image.
@MainActor enum AudioTakeIndex {
    static func recovered(folder:URL,engine:String,cues:[[String:Any]],profiles:[VoiceProfile])->[[String:Any]] {
        guard engine=="gpt-sovits" else{return []}
        let fm=FileManager.default
        let files=(try? fm.contentsOfDirectory(at:folder,includingPropertiesForKeys:nil)) ?? []
        var owners:[String:Set<String>]=[:],conditioned:[String:String]=[:]
        for profile in profiles {
            let references=[profile.reference]+(profile.referenceCandidates ?? []).map(\.reference)+(profile.engineReferences ?? [:]).filter {$0.key.hasPrefix(engine+":") && $0.value.enabled}.map{$0.value.reference}
            for path in references {
                guard let bytes=try? Data(contentsOf:URL(fileURLWithPath:path)) else{continue}
                let digest=SHA256.hash(data:bytes).map{String(format:"%02x",$0)}.joined()
                owners[digest,default:[]].insert(profile.id)
            }
        }
        var result:[[String:Any]]=[]
        for health in files where health.lastPathComponent.hasPrefix(engine+"-") && health.lastPathComponent.hasSuffix(".health.json") {
            guard let data=try? Data(contentsOf:health),let attempts=try? JSONSerialization.jsonObject(with:data) as? [[String:Any]],let first=attempts.first,let last=attempts.last,(last["problems"] as? [String])?.isEmpty==true,let text=first["text"] as? String,let reference=last["reference"] as? String else{continue}
            let audio=health.deletingPathExtension().deletingPathExtension().appendingPathExtension("wav")
            guard fm.fileExists(atPath:audio.path),let length=ProjectEditor.audioLength(audio.path),length>0 else{continue}
            let sourceHash:String
            if let cached=conditioned[reference] {sourceHash=cached}
            else {
                let manifest=URL(fileURLWithPath:reference).deletingLastPathComponent().appendingPathComponent("reference.json")
                guard let bytes=try? Data(contentsOf:manifest),let metadata=try? JSONSerialization.jsonObject(with:bytes) as? [String:Any],let digest=metadata["sourceSHA"] as? String else{continue}
                sourceHash=digest;conditioned[reference]=digest
            }
            guard let ids=owners[sourceHash],ids.count==1,let role=ids.first else{continue}
            let seed=(first["seed"] as? Int) ?? 42
            let matches=cues.filter {$0["speakerId"] as? String==role && $0["cantonese"] as? String==text && ($0["_seed"] as? Int ?? 42)==seed}
            guard matches.count==1 else{continue}
            for cue in matches {
                var row=cue;row["audio"]=audio.path;row["recoveredFromHealth"]=true;row["modelVersion"]=first["modelVersion"] as? String ?? "v2";row["nativeSeconds"]=length;result.append(row)
            }
        }
        return result
    }
}
