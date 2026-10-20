import Foundation

@main struct CueVoiceReviewPolicyTests {
    static func main() {
        let raw: [String: Any] = ["heard": "", "languageMismatch": true, "criticalDifferences": ["negation"]]
        precondition(CueVoiceReviewPolicy.blocked(raw, language: "yue", rejected: false))
        for decision in ["accept", "retain-with-note"] {
            var reviewed = raw
            reviewed.merge(["cantoneseReviewPolicy": "yue-advisory-two-witnesses-2", "contentDecision": decision, "confirmedContentFailure": false]) { _, new in new }
            precondition(!CueVoiceReviewPolicy.blocked(reviewed, language: "yue", rejected: false))
            precondition(CueVoiceReviewPolicy.blocked(reviewed, language: "yue", rejected: true))
            precondition(CueVoiceReviewPolicy.blocked(reviewed, language: "en", rejected: false))
            reviewed["confirmedContentFailure"] = true
            precondition(CueVoiceReviewPolicy.blocked(reviewed, language: "yue", rejected: false))
        }
        let confirmed: [String: Any] = ["heard": "speech", "confirmedContentFailure": true, "contentDecision": "repair"]
        precondition(CueVoiceReviewPolicy.blocked(confirmed, language: "yue", rejected: false))
        precondition(!CueVoiceReviewPolicy.blocked(["heard": "正常對白"], language: "yue", rejected: false))
        print("PASS audition adoption: advisory Cantonese, physical rejection, confirmed failure and English")
    }
}
