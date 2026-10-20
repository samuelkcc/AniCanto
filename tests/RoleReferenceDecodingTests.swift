import Foundation

@main struct RoleReferenceDecodingTests {
    static func main() throws {
        let data=Data("""
        [{"id":"role-1","name":"主角","reference":"original.wav","promptText":"こんにちは","language":"ja","avatar":"head.jpg","sourceFrame":"frame.jpg","avatarTime":12.5,"portraits":[{"avatar":"head.jpg","sourceFrame":"frame.jpg","time":12.5}],"referenceQuality":{"score":82,"warnings":[]},"referenceCandidates":[{"reference":"alternate.wav","promptText":"行くぞ","language":"ja","range":[10,14]}],"engineReferences":{"gpt-sovits:yue":{"reference":"custom.wav","promptText":"你好","enabled":true}}},
         {"id":"role-2","name":"旁白","reference":"second.wav","promptText":"次回","language":"ja","referenceCandidates":[]}]
        """.utf8)
        let roles=try JSONDecoder().decode([VoiceProfile].self,from:data)
        precondition(roles.count==2 && roles[0].avatar=="head.jpg")
        precondition(roles[0].portraits?.first?.sourceFrame=="frame.jpg" && roles[0].referenceQuality?.score==82)
        let alternative=roles[0].referenceCandidates![0]
        precondition(!alternative.enabled && alternative.language=="ja" && alternative.range==[10,14])
        precondition(roles[0].engineReferences!["gpt-sovits:yue"]!.enabled)
        let restored=try JSONDecoder().decode([VoiceProfile].self,from:JSONEncoder().encode(roles))
        precondition(restored==roles)
        print("PASS: automatic reference candidates preserve the role list and avatars; explicit enabled settings and metadata survive round trip.")
    }
}
