import Foundation
import Darwin
import AVFoundation

final class SubtitleObserver: NSObject, AVPlayerItemLegibleOutputPushDelegate, @unchecked Sendable {
    var texts: [String] = []
    func legibleOutput(_ output: AVPlayerItemLegibleOutput, didOutputAttributedStrings strings: [NSAttributedString], nativeSampleBuffers: [Any], forItemTime itemTime: CMTime) {
        for s in strings where !s.string.isEmpty { texts.append(s.string); print("SUBTITLE: \(s.string)") }
    }
}

@main struct PreviewTests {
    static func main() async throws {
        runManagedToolIfNeeded()
        setbuf(stdout, nil)
        let aac: [String:Any] = ["codec_name":"aac", "profile":"LC"]
        let h264: [String:Any] = ["codec_name":"h264", "pix_fmt":"yuv420p"]
        let copy = PreviewEncodingPlan(picture:h264, audio:aac)
        precondition(copy.copyVideo && copy.copyAudio && copy.arguments.contains("copy"))
        precondition(!PreviewEncodingPlan(picture:["codec_name":"h264","pix_fmt":"yuv420p10le"],audio:aac).copyVideo)
        precondition(!PreviewEncodingPlan(picture:h264,audio:["codec_name":"dts"]).copyAudio)
        let hevc = PreviewEncodingPlan(picture:["codec_name":"hevc","pix_fmt":"yuv420p10le"],audio:nil)
        precondition(hevc.copyVideo && hevc.arguments.contains("hvc1"))
        let e = Engine(); e.notify = { event in print("\(event.stage): \(event.message)") }
        let started = Date()
        let info = try e.inspectVideo(URL(fileURLWithPath:CommandLine.arguments[1]))
        let elapsed = Date().timeIntervalSince(started)
        print("PREVIEW: \(info.preview.path)\nSECONDS: \(elapsed)")
        precondition(!info.tracks.isEmpty)
        let asset = AVURLAsset(url:info.preview)
        let playable = try await asset.load(.isPlayable)
        precondition(playable)
        let group = try await asset.loadMediaSelectionGroup(for:.legible)!
        let options = previewSubtitleOptions(group)
        print("GROUP options \(group.options.count), selectable \(options.count), source \(info.tracks.count)")
        precondition(options.count == info.tracks.filter(\.supported).count)
        let item = AVPlayerItem(asset:asset)
        let player = AVPlayer(playerItem:item); player.isMuted = true
        let output = AVPlayerItemLegibleOutput()
        let observer = SubtitleObserver(); output.setDelegate(observer,queue:.main); item.add(output)
        let selected = CommandLine.arguments.count > 2 ? Int(CommandLine.arguments[2])! : 0
        item.select(options[selected],in:group)
        let time = info.tracks[selected].firstCue ?? 0
        let captions = try e.previewCaptions(source:URL(fileURLWithPath:CommandLine.arguments[1]),stream:info.tracks[selected].id)
        precondition(!captions.isEmpty)
        precondition(!PreviewCaption.text(at:time+0.2,in:captions).isEmpty)
        precondition(PreviewCaption.text(at:-1,in:captions).isEmpty)
        let external = try e.previewCaptions(source:e.resources.appendingPathComponent("demo.srt"),stream:nil)
        precondition(!external.isEmpty && PreviewCaption.text(at:1,in:external).contains("你好"))

        let seeked = await player.seek(to:CMTime(seconds:time+0.2,preferredTimescale:600),toleranceBefore:.zero,toleranceAfter:.zero)
        precondition(seeked)
        player.play()
        try await Task.sleep(nanoseconds:3_000_000_000)
        player.pause()
        precondition(item.status == .readyToPlay, "AVPlayer not ready: \(String(describing:item.error))")
        print("STATUS \(item.status.rawValue), TEXTS \(observer.texts), SELECTED \(String(describing:item.currentMediaSelection.selectedMediaOption(in:group)))")
        precondition(!observer.texts.isEmpty,"selected subtitle track produced no display text")
        let result: [String:Any] = ["preview":info.preview.path,"seconds":elapsed,"firstSubtitle":time,"subtitleTracks":options.count,"subtitleText":observer.texts,"playerReady":true]
        let dest = e.root.appendingPathComponent("preview-test.json")
        try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:dest)
        let cached = try e.inspectVideo(URL(fileURLWithPath:CommandLine.arguments[1]))
        precondition(cached.preview == info.preview)
        print("PASS: native playback, selected subtitle output, source timings and cached preview")
    }
}
