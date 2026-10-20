import AppKit
import AVFoundation

@main struct VLCPreviewTests {
    @MainActor static func main() throws {
        runManagedToolIfNeeded()
        guard CommandLine.arguments.count == 4 else { print("Usage: video seconds snapshot.png"); return }
        let app = NSApplication.shared
        app.setActivationPolicy(.accessory)
        let engine = Engine()
        let url = URL(fileURLWithPath: CommandLine.arguments[1])
        let info = try engine.inspectVideo(url)
        let target = Double(CommandLine.arguments[2])!
        let player = CantoPlayer()
        let view = VLCVideoView(frame: NSRect(x: 0, y: 0, width: 960, height: 540)); view.player = player
        let window = NSWindow(contentRect: view.frame, styleMask: [.titled, .closable], backing: .buffered, defer: false)
        window.title = "AniCanto 獨立播放器驗證"; window.contentView = view; window.makeKeyAndOrderFront(nil)
        player.replaceCurrentItem(with: AVPlayerItem(url: url))
        if let track = info.tracks.first(where: { $0.supported }) {
            let ass = try engine.vlcSubtitle(source: url, stream: track.id)
            player.subtitles(ordinal: nil, external: ass)
        }
        player.seek(to: CMTime(seconds: target, preferredTimescale: 1000)); player.play()
        var failures: [String] = []
        Timer.scheduledTimer(withTimeInterval: 4, repeats: false) { _ in
            if player.currentTime().seconds < target || player.duration <= target { failures.append("playback clock/duration") }
            player.pause(); player.seek(to: CMTime(seconds: target, preferredTimescale: 1000))
        }
        Timer.scheduledTimer(withTimeInterval: 7, repeats: false) { _ in
            if abs(player.currentTime().seconds - target) > 0.5 { failures.append("paused seek") }
            if let error = player.failure { failures.append(error) }
            if let api = VLCAPI.shared, let pointer = player.pointer {
                let snap = api.fn("libvlc_video_take_snapshot", (@convention(c) (OpaquePointer, UInt32, UnsafePointer<CChar>, UInt32, UInt32) -> Int32).self)(pointer, 0, CommandLine.arguments[3], 960, 540)
                if snap != 0 { failures.append("snapshot") }
            } else { failures.append("VLC unavailable") }
            player.replaceCurrentItem(with: nil)
            print(failures.isEmpty ? "PASS native VLC play/pause/seek/stop and decoded subtitle snapshot" : "FAIL \(failures)")
            fflush(stdout); app.terminate(nil)
        }
        app.run()
    }
}
