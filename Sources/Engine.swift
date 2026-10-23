import Foundation
import CryptoKit
import AVFoundation
import Darwin

// Launch every App-owned tool in its own process group so shutdown also reaches
// model runners and other descendants, not just the immediate worker.
func runManagedToolIfNeeded() {
    guard CommandLine.arguments.count >= 3, CommandLine.arguments[1] == "--managed-tool" else { return }
    guard setpgid(0, 0) == 0 || getpgrp() == getpid() else { exit(126) }
    let args = Array(CommandLine.arguments.dropFirst(2))
    var argv = args.map { strdup($0) } + [nil]
    argv.withUnsafeMutableBufferPointer { buffer in
        _ = execv(args[0], buffer.baseAddress!)
    }
    perror("啟動工作程序失敗")
    exit(127)
}

struct AppFailure: LocalizedError { let message: String; var errorDescription: String? { message } }
struct WorkerEvent: Decodable {
    var stage: String
    var message: String
    var workID: String?
    var workCompleted: Double?
    var workTotal: Double?
    var workCached: Bool?
    var progress: Double?
    var journey: ProductionJourney?
    var productionPending:Bool?
    var output: String?
    var deliveryKind:String?
    var artifactRole:String?
    var previewOutput:String?
    var missingDialogue:Int?
    var incompleteDialogue:Int?
    var trackOutput:String?
    var primaryVoiceFraction:Double?
    var partial: Bool?
    var autoRepair: Bool?
    var review: String?
    var job: String?
    var audioTrack: AudioTrackProgress?
    var ocrOriginal: String?
    var ocrPreview: String?
    var ocrText: String?
    var background: String?
    var dialogue: String?
    var reference: String?
    var promptText: String?
    var profileId: String?
    var voicePreview: String?
    var comparisonGSV: String?
    var comparisonCosy: String?
    var rewriteIndex: Int?
    var rewriteText: String?
    var cueIndex:Int?
    var batchId: String?
    var batchStatus: String?
    var opStart: Double?
    var download: DownloadTransfer?
    var componentProgress:ComponentProgress?
}
struct ComponentProgress:Decodable {let label:String;var fraction:Double?;var phase:String?}
struct DownloadTransfer:Codable {
    var file:String
    var bytesReceived:Double
    var totalBytes:Double?
    var bytesPerSecond:Double
    var etaSeconds:Double?
    var attempt:Int
    var state:String
    var stateTitle:String {
        if state=="reused" {return L("已安裝 · 沿用")}
        return L(["connecting":"連接下載伺服器","transferring":"下載中","waiting":"等候資料","retrying":"連線中斷，自動續傳","verifying":"校驗模型","complete":"下載完成","failed":"下載未完成"][state] ?? "下載中")
    }
    var sizeText:String {
        let received=ByteCountFormatter.string(fromByteCount:Int64(max(0,bytesReceived)),countStyle:.file)
        guard let totalBytes else {return received}
        return received+" / "+ByteCountFormatter.string(fromByteCount:Int64(max(0,totalBytes)),countStyle:.file)
    }
    var speedText:String {
        guard bytesPerSecond>0,state=="transferring" else {return "—"}
        return String(format:bytesPerSecond>=1_000_000 ? "%.1f MB/s":"%.0f KB/s",bytesPerSecond/(bytesPerSecond>=1_000_000 ? 1_000_000:1_000))
    }
    var remainingText:String {
        guard let etaSeconds,etaSeconds.isFinite,bytesPerSecond>0,state=="transferring" else {return L("估算中")}
        let seconds=Int(min(etaSeconds,31_536_000))
        return String(format:"%02d:%02d:%02d",seconds/3600,(seconds/60)%60,seconds%60)
    }
}
struct SubtitleTrack: Identifiable, Hashable, Sendable {
    let id: Int
    let language: String
    let title: String
    let codec: String
    var firstCue: Double? = nil
    var supported: Bool { ["subrip", "ass", "ssa", "mov_text", "webvtt", "text"].contains(codec) }
    var label: String { L("軌")+" \(id) · \(language) · \(title.isEmpty ? codec.uppercased() : title + " / " + codec.uppercased())" + (supported ? "" : L("（圖片字幕暫未支援）")) }
}
struct PreviewCaption: Sendable, Equatable {
    let start: Double
    let end: Double
    let text: String
    static func parse(_ srt: String) -> [PreviewCaption] {
        let pattern = #"(\d+:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d+:\d{2}:\d{2}[,.]\d{3})[^\n]*\n(.*?)(?=\n\s*\n|\z)"#
        let text = srt.replacingOccurrences(of: "\r", with: "")
        guard let regex = try? NSRegularExpression(pattern: pattern, options: [.dotMatchesLineSeparators]) else { return [] }
        func seconds(_ value: String) -> Double {
            let p = value.components(separatedBy: CharacterSet(charactersIn: ":,.")) .compactMap(Double.init)
            return p.count == 4 ? p[0]*3600+p[1]*60+p[2]+p[3]/1000 : -1
        }
        return regex.matches(in: text, range: NSRange(text.startIndex..., in: text)).compactMap { match in
            guard let a = Range(match.range(at: 1), in: text), let b = Range(match.range(at: 2), in: text), let c = Range(match.range(at: 3), in: text) else { return nil }
            let start = seconds(String(text[a])), end = seconds(String(text[b]))
            let body = String(text[c]).replacingOccurrences(of: #"<[^>]*>|\{[^}]*\}"#, with: "", options: .regularExpression).trimmingCharacters(in: .whitespacesAndNewlines)
            return end > start && !body.isEmpty ? PreviewCaption(start: start, end: end, text: body) : nil
        }
    }
    static func text(at time: Double, in cues: [PreviewCaption]) -> String {
        cues.filter { $0.start <= time && time < $0.end }.map(\.text).joined(separator: "\n")
    }
}

// AVFoundation exposes an extra forced-only option for each ordinary text
// track. Those virtual options are not additional source subtitle tracks.
func previewSubtitleOptions(_ group: AVMediaSelectionGroup) -> [AVMediaSelectionOption] {
    let full = group.options.filter { !$0.hasMediaCharacteristic(.containsOnlyForcedSubtitles) }
    return full.isEmpty ? group.options : full
}

// AVPlayer cannot decode every H.264 profile just because the codec name matches.
struct PreviewEncodingPlan {
    let copyVideo: Bool
    let copyAudio: Bool
    let hevc: Bool
    init(picture: [String:Any], audio: [String:Any]?) {
        let codec = picture["codec_name"] as? String ?? ""
        let pixels = picture["pix_fmt"] as? String ?? ""
        hevc = codec == "hevc"
        copyVideo = (codec == "h264" && pixels == "yuv420p") || (hevc && ["yuv420p", "yuv420p10le"].contains(pixels))
        copyAudio = audio == nil || (audio?["codec_name"] as? String == "aac" && audio?["profile"] as? String == "LC")
    }
    var arguments: [String] {
        var args = copyVideo ? ["-c:v", "copy"] : ["-c:v", "libx264", "-preset", "veryfast", "-crf", "25", "-pix_fmt", "yuv420p"]
        if copyVideo && hevc { args += ["-tag:v", "hvc1"] }
        args += copyAudio ? ["-c:a", "copy"] : ["-c:a", "aac", "-b:a", "128k", "-ac", "2"]
        return args
    }
}
struct MediaInfo: Sendable { let tracks: [SubtitleTrack]; let preview: URL; let duration: Double; let aspectRatio: Double; var burnedCaptions: Bool = false }

final class Engine: @unchecked Sendable {
    let root: URL
    let resources: URL
    let port: Int
    let modelSelectionLock=NSLock()
    private let lock = NSLock()
    private let devLogLock = NSLock()
    // Bounded diagnostic output, independent of the UI's shortened progress messages.
    private func devLog(_ data: Data) {
        devLogLock.lock(); defer { devLogLock.unlock() }
        let url=root.appendingPathComponent("developer-process.log")
        do {
            if let size=(try? FileManager.default.attributesOfItem(atPath:url.path)[.size]) as? NSNumber, size.intValue > 5_000_000 {
                let previous=root.appendingPathComponent("developer-process.previous.log")
                try? FileManager.default.removeItem(at:previous)
                try FileManager.default.moveItem(at:url,to:previous)
            }
            if !FileManager.default.fileExists(atPath:url.path) { FileManager.default.createFile(atPath:url.path,contents:nil) }
            let file=try FileHandle(forWritingTo:url);defer {try? file.close()}
            try file.seekToEnd();try file.write(contentsOf:data)
        } catch { /* Diagnostic storage must never stop a conversion. */ }
    }
    private func devEvent(_ text:String) {
        devLog(Data(("\n["+ISO8601DateFormatter().string(from:Date())+"] "+text+"\n").utf8))
    }
    private let startupLock = NSLock()
    private var active: Process?
    private var server: Process?
    private var mlxServer: Process?
    private var mlxPort: Int?
    private var cancelled = false
    private var shuttingDown = false
    private var usedModels: Set<String> = []
    var notify: (@Sendable (WorkerEvent) -> Void)?
    func runtimePython(_ name: String) -> URL {
        let bundled = resources.appendingPathComponent("runtimes/\(name)/bin/python3")
        return FileManager.default.isExecutableFile(atPath: bundled.path) ? bundled : root.appendingPathComponent("\(name)/bin/python3")
    }
    var python: URL { runtimePython("runtime") }
    func readyMarkerValue(_ file:String,_ key:String,_ expected:String)->Bool {
        guard let data=try? Data(contentsOf:root.appendingPathComponent(file)),
              let value=try? JSONSerialization.jsonObject(with:data) as? [String:Any] else{return false}
        return value[key] as? String==expected
    }
    func readyVariantMarker(_ file:String,_ variant:String)->Bool {readyMarkerValue(file,"variant",variant)}
    var asrReady: Bool {
        let variant=selectedVariant("asr",default:"asr-1.7b-bf16")
        return runtimeVerified("asr-runtime") && ModelOption.all.first(where:{$0.id==variant})?.ready(root)==true && readyVariantMarker("asr-ready.json",variant)
    }
    var ollama: URL { let bundled = resources.appendingPathComponent("ollama/bin/ollama"); return FileManager.default.isExecutableFile(atPath: bundled.path) ? bundled : root.appendingPathComponent("ollama/bin/ollama") }
    var ffmpeg: URL { resources.appendingPathComponent("bin/ffmpeg") }
    var ffprobe: URL { resources.appendingPathComponent("bin/ffprobe") }
    var runtimeReady: Bool { runtimeVerified("runtime") }
    func gsvVersionReady(_ version:String)->Bool {
        let revision="48b1a0169a28582a8984402f82cf438d3bfa6aca"
        let files:[String:Int64]
        switch version {
        case "v2ProPlus":files=["s1v3.ckpt":155284856,"v2Pro/s2Gv2ProPlus.pth":200125741,"sv/pretrained_eres2netv2w24s4ep4.ckpt":107528697]
        case "v2":files=["gsv-v2final-pretrained/s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt":155315150,"gsv-v2final-pretrained/s2G2333k.pth":106035259]
        case "v3":files=["s1v3.ckpt":155284856,"s2Gv3.pth":769035145,"models--nvidia--bigvgan_v2_24khz_100band_256x/config.json":1402,"models--nvidia--bigvgan_v2_24khz_100band_256x/bigvgan_generator.pt":450088331]
        default:files=["s1v3.ckpt":155284856,"gsv-v4-pretrained/s2Gv4.pth":769025545,"gsv-v4-pretrained/vocoder.pth":57781109]
        }
        guard runtimeVerified("gsv-runtime"),FileManager.default.fileExists(atPath:root.appendingPathComponent("gsv-ready.json").path) else{return false}
        return [root,resources].contains {base in files.allSatisfy {name,size in
            let file=base.appendingPathComponent("gpt-sovits/\(revision)/GPT_SoVITS/pretrained_models/\(name)")
            return ((try? FileManager.default.attributesOfItem(atPath:file.path)[.size]) as? NSNumber)?.int64Value==size
        }}
    }
    var gsvReady: Bool {gsvVersionReady("v4")}
    var cosyReady: Bool {
        guard runtimeVerified("cosy-runtime"),let data=try? Data(contentsOf:root.appendingPathComponent("cosy-ready.json")),
              let receipt=try? JSONSerialization.jsonObject(with:data) as? [String:Any] else{return false}
        return receipt["variant"] as? String=="cosy-native-0.5b" && receipt["adapter"] as? String=="official-pytorch-cpu-1"
    }
    private func storedFile(_ path:String,size:Int64)->Bool {((try? FileManager.default.attributesOfItem(atPath:root.appendingPathComponent(path).path)[.size]) as? NSNumber)?.int64Value==size}
    var separatorReady: Bool { FileManager.default.fileExists(atPath: root.appendingPathComponent("separator-ready.json").path) && storedFile("models/separator/MelBandRoformer.ckpt",size:913106900) && runtimeVerified("separator-runtime") }
    var speechReady: Bool {
        let variant=selectedVariant("speech",default:"whisper-large-v3")
        return runtimeReady && ModelOption.all.first(where:{$0.id==variant})?.ready(root)==true && readyVariantMarker("speech-ready.json",variant)
    }
    var speakersReady: Bool { FileManager.default.fileExists(atPath: root.appendingPathComponent("speakers-ready.json").path) && storedFile("models/speakers/voxceleb_resnet34_LM.onnx",size:26530309) }
    var ollamaReady: Bool { FileManager.default.isExecutableFile(atPath: ollama.path) }
    var whisperReady: Bool {
        ModelOption.all.first(where:{$0.id==selectedVariant("referenceSpeech",default:"whisper-small")})?.ready(root)==true
    }
    init(port: Int = 11439) {
        self.port = port
        resources = Bundle.main.resourceURL!
        if let override = ProcessInfo.processInfo.environment["SAM_CANTO_DATA"] {
            root = URL(fileURLWithPath: override)
        } else {
            root = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("SamCantoSync")
        }
        try? FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
    }
    func resetCancellation() { lock.lock(); if !shuttingDown { cancelled = false }; lock.unlock() }
    func checkCancellation() throws {
        lock.lock(); let stopped = cancelled; lock.unlock()
        if stopped { throw AppFailure(message: "已取消。完成嘅字幕同配音已保留，再按開始可以續做。") }
    }
    func cancel() {
        lock.lock(); cancelled = true; let p = active; lock.unlock()
        if let p { stopManagedProcess(p) }
        if let p=mlxServer { stopManagedProcess(p) };mlxServer=nil;mlxPort=nil
    }
    func releaseTextModels() {
        if let p=mlxServer {stopManagedProcess(p)};mlxServer=nil;mlxPort=nil
    }
    func shutdown() {
        lock.lock()
        if shuttingDown { lock.unlock(); return }
        shuttingDown = true
        let models = usedModels
        lock.unlock()
        cancel()
        if let p = mlxServer { stopManagedProcess(p) }; mlxServer=nil; mlxPort=nil
        lock.lock(); let p = server; lock.unlock()
        if let p { stopManagedProcess(p) }
        else {
            // A reused service belongs to another owner. Unload only models
            // requested by this App rather than terminating that service.
            for model in models where !model.hasPrefix("mlx:") {
                _ = try? request("/api/generate", timeout: 2, body: ["model":model,"keep_alive":0])
            }
        }
    }
    private func stopManagedProcess(_ p: Process) {
        let pid = p.processIdentifier
        guard pid > 0 else { return }
        let grouped = getpgid(pid) == pid
        let target = grouped ? -pid : pid
        guard grouped || p.isRunning else { return }
        kill(target, SIGTERM)
        let deadline = Date().addingTimeInterval(1.5)
        while kill(target, 0) == 0 && Date() < deadline { Thread.sleep(forTimeInterval: 0.05) }
        if kill(target, 0) == 0 { kill(target, SIGKILL) }
    }
    private func managedProcess(_ executable: URL, _ args: [String]) -> Process {
        let p = Process()
        // The shared desktop keeps this adapter beside its Tauri executable.
        // Bundle.main.executableURL names the UI there, not this running helper.
        let invoked=CommandLine.arguments[0]
        p.executableURL = invoked.hasPrefix("/") ? URL(fileURLWithPath:invoked):Bundle.main.executableURL!
        p.arguments = ["--managed-tool", executable.path] + args
        p.currentDirectoryURL = root
        p.environment = environment()
        return p
    }
    func event(_ stage: String, _ message: String, _ progress: Double? = nil) {
        notify?(WorkerEvent(stage: stage, message: message, progress: progress))
    }
    func environment() -> [String: String] {
        var env = ProcessInfo.processInfo.environment
        env["CANTOSYNC_UI_LANGUAGE"] = UserDefaults.standard.string(forKey:"studioLanguage") ?? Locale.current.identifier
        if let port=mlxPort { env["CANTOSYNC_MLX_PORT"]=String(port) }
        env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
        for key in Array(env.keys) where key.hasPrefix("UV_") || key.hasPrefix("PIP_") {env.removeValue(forKey:key)}
        env["PIP_CACHE_DIR"] = root.appendingPathComponent("cache/pip").path
        env["HF_HOME"] = root.appendingPathComponent("cache/huggingface").path
        // Numba's compiled kernels are separate from Python bytecode. Keep them
        // out of the sealed app bundle even when PYTHONDONTWRITEBYTECODE is set.
        env["NUMBA_CACHE_DIR"] = root.appendingPathComponent("cache/numba").path
        env["HF_HUB_DISABLE_TELEMETRY"] = "1"
        env["ORT_DISABLE_TELEMETRY"] = "1"
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONNOUSERSITE"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["OLLAMA_HOST"] = "127.0.0.1:\(port)"
        env["OLLAMA_MODELS"] = root.appendingPathComponent("models/ollama").path
        env["OLLAMA_NO_CLOUD"] = "1"
        env["OLLAMA_KEEP_ALIVE"] = "5m"
        env["OLLAMA_CONTEXT_LENGTH"] = "8192"
        return env
    }
    @discardableResult
    func run(_ executable: URL, _ args: [String], protocolOutput: Bool = false, mediaDuration: Double? = nil) throws -> String {
        try checkCancellation()
        let p = managedProcess(executable, args)
        let pipe = Pipe()
        p.standardOutput = pipe
        p.standardError = pipe
        lock.lock()
        if cancelled || shuttingDown { lock.unlock(); throw AppFailure(message: "工作已取消。") }
        do { try p.run(); active = p; lock.unlock() }
        catch { lock.unlock(); throw error }
        defer { lock.lock(); if active === p { active = nil }; lock.unlock() }
        devEvent("START PID=\(p.processIdentifier) TOOL=\(executable.lastPathComponent)")
        var pending = Data()
        var captured = Data()
        var workerFailure: String?
        func consume(_ line: Data) {
            if let duration = mediaDuration, duration > 0, let text = String(data: line, encoding: .utf8) {
                if text.hasPrefix("out_time_us="), let micros = Double(text.dropFirst(12)), micros >= 0 {
                    let fraction = min(0.98, max(0, micros / 1_000_000 / duration))
                    event("預覽", "準備播放檔 \(Int(fraction * 100))% · \(Int(min(duration, micros / 1_000_000))) / \(Int(duration)) 秒", fraction)
                } else if text == "progress=end" { event("預覽", "完成播放檔封裝，正在開啟播放器。", 0.99) }
                if text.contains("=") { return }
            }
            if protocolOutput, let parsed = try? JSONDecoder().decode(WorkerEvent.self, from: line) {
                if parsed.stage == "錯誤" { workerFailure = parsed.message }
                notify?(parsed)
            } else if protocolOutput, let text = String(data: line, encoding: .utf8), !text.isEmpty {
                event("工具", String(text.suffix(800)))
            }
        }
        while true {
            let chunk = pipe.fileHandleForReading.availableData
            if chunk.isEmpty { break }
            devLog(chunk)
            captured.append(chunk)
            if captured.count > 1_000_000 { captured = captured.suffix(500_000) }
            pending.append(chunk)
            while let end = pending.firstIndex(of: 10) {
                let line = Data(pending[..<end])
                pending.removeSubrange(...end)
                consume(line)
            }
        }
        if !pending.isEmpty { consume(pending) }
        p.waitUntilExit()
        devEvent("EXIT PID=\(p.processIdentifier) CODE=\(p.terminationStatus)")
        try checkCancellation()
        let result = String(data: captured, encoding: .utf8) ?? ""
        if p.terminationStatus != 0 {
            let fallback = protocolOutput ? "工作程序意外停止（代碼 \(p.terminationStatus)）。已完成進度已保留，請重新開始續做。" : String(result.suffix(2200))
            throw AppFailure(message: workerFailure ?? (fallback.isEmpty ? "工具啟動失敗：\(executable.lastPathComponent)" : fallback))
        }
        return result
    }
    func installRuntime() throws {
        if runtimeReady { return }
        if lightweightPackage {try ensureMacRuntime("runtime");event("完成","本機執行環境已準備好。",1);return}
        event("設定", "部署 App 專用 Python 3.11；毋須安裝系統 Python。")
        try ensurePythonEnvironment("runtime")
        try run(python, ["-c", "import ssl, json, wave; print('本機執行環境檢查通過')"])
        event("完成", "本機執行環境已準備好。", 1)
    }
    func installSTT() throws {
        if !runtimeReady { try installRuntime() }
        event("設定", "安裝語音辨識元件；只寫入 App 專用環境。")
        if !python.path.hasPrefix(resources.path) { try installPythonPackages(python,["install","faster-whisper==1.2.1"]) }
        try worker("download-stt", config: ["storage": root.path])
        try run(python, ["-c", "from faster_whisper import WhisperModel; print('語音辨識元件檢查通過')"])
        try "1.2.1".write(to: root.appendingPathComponent("stt-ready"), atomically: true, encoding: .utf8)
    }
    func installDubbing(_ kind: String, variant: String? = nil) throws {
        if !runtimeReady { try installRuntime() }
        if lightweightPackage,let runtime=["separator":"separator-runtime","speakers":"separator-runtime","asr":"asr-runtime","gsv":"gsv-runtime","cosy":"cosy-runtime","qwen":"qwen-runtime","drama3":"text-runtime","voxcpm2":"local-tts-runtime","wsyue":"local-tts-runtime"][kind] {try ensureMacRuntime(runtime)}
        if kind == "separator" && !python.path.hasPrefix(resources.path) { try installPythonPackages(python,["install","faster-whisper==1.2.1"]) }
        try run(python, [resources.appendingPathComponent("dubbing_setup.py").path, root.path, kind] + (variant.map {[$0]} ?? []), protocolOutput: true)
        event("完成", kind == "drama3" ? "Drama 3 已部署，可以離線試音。" : kind == "voxcpm2" ? "VoxCPM2 已部署，可以離線試聽。" : kind == "wsyue" ? "WenetSpeech-Yue 已部署，可以離線試聽廣東話。" : kind == "qwen" ? "Qwen3-TTS 模型已部署，請先試聽廣東話。" : kind == "cosy" ? "CosyVoice 3 已部署，可以離線試聽。" : kind == "gsv" ? "GPT-SoVITS 已部署，請到角色頁設定參考聲音。" : "背景分離模型已部署，可以試聽背景軌。", 1)
    }
    func ensureSpeechTiming(qualityChecks:Bool=true) throws {
        if !runtimeReady { try installRuntime() }
        if !whisperReady { try installSTT() }
        if !speechReady { try worker("download-speech", config: ["storage":root.path]) }
        if qualityChecks && !asrReady { try installDubbing("asr") }
    }
    func ensureAutoSpeakers(independent:Bool=false) throws {
        if !separatorReady { try installDubbing("separator") }
        if !independent && !speakersReady { try installDubbing("speakers") }
        if !whisperReady { try installSTT() }
    }
    func sha256(_ url: URL) throws -> String {
        let f = try FileHandle(forReadingFrom: url)
        defer { try? f.close() }
        var hash = SHA256()
        while let data = try f.read(upToCount: 4_194_304), !data.isEmpty { hash.update(data: data) }
        return hash.finalize().map { String(format: "%02x", $0) }.joined()
    }
    func installOllama() throws {
        if ollamaReady { return }
        event("下載", "下載官方 Ollama v0.35.1 本機引擎；完成後驗證 SHA-256。")
        let archive = root.appendingPathComponent("ollama-darwin.tgz")
        try run(URL(fileURLWithPath: "/usr/bin/curl"), ["--fail", "--location", "--retry", "2", "--connect-timeout", "30", "--max-time", "3600", "--continue-at", "-", "--output", archive.path, "https://github.com/ollama/ollama/releases/download/v0.35.1/ollama-darwin.tgz"])
        guard try sha256(archive) == "3137dbf28948ee844e0fb3e584d9b5de6879d73d9f0cb7eff3ad64930601d307" else {
            // Keep invalid archive for diagnosis, but don't reuse it as a resumable download.
            try? FileManager.default.moveItem(at: archive, to: root.appendingPathComponent("ollama-invalid-\(UUID().uuidString).tgz"))
            throw AppFailure(message: "引擎校驗失敗，未執行下載檔案。請重新下載。")
        }
        let dest = root.appendingPathComponent("ollama")
        try FileManager.default.createDirectory(at: dest, withIntermediateDirectories: true)
        try run(URL(fileURLWithPath: "/usr/bin/tar"), ["-xzf", archive.path, "-C", dest.path])
        if !ollamaReady {
            let flat = dest.appendingPathComponent("ollama")
            if FileManager.default.isExecutableFile(atPath: flat.path) {
                try FileManager.default.createDirectory(at: dest.appendingPathComponent("bin"), withIntermediateDirectories: true)
                try FileManager.default.createSymbolicLink(at: ollama, withDestinationURL: flat)
            }
        }
        guard ollamaReady else { throw AppFailure(message: "下載完成，但引擎目錄格式未符合預期。詳見環境資料夾。") }
        event("完成", "本機 AI 引擎已部署。", 1)
    }
    func startServer() throws {
        startupLock.lock(); defer { startupLock.unlock() }
        try checkCancellation()
        // A previous app instance may already serve this port. Do not launch a
        // duplicate or take ownership of a service this Engine did not start.
        if ollamaIsReady() { return }
        guard ollamaReady else { throw AppFailure(message: "請先喺環境頁下載本機 AI 引擎。") }
        lock.lock(); let existing = server; lock.unlock()
        let p = existing?.isRunning == true ? existing! : managedProcess(ollama, ["serve"])
        let log = root.appendingPathComponent("ollama.log")
        var handle: FileHandle?
        var logOffset: UInt64 = 0
        defer { try? handle?.close() }
        do {
            if !p.isRunning {
                if !FileManager.default.fileExists(atPath: log.path) { FileManager.default.createFile(atPath: log.path, contents: nil) }
                handle = try FileHandle(forWritingTo: log)
                logOffset = try handle!.seekToEnd()
                p.standardOutput = handle
                p.standardError = handle
                lock.lock()
                if cancelled || shuttingDown { lock.unlock(); throw AppFailure(message: "工作已取消。") }
                do { try p.run(); server = p; lock.unlock() }
                catch { lock.unlock(); throw error }
            }
            for _ in 0..<40 {
                try checkCancellation()
                // Probe before checking process exit: another instance can win
                // the bind race and still provide a healthy Ollama endpoint.
                if ollamaIsReady() { return }
                if !p.isRunning {
                    let reader = try? FileHandle(forReadingFrom: log)
                    defer { try? reader?.close() }
                    try? reader?.seek(toOffset: logOffset)
                    let detail = String(data: (try? reader?.readToEnd()) ?? Data(), encoding: .utf8) ?? ""
                    if detail.contains("address already in use") {
                        throw AppFailure(message: "連接埠 \(port) 已被佔用，但未能確認係正常嘅 Ollama 服務。請查看 ollama.log；現有服務未被停止。")
                    }
                    throw AppFailure(message: "本機 AI 引擎啟動失敗（退出碼 \(p.terminationStatus)）：\(detail.trimmingCharacters(in: .whitespacesAndNewlines).suffix(700))。詳見 ollama.log。")
                }
                Thread.sleep(forTimeInterval: 0.25)
            }
            throw AppFailure(message: "本機 AI 引擎啟動逾時；未通過服務檢查。請重試或查看 ollama.log。")
        } catch {
            // Only clean up the process started by this Engine.
            stopManagedProcess(p)
            lock.lock(); if server === p { server = nil }; lock.unlock()
            throw error
        }
    }
    func ollamaIsReady() -> Bool {
        guard let versionData = try? request("/api/version", timeout: 1),
              let version = try? JSONSerialization.jsonObject(with: versionData) as? [String:Any],
              let number = version["version"] as? String, !number.isEmpty,
              let tagsData = try? request("/api/tags", timeout: 1),
              let tags = try? JSONSerialization.jsonObject(with: tagsData) as? [String:Any],
              let models = tags["models"] as? [[String:Any]] else { return false }
        return models.allSatisfy { ($0["name"] as? String)?.isEmpty == false }
    }
    @discardableResult
    func request(_ path: String, timeout: Double = 5, body: [String:Any]? = nil, method: String = "POST") throws -> Data {
        let sem = DispatchSemaphore(value: 0)
        let box = ResponseBox()
        let isMLX = (body?["model"] as? String)?.hasPrefix("mlx:") == true
        if isMLX { try startTextModel(body?["model"] as? String ?? Self.mlxModel) }
        let targetPort = isMLX ? (mlxPort ?? port) : port
        var request = URLRequest(url: URL(string: "http://127.0.0.1:\(targetPort)\(path)")!)
        request.timeoutInterval = timeout
        if let body {
            request.httpMethod = method
            request.setValue("application/json", forHTTPHeaderField:"Content-Type")
            request.httpBody = try JSONSerialization.data(withJSONObject:body)
        }
        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            box.data = data; box.error = error
            if error == nil, let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
                box.error = AppFailure(message: "本機 AI 服務回傳 HTTP \(http.statusCode)。")
            }
            sem.signal()
        }
        task.resume()
        if sem.wait(timeout: .now() + timeout + 1) == .timedOut { task.cancel(); throw AppFailure(message: "本機模型連線逾時。") }
        if let error = box.error { throw error }
        return box.data ?? Data()
    }
    func pullModel(_ model: String) throws {
        if model.hasPrefix("mlx:") { try downloadMLXText(model); return }
        if !runtimeReady { try installRuntime() }
        try startServer()
        event("下載", "下載 \(model)。模型可能佔數 GB，下載中可取消及稍後續傳。")
        // Ollama verifies content-addressed model blobs and resumes incomplete pulls.
        try worker("download-model", config: ["port":port, "model":model])
        event("完成", "\(model) 已準備好，可離線使用。", 1)
    }
    func availableModels() -> [String] {
        guard let data = try? request("/api/tags", timeout: 1), let obj = try? JSONSerialization.jsonObject(with: data) as? [String:Any], let list = obj["models"] as? [[String:Any]] else { return installedMLXModels }
        return list.compactMap { $0["name"] as? String } + installedMLXModels
    }
    func installedModelsOnDisk() -> [String] {
        let base = root.appendingPathComponent("models/ollama/manifests/registry.ollama.ai/library")
        guard let enumerator = FileManager.default.enumerator(at:base,includingPropertiesForKeys:[.isRegularFileKey]) else { return installedMLXModels }
        return enumerator.compactMap { item -> String? in
            guard let url = item as? URL, (try? url.resourceValues(forKeys:[.isRegularFileKey]).isRegularFile) == true else { return nil }
            return url.deletingLastPathComponent().lastPathComponent + ":" + url.lastPathComponent
        }.sorted() + installedMLXModels
    }
    func vlcSubtitle(source: URL, stream: Int? = nil) throws -> URL {
        let attrs = try FileManager.default.attributesOfItem(atPath: source.path)
        let key = SHA256.hash(data: Data(("vlc-ass-v1|" + source.path + "|\(stream ?? -1)|\(attrs[.size] ?? 0)|\(attrs[.modificationDate] ?? "")").utf8)).prefix(12).map { String(format:"%02x", $0) }.joined()
        let dir = root.appendingPathComponent("previews")
        try FileManager.default.createDirectory(at:dir,withIntermediateDirectories:true)
        let target = dir.appendingPathComponent(key + ".ass")
        if FileManager.default.fileExists(atPath:target.path) { return target }
        var args = ["-v","error","-i",source.path]
        if let stream { args += ["-map","0:\(stream)"] }
        args += ["-f","ass","pipe:1"]
        let original = try run(ffmpeg,args)
        // Preserve ASS timing, positioning and colours. A bundled CJK family
        // avoids broken system fallback paths and missing fonts on clean Macs.
        let lines = original.components(separatedBy:"\n").map { line -> String in
            guard line.hasPrefix("Style:") else { return line }
            var fields = line.components(separatedBy:",")
            if fields.count > 2 { fields[1] = "Noto Sans CJK TC" }
            return fields.joined(separator:",")
        }
        let styled = lines.joined(separator:"\n").replacingOccurrences(of: #"\\fn[^}\\]*"#, with: #"\\fnNoto Sans CJK TC"#, options:.regularExpression)
        try styled.write(to:target,atomically:true,encoding:.utf8)
        return target
    }

    func vlcOutputSubtitle(source: URL) throws -> URL? {
        // Exported files must work without their original job directory.
        let raw = try run(ffprobe,["-v","error","-select_streams","s","-show_streams","-show_format","-of","json",source.path])
        if let data=raw.data(using:.utf8), let object=try JSONSerialization.jsonObject(with:data) as? [String:Any],
           let format=object["format"] as? [String:Any], let tags=format["tags"] as? [String:String], tags["comment"] == "CantoSync:burned-captions" { return nil }
        if let data=raw.data(using:.utf8), let object=try JSONSerialization.jsonObject(with:data) as? [String:Any],
           let streams=object["streams"] as? [[String:Any]],
           let selected=streams.first(where: { ["ass","ssa","subrip","mov_text","webvtt","text"].contains($0["codec_name"] as? String ?? "") }), let index=selected["index"] as? Int {
            return try vlcSubtitle(source:source,stream:index)
        }
        for file in [source.deletingPathExtension().appendingPathExtension("srt"),source.deletingPathExtension().appendingPathExtension("ass"),source.deletingLastPathComponent().appendingPathComponent("cantonese.srt")] {
            if FileManager.default.fileExists(atPath:file.path) { return try vlcSubtitle(source:file) }
        }
        throw AppFailure(message:"成品冇可用字幕軌或同名字幕檔。")
    }

    func inspectVideo(_ video: URL) throws -> MediaInfo {
        event("分析", "讀取影片、音軌同可選字幕軌。")
        let raw = try run(ffprobe, ["-v", "error", "-show_format", "-show_streams", "-of", "json", video.path])
        guard let data = raw.data(using: .utf8), let obj = try JSONSerialization.jsonObject(with: data) as? [String:Any], let streams = obj["streams"] as? [[String:Any]], streams.contains(where: { $0["codec_type"] as? String == "video" }) else { throw AppFailure(message: "讀唔到影片軌。請揀有效嘅 MP4／MKV。") }
        var tracks: [SubtitleTrack] = streams.filter { $0["codec_type"] as? String == "subtitle" }.compactMap { stream in
            guard let index = stream["index"] as? Int else { return nil }
            let tags = stream["tags"] as? [String:String] ?? [:]
            return SubtitleTrack(id: index, language: tags["language"] ?? "未標示語言", title: tags["title"] ?? "", codec: stream["codec_name"] as? String ?? "unknown")
        }
        // Text tracks in MKV often begin after a long OP. Show this distinction
        // instead of presenting an empty opening as a subtitle loading failure.
        for i in tracks.indices where ["ass", "ssa", "subrip", "mov_text", "webvtt", "text"].contains(tracks[i].codec) {
            let first = try run(ffprobe, ["-v", "error", "-select_streams", "\(tracks[i].id)", "-read_intervals", "%+#1", "-show_packets", "-show_entries", "packet=pts_time", "-of", "json", video.path])
            if let data = first.data(using: .utf8), let packetInfo = try? JSONSerialization.jsonObject(with: data) as? [String:Any], let packets = packetInfo["packets"] as? [[String:Any]], let text = packets.first?["pts_time"] as? String, let time = Double(text), time.isFinite, time >= 0 { tracks[i].firstCue = time }
        }
        let format = obj["format"] as? [String:Any] ?? [:]
        let duration = Double(format["duration"] as? String ?? "0") ?? 0
        let picture = streams.first { $0["codec_type"] as? String == "video" } ?? [:]
        let dar = (picture["display_aspect_ratio"] as? String ?? "").split(separator: ":").compactMap { Double($0) }
        var aspect = Double(picture["width"] as? Int ?? 16) / max(1, Double(picture["height"] as? Int ?? 9))
        if dar.count == 2, dar[0] > 0, dar[1] > 0 { aspect = dar[0] / dar[1] }
        if let data = picture["side_data_list"] as? [[String:Any]], let rotation = data.compactMap({ $0["rotation"] as? Double }).first, abs(rotation.truncatingRemainder(dividingBy: 180)) == 90 { aspect = 1 / aspect }
        var preview = video
        let plan = PreviewEncodingPlan(picture: picture, audio: streams.first { $0["codec_type"] as? String == "audio" })
        if !VLCAPI.bundled && (!["mp4", "m4v", "mov"].contains(video.pathExtension.lowercased()) || !plan.copyVideo || !plan.copyAudio) {
            let attrs = try FileManager.default.attributesOfItem(atPath: video.path)
            let key = SHA256.hash(data: Data(("preview-v2|" + video.path + "\(attrs[.size] ?? 0)" + "\(attrs[.modificationDate] ?? "")").utf8)).prefix(12).map { String(format: "%02x", $0) }.joined()
            let dir = root.appendingPathComponent("previews")
            try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
            preview = dir.appendingPathComponent(key + ".mp4")
            if !FileManager.default.fileExists(atPath: preview.path) {
                event("預覽", plan.copyVideo && plan.copyAudio ? "快速建立播放檔：影像同音訊直接複製，保留可選字幕。" : "建立 Mac 相容播放檔；只重新編碼唔相容嘅軌道。", 0)
                let temporary = dir.appendingPathComponent(key + ".partial.mp4")
                defer { try? FileManager.default.removeItem(at: temporary) }
                var args = ["-v", "error", "-nostdin", "-nostats", "-progress", "pipe:1", "-y", "-i", video.path, "-map", "0:v:0", "-map", "0:a:0?"]
                for track in tracks where track.supported { args += ["-map", "0:\(track.id)"] }
                args += ["-c:s", "mov_text"]
                args += plan.arguments
                args += ["-movflags", "+faststart", temporary.path]
                try run(ffmpeg, args, mediaDuration: duration)
                try FileManager.default.moveItem(at: temporary, to: preview)
            }
        }
        return MediaInfo(tracks: tracks, preview: preview, duration: duration, aspectRatio: aspect, burnedCaptions: (format["tags"] as? [String:String])?["comment"] == "CantoSync:burned-captions")
    }
    func previewCaptions(source: URL, stream: Int?) throws -> [PreviewCaption] {
        let attrs = try FileManager.default.attributesOfItem(atPath: source.path)
        let key = SHA256.hash(data: Data((source.path + "|\(stream ?? -1)|\(attrs[.size] ?? 0)|\(attrs[.modificationDate] ?? "")").utf8)).prefix(12).map { String(format: "%02x", $0) }.joined()
        let dir = root.appendingPathComponent("previews")
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        let file = dir.appendingPathComponent("captions-" + key + ".srt")
        if !FileManager.default.fileExists(atPath: file.path) {
            var args = ["-v", "error", "-nostdin", "-i", source.path]
            if let stream { args += ["-map", "0:\(stream)"] }
            args += ["-f", "srt", "pipe:1"]
            let text = try run(ffmpeg, args)
            try text.write(to: file, atomically: true, encoding: .utf8)
        }
        return PreviewCaption.parse(try String(contentsOf: file, encoding: .utf8))
    }
    static let mlxModel = "mlx:qwen3.5-35b-a3b:4bit"
    var installedMLXModels:[String] {ModelOption.all.filter{$0.category=="text" && $0.ready(root)}.map(\.id)}
    var mlxReady: Bool { FileManager.default.fileExists(atPath:root.appendingPathComponent("mlx-text-ready.json").path) }
    func startTextModel(_ model: String) throws {
        if lightweightPackage && model.hasPrefix("mlx:") && !runtimeVerified("text-runtime") {try ensureMacRuntime("text-runtime")}
        if !model.hasPrefix("mlx:") {
            if let p=mlxServer { stopManagedProcess(p) };mlxServer=nil;mlxPort=nil
            try startServer(); return
        }
        startupLock.lock(); defer { startupLock.unlock() }
        if let p = mlxServer, p.isRunning { return }
        guard ModelOption.all.first(where:{$0.id==model})?.ready(root)==true else { throw AppFailure(message:"請先下載所選 MLX 文字模型。") }
        let ready=root.appendingPathComponent("mlx-server-\(UUID().uuidString).json")
        let token=UUID().uuidString
        let p=managedProcess(runtimePython("text-runtime"),[resources.appendingPathComponent("mlx_text.py").path,"serve",root.path,"--ready",ready.path,"--token",token])
        let log=root.appendingPathComponent("mlx-text.log");FileManager.default.createFile(atPath:log.path,contents:nil)
        let handle=try FileHandle(forWritingTo:log);defer { try? handle.close() }
        p.standardOutput=handle;p.standardError=handle
        try p.run();mlxServer=p
        defer { try? FileManager.default.removeItem(at:ready) }
        for _ in 0..<100 {
            try checkCancellation()
            if let data=try? Data(contentsOf:ready), let info=try? JSONSerialization.jsonObject(with:data) as? [String:Any], info["token"] as? String == token, let port=info["port"] as? Int {
                mlxPort=port;return
            }
            if !p.isRunning { break };Thread.sleep(forTimeInterval:0.1)
        }
        stopManagedProcess(p);mlxServer=nil;mlxPort=nil
        throw AppFailure(message:"MLX 文字服務啟動失敗，詳見 mlx-text.log。")
    }
    func downloadMLXText(_ model:String = Engine.mlxModel) throws {
        if lightweightPackage {try ensureMacRuntime("text-runtime")}
        try run(runtimePython("text-runtime"),[resources.appendingPathComponent("mlx_text.py").path,"install",root.path,"--model",model],protocolOutput:true)
    }
    func removeMLXText(_ model:String = Engine.mlxModel) throws {
        if let p=mlxServer { stopManagedProcess(p) };mlxServer=nil;mlxPort=nil
        guard let option=ModelOption.all.first(where:{$0.id==model}) else{return}
        for path in ["model-ready/"+model.replacingOccurrences(of:":",with:"-")+".json",option.relativeFolder]+(model==Self.mlxModel ? ["mlx-text-ready.json"]:[]) {
            let url=root.appendingPathComponent(path)
            if FileManager.default.fileExists(atPath:url.path) { try FileManager.default.removeItem(at:url) }
        }
    }

    func worker(_ action: String, config: [String: Any]) throws {
        guard runtimeReady else { throw AppFailure(message: "請先部署本機執行環境。") }
        let effective=WorkerModelSelection.effective(config,action:action)
        var requestConfig=config
        if ["convert","batch"].contains(action) {
            requestConfig["productionPlan"]=try productionPlan(config)
        }
        let model=effective["model"] as? String
        let needsText = action != "speech-studio" || (effective["speechStudio"] as? [String:Any])?["action"] as? String == "translate"
        if needsText,let model,model.hasPrefix("mlx:") || ["speech-studio","render","render-project","rebuild-dialogue","shorten-cue","translate-cue"].contains(action) {
            try startTextModel(model)
        }
        if let model {lock.lock();usedModels.insert(model);lock.unlock()}
        if effective["aiAutoFix"] as? Bool == true {
            if let repairModel=WorkerModelSelection.repairModel(effective) {
                requestConfig["aiRepairModel"]=repairModel
                do {try startTextModel(repairModel);lock.lock();usedModels.insert(repairModel);lock.unlock()}
                catch {
                    try checkCancellation()
                    requestConfig["aiDecisionUnavailable"]=true
                    event("固定修復流程","可選 AI 修復服務未能啟動；缺聲偵測、角色卡後備配音及輸出會繼續。"+error.localizedDescription)
                }
            } else {requestConfig["aiDecisionUnavailable"]=true}
        }
        let file = root.appendingPathComponent("request-\(UUID().uuidString).json")
        try JSONSerialization.data(withJSONObject: requestConfig, options: [.prettyPrinted, .sortedKeys]).write(to: file, options: .atomic)
        defer { try? FileManager.default.removeItem(at: file) }
        try run(python, [resources.appendingPathComponent("worker.py").path, action, file.path], protocolOutput: true)
    }
}

private final class ResponseBox: @unchecked Sendable { var data: Data?; var error: Error? }
