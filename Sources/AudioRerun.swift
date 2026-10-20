import SwiftUI
import AVKit
import CryptoKit

extension ProjectEditor {
    func playReference(_ profile:VoiceProfile,engine:String) {
        let path:String
        if voiceStyleMode=="natural" {
            guard let reference=naturalReference(profile,engine:engine,language:previewLanguage) else {error=L("自動自然聲線未配對；先生成試音，或選擇一條自然聲線試聽。");return}
            path=reference
        } else {path=profile.referenceFor(engine,previewLanguage)}
        player.pause();audio.pause();audio.replaceCurrentItem(with:AVPlayerItem(url:URL(fileURLWithPath:path)));audio.play()
        auditionLabel=L(voiceStyleMode=="natural" ? "自然聲線參考":"角色原聲參考")
    }
    func useOriginalReference(segment:EditSegment,profileID:String,ffmpeg:URL) {
        guard !readOnlyPreview,segment.speakerId==profileID,let source=dialoguePath,let document,let i=profiles.firstIndex(where:{$0.id==profileID}),3...10 ~= segment.end-segment.start,!segment.original.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty else{return}
        let capturedReview=document.review
        let capturedProfile=profiles[i]
        let folder=URL(fileURLWithPath:document.review).deletingLastPathComponent().appendingPathComponent("manual-original-references")
        Task {
            do {
                try FileManager.default.createDirectory(at:folder,withIntermediateDirectories:true)
                let temp=folder.appendingPathComponent(UUID().uuidString+".wav")
                defer {try? FileManager.default.removeItem(at:temp)}
                try await Task.detached(priority:.utility) {
                    let p=Process();p.executableURL=ffmpeg;p.arguments=["-v","error","-y","-ss",String(segment.start),"-i",source,"-t",String(segment.end-segment.start),"-ar","48000","-ac","1","-c:a","pcm_s16le",temp.path];p.standardError=FileHandle.nullDevice;p.standardOutput=FileHandle.nullDevice
                    try p.run();p.waitUntilExit();if p.terminationStatus != 0 {throw AppFailure(message:"未能擷取角色原聲參考。")}
                }.value
                let bytes=try Data(contentsOf:temp),hash=SHA256.hash(data:bytes).map{String(format:"%02x",$0)}.joined()
                let target=folder.appendingPathComponent(hash+".wav")
                if !FileManager.default.fileExists(atPath:target.path) {try bytes.write(to:target,options:.atomic)}
                guard self.document?.review==capturedReview,let index=profiles.firstIndex(where:{$0.id==profileID}),profiles[index]==capturedProfile else{throw AppFailure(message:"角色已修改；新參考已保存，請重新選擇。")}
                var p=capturedProfile
                let previous=EngineVoiceReference(reference:p.reference,promptText:p.promptText,language:p.language)
                p.referenceCandidates=[previous]+(p.referenceCandidates ?? []).filter{$0.reference != previous.reference}
                p.reference=target.path;p.promptText=segment.original;p.language="ja";p.referenceRanges=[[segment.start,segment.end]];p.referenceQuality=nil;p.shortReference=false;p.mixedReference=false;p.transcriptSource="original-japanese-words";p.originalReference=nil
                if p.engineReferences==nil {p.engineReferences=[:]}
                p.engineReferences?[previewEngine+":"+previewLanguage]=EngineVoiceReference(reference:target.path,promptText:segment.original,enabled:true,language:"ja",range:[segment.start,segment.end])
                profiles[index]=p;dirty=true;invalidateTakes();try save();playReference(p,engine:previewEngine)
                auditionLabel=L("已選角色分離原聲；請覆聽音效殘留及逐字原文，純度未認證。")
            } catch {self.error=error.localizedDescription}
        }
    }
}
