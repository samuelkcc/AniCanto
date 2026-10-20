import Foundation

/// Keep the audition controls consistent with the worker's Cantonese review.
/// A diagnostic transcript is not itself a reason to discard audible speech.
enum CueVoiceReviewPolicy {
    static func blocked(_ check: [String: Any], language: String, rejected: Bool) -> Bool {
        if rejected || check["confirmedContentFailure"] as? Bool == true { return true }
        let reviewed = language == "yue"
            && (check["cantoneseReviewPolicy"] as? String)?.hasPrefix("yue-advisory-") == true
            && ["accept", "retain-with-note"].contains(check["contentDecision"] as? String ?? "")
            && check["confirmedContentFailure"] as? Bool == false
        if reviewed { return false }
        return check["languageMismatch"] as? Bool == true
            || !(check["criticalDifferences"] as? [Any] ?? []).isEmpty
            || (check["heard"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == true
    }
}
