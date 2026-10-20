import Foundation

/// Applied when a new request is submitted. Frozen jobs retain their own policy.
enum RoleAnalysisPolicy {
    static func mode(selected:String,visualEnabled:Bool,interfaceMode:String)->String {
        if selected=="independent" {return "independent"}
        return interfaceMode=="professional" && visualEnabled ? "audiovisual":"audio"
    }
}
