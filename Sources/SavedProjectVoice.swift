import Foundation

extension AppModel {
    /// References may be shared with projects. Remove library entries only;
    /// retain media and a reversible metadata backup rather than breaking them.
    func removeLibraryVoices(_ ids:Set<String>) throws {
        guard !busy else{return}
        let next=voiceProfiles.filter {!ids.contains($0.id)}
        guard next.count != voiceProfiles.count else{return}
        let backups=engine.root.appendingPathComponent("voice-library-backups")
        try FileManager.default.createDirectory(at:backups,withIntermediateDirectories:true)
        try JSONEncoder().encode(voiceProfiles).write(to:backups.appendingPathComponent(UUID().uuidString+".json"),options:.atomic)
        try JSONEncoder().encode(next).write(to:engine.root.appendingPathComponent("voice-profiles.json"),options:.atomic)
        voiceProfiles=next
    }
    // Project references become global only through this explicit save action.
    // Copy their media now so deleting the project cannot invalidate a favorite.
    func saveProjectVoice(_ profile:VoiceProfile) throws {
        let directory=engine.root.appendingPathComponent("saved-role-recordings").appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at:directory,withIntermediateDirectories:true)
        var copies:[String:String]=[:]
        func copyMedia(_ object:Any,key:String="") throws -> Any {
            if let map=object as? [String:Any] {return try map.mapValuesWithKeys {try copyMedia($0.value,key:$0.key)}}
            if let array=object as? [Any] {return try array.map {try copyMedia($0,key:key)}}
            if ["reference","avatar","sourceFrame"].contains(key),let path=object as? String,path.hasPrefix("/"),FileManager.default.fileExists(atPath:path) {
                if let saved=copies[path] {return saved}
                let source=URL(fileURLWithPath:path),destination=directory.appendingPathComponent(UUID().uuidString+"."+source.pathExtension)
                try FileManager.default.copyItem(at:source,to:destination);copies[path]=destination.path;return destination.path
            }
            return object
        }
        do {
            let original=try JSONSerialization.jsonObject(with:JSONEncoder().encode(profile))
            let saved=try JSONDecoder().decode(VoiceProfile.self,from:JSONSerialization.data(withJSONObject:copyMedia(original)))
            if let index=voiceProfiles.firstIndex(where:{$0.id==saved.id}) {voiceProfiles[index]=saved} else {voiceProfiles.append(saved)}
        } catch {try? FileManager.default.removeItem(at:directory);throw error}
    }
}

private extension Dictionary where Key==String,Value==Any {
    func mapValuesWithKeys(_ transform:((key:String,value:Any)) throws -> Any) rethrows -> [String:Any] {
        var result:[String:Any]=[:]
        for item in self {result[item.key]=try transform(item)}
        return result
    }
}
