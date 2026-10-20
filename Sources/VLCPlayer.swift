import AppKit
import AVFoundation
import Darwin
import CoreText

// libVLC is shipped inside this app; never load the user's VLC installation.
final class VLCAPI {
    private static let loaded: Result<VLCAPI, Error> = Result { try VLCAPI() }
    static var shared: VLCAPI? { try? loaded.get() }
    static var loadError: String? { if case .failure(let error) = loaded { return error.localizedDescription }; return nil }
    let handle: UnsafeMutableRawPointer
    let instance: OpaquePointer
    static var bundled: Bool { Bundle.main.resourceURL.map { FileManager.default.fileExists(atPath: $0.appendingPathComponent("vlc/lib/libvlc.dylib").path) } ?? false }
    private init() throws {
        let root = Bundle.main.resourceURL!.appendingPathComponent("vlc")
        let fonts = root.appendingPathComponent("fonts")
        CTFontManagerRegisterFontsForURL(fonts.appendingPathComponent("NotoSansCJKtc-Regular.otf") as CFURL, .process, nil)
        setenv("VLC_PLUGIN_PATH", root.appendingPathComponent("plugins").path, 1)
        guard let h = dlopen(root.appendingPathComponent("lib/libvlc.dylib").path, RTLD_NOW | RTLD_GLOBAL) else { throw NSError(domain:"AniCanto.VLC",code:1,userInfo:[NSLocalizedDescriptionKey:"內置播放器載入失敗：" + String(cString:dlerror())]) }
        for name in ["libvlc_audio_get_track", "libvlc_audio_get_track_description", "libvlc_audio_set_track", "libvlc_video_get_spu", "libvlc_audio_set_mute", "libvlc_media_new_path", "libvlc_media_player_add_slave", "libvlc_media_player_get_length", "libvlc_media_player_get_state", "libvlc_media_player_get_time", "libvlc_media_player_new", "libvlc_media_player_play", "libvlc_media_player_release", "libvlc_media_player_set_media", "libvlc_media_player_set_nsobject", "libvlc_media_player_set_pause", "libvlc_media_player_set_time", "libvlc_media_player_stop", "libvlc_media_release", "libvlc_new", "libvlc_track_description_list_release", "libvlc_video_get_spu_description", "libvlc_video_set_spu"] {
            guard dlsym(h,name) != nil else {
                dlclose(h)
                throw NSError(domain:"AniCanto.VLC",code:2,userInfo:[NSLocalizedDescriptionKey:"內置播放器缺少元件："+name])
            }
        }
        handle = h
        let create = unsafeBitCast(dlsym(h, "libvlc_new")!, to: (@convention(c) (Int32, UnsafePointer<UnsafePointer<CChar>?>?) -> OpaquePointer?).self)
        // macOS 27 VideoToolbox can deadlock VLC input_Close during source changes.
        // Keep preview decoding in software on that OS; conversion/TTS are unchanged.
        let decoderOptions=ProcessInfo.processInfo.operatingSystemVersion.majorVersion>=27 ? ["--avcodec-hw=none"]:[]
        let strings = (decoderOptions + ["--no-video-title-show", "--no-osd", "--no-sub-autodetect-file", "--vout=macosx", "--quiet", "--ssa-fontsdir=\(fonts.path)", "--freetype-font=Noto Sans CJK TC"]).map { (s: String) in s.withCString { strdup($0)! } }
        defer { strings.forEach { free($0) } }
        let args = strings.map { Optional(UnsafePointer<CChar>($0)) }
        guard let p = args.withUnsafeBufferPointer({ create(Int32($0.count), $0.baseAddress) }) else { dlclose(h); throw NSError(domain:"AniCanto.VLC",code:3,userInfo:[NSLocalizedDescriptionKey:"內置播放器初始化失敗，請重新開啟 App。"]) }
        instance = p
    }
    func fn<T>(_ name: String, _ type: T.Type) -> T { unsafeBitCast(dlsym(handle, name)!, to: type) }
}

final class CantoPlayer {
    private let api=VLCAPI.shared
    let pointer:OpaquePointer?
    var currentItem:AVPlayerItem?
    private var observers:[Timer]=[]
    private var loadTimer:Timer?
    private var pendingTime=0.0
    private var seekSettlingUntil=Date.distantPast
    private var wantsPlay=false
    private var ready=false
    private var mediaError:String?
    private var subtitleOrdinal:Int?
    private var externalSubtitle:URL?
    private let drawable=NSView()
    private let commands=PreviewCommandQueue()
    private var attached=false
    private var mediaGeneration=0
    private var polling=false
    private var cachedTime=0.0,cachedDuration=0.0
    private var cachedState:Int32=0
    struct TrackDescription {let id:Int32,name:String}
    private var cachedAudioTracks:[TrackDescription]=[],cachedSubtitleTracks:[TrackDescription]=[]
    private var cachedAudioTrack:Int32 = -1,cachedSubtitleTrack:Int32 = -1
    private var tracksNeedRefresh=true
    private var trackRevision=0
    init() {
        if let api {pointer=api.fn("libvlc_media_player_new",(@convention(c) (OpaquePointer)->OpaquePointer?).self)(api.instance)}
        else {pointer=nil}
    }
    deinit {
        observers.forEach {$0.invalidate()};loadTimer?.invalidate()
        guard let api,let pointer else{return}
        let retainedDrawable=drawable
        commands.finish {
            api.fn("libvlc_media_player_stop",(@convention(c) (OpaquePointer)->Void).self)(pointer)
            api.fn("libvlc_media_player_release",(@convention(c) (OpaquePointer)->Void).self)(pointer)
            DispatchQueue.main.async {withExtendedLifetime(retainedDrawable) {}}
        }
    }
    var failure:String? {
        guard api != nil,pointer != nil else{return VLCAPI.loadError ?? "播放器未能建立，請重新開啟 App。"}
        requestPoll()
        return mediaError ?? (cachedState==7 ? "VLC 未能解碼呢個檔案；請檢查影片是否已完整下載。":nil)
    }
    var volume:Float=1 {didSet {
        volume=min(1,max(0,volume));guard volume != oldValue,let api,let pointer else{return}
        let level=Int32((volume*100).rounded())
        commands.submit(key:"volume") {_ in _=api.fn("libvlc_audio_set_volume",(@convention(c) (OpaquePointer,Int32)->Int32).self)(pointer,level)}
    }}
    var isMuted=false {didSet {
        guard isMuted != oldValue,let api,let pointer else{return};let mute:Int32=isMuted ? 1:0
        commands.submit(key:"mute") {_ in api.fn("libvlc_audio_set_mute",(@convention(c) (OpaquePointer,Int32)->Void).self)(pointer,mute)}
    }}
    var rate:Float {wantsPlay ? 1:0}
    var duration:Double {requestPoll();return cachedDuration}
    func currentTime()->CMTime {
        requestPoll()
        let time=ready ? cachedTime:pendingTime
        let settled=(Date()<seekSettlingUntil && abs(time-pendingTime)>0.5) ? pendingTime:time
        return CMTime(seconds:max(0,settled),preferredTimescale:1000)
    }
    func attach(_ view:NSView) {
        guard let api,let pointer else{return}
        if drawable.superview !== view {
            drawable.removeFromSuperview();view.addSubview(drawable)
            drawable.frame=view.bounds;drawable.autoresizingMask=[.width,.height]
        }
        guard !attached else{return};attached=true
        // AppKit owns the drawable; attach it on AppKit's thread.
        api.fn("libvlc_media_player_set_nsobject",(@convention(c) (OpaquePointer,UnsafeMutableRawPointer?)->Void).self)(pointer,Unmanaged.passUnretained(drawable).toOpaque())
    }
    func replaceCurrentItem(with item:AVPlayerItem?) {
        mediaGeneration += 1;let generation=mediaGeneration;commands.invalidate()
        loadTimer?.invalidate();ready=false;wantsPlay=false;pendingTime=0;cachedTime=0;cachedDuration=0;cachedState=0
        cachedAudioTracks=[];cachedSubtitleTracks=[];tracksNeedRefresh=true
        cachedAudioTrack = -1;cachedSubtitleTrack = -1
        currentItem=item;mediaError=nil
        guard let api,let pointer else{return}
        let url=(item?.asset as? AVURLAsset)?.url
        commands.submit { [weak self,commands] ticket in
            api.fn("libvlc_media_player_stop",(@convention(c) (OpaquePointer)->Void).self)(pointer)
            guard commands.current(ticket),let url else{return}
            guard let media=api.fn("libvlc_media_new_path",(@convention(c) (OpaquePointer,UnsafePointer<CChar>)->OpaquePointer?).self)(api.instance,url.path) else {
                DispatchQueue.main.async {if self?.mediaGeneration==generation {self?.mediaError="播放器未能開啟影片，請檢查檔案。"}}
                return
            }
            api.fn("libvlc_media_player_set_media",(@convention(c) (OpaquePointer,OpaquePointer)->Void).self)(pointer,media)
            api.fn("libvlc_media_release",(@convention(c) (OpaquePointer)->Void).self)(media)
            _=api.fn("libvlc_media_player_play",(@convention(c) (OpaquePointer)->Int32).self)(pointer)
        }
        guard url != nil else{return}
        let started=Date()
        loadTimer=Timer.scheduledTimer(withTimeInterval:0.1,repeats:true) { [weak self] timer in
            guard let self,self.mediaGeneration==generation else{timer.invalidate();return}
            self.requestPoll()
            if self.ready {timer.invalidate()}
            else if Date().timeIntervalSince(started)>20 {timer.invalidate();self.mediaError="影片載入逾時，請檢查檔案是否已完整下載。"}
        }
    }
    func play() {
        wantsPlay=true;guard ready,let api,let pointer else{return}
        commands.submit(key:"transport") {_ in _=api.fn("libvlc_media_player_play",(@convention(c) (OpaquePointer)->Int32).self)(pointer)}
    }
    func pause() {
        wantsPlay=false;guard ready,let api,let pointer else{return}
        commands.submit(key:"transport") {_ in api.fn("libvlc_media_player_set_pause",(@convention(c) (OpaquePointer,Int32)->Void).self)(pointer,1)}
    }
    func seek(to time:CMTime,toleranceBefore:CMTime = .zero,toleranceAfter:CMTime = .zero,completionHandler:((Bool)->Void)?=nil) {
        guard let api,let pointer,time.seconds.isFinite else{completionHandler?(false);return}
        pendingTime=max(0,time.seconds);seekSettlingUntil=Date().addingTimeInterval(2)
        guard ready else{completionHandler?(true);return}
        let target=Int64(pendingTime*1000),paused = !wantsPlay
        commands.submit(key:"seek") { [weak self,commands] ticket in
            if paused {
                api.fn("libvlc_audio_set_mute",(@convention(c) (OpaquePointer,Int32)->Void).self)(pointer,1)
                api.fn("libvlc_media_player_set_pause",(@convention(c) (OpaquePointer,Int32)->Void).self)(pointer,0)
            }
            api.fn("libvlc_media_player_set_time",(@convention(c) (OpaquePointer,Int64)->Void).self)(pointer,target)
            DispatchQueue.main.asyncAfter(deadline:.now()+0.2) { [weak self] in
                guard let self,commands.current(ticket) else{return}
                if !self.wantsPlay {self.pause()}
                let mute:Int32=self.isMuted ? 1:0,level=Int32((self.volume*100).rounded())
                commands.submit(key:"seek-settle") {_ in
                    api.fn("libvlc_audio_set_mute",(@convention(c) (OpaquePointer,Int32)->Void).self)(pointer,mute)
                    _=api.fn("libvlc_audio_set_volume",(@convention(c) (OpaquePointer,Int32)->Int32).self)(pointer,level)
                }
            }
        }
        completionHandler?(true)
    }
    /// Poll on the decoder queue, with one in-flight request. UI clocks use
    /// cached values and remain responsive even if the input thread stalls.
    private func requestPoll() {
        guard !polling,currentItem != nil,let api,let pointer else{return}
        polling=true;let generation=mediaGeneration,refreshTracks=tracksNeedRefresh,revision=trackRevision
        // A poll always clears its in-flight flag, including source changes.
        commands.always { [weak self] in
            let state=api.fn("libvlc_media_player_get_state",(@convention(c) (OpaquePointer)->Int32).self)(pointer)
            let length=Double(api.fn("libvlc_media_player_get_length",(@convention(c) (OpaquePointer)->Int64).self)(pointer))/1000
            let time=Double(api.fn("libvlc_media_player_get_time",(@convention(c) (OpaquePointer)->Int64).self)(pointer))/1000
            let canReadTracks=refreshTracks && (state==3 || state==4)
            let audio=canReadTracks ? Self.readTracks(api,pointer,audio:true):[]
            let subtitles=canReadTracks ? Self.readTracks(api,pointer,audio:false):[]
            let selectedAudio=canReadTracks ? api.fn("libvlc_audio_get_track",(@convention(c) (OpaquePointer)->Int32).self)(pointer):Int32(-1)
            let selectedSubtitle=canReadTracks ? api.fn("libvlc_video_get_spu",(@convention(c) (OpaquePointer)->Int32).self)(pointer):Int32(-1)
            DispatchQueue.main.async { [weak self] in
                guard let self else{return};self.polling=false
                guard self.mediaGeneration==generation else{return}
                self.cachedState=state;self.cachedDuration=max(0,length);self.cachedTime=max(0,time)
                if canReadTracks,self.trackRevision==revision {self.cachedAudioTracks=audio;self.cachedSubtitleTracks=subtitles;self.cachedAudioTrack=selectedAudio;self.cachedSubtitleTrack=selectedSubtitle;self.tracksNeedRefresh=false}
                if !self.ready && (state==3 || state==4) {
                    self.ready=true;self.mediaError=nil
                    self.seek(to:CMTime(seconds:self.pendingTime,preferredTimescale:1000));self.applySubtitle()
                }
            }
        }
    }
    func addPeriodicTimeObserver(forInterval interval:CMTime,queue:DispatchQueue?,using block:@escaping (CMTime)->Void)->Any {
        let timer=Timer.scheduledTimer(withTimeInterval:interval.seconds,repeats:true) { [weak self] _ in if let self {block(self.currentTime())} }
        observers.append(timer);return timer
    }
    private static func readTracks(_ api:VLCAPI,_ pointer:OpaquePointer,audio:Bool)->[TrackDescription] {
        struct Track {var id:Int32;var name:UnsafePointer<CChar>?;var next:UnsafeMutableRawPointer?}
        let head=api.fn(audio ? "libvlc_audio_get_track_description":"libvlc_video_get_spu_description",(@convention(c) (OpaquePointer)->UnsafeMutableRawPointer?).self)(pointer)
        defer {if let head {api.fn("libvlc_track_description_list_release",(@convention(c) (UnsafeMutableRawPointer)->Void).self)(head)}}
        var node=head,result:[TrackDescription]=[]
        while let p=node {let row=p.load(as:Track.self);result.append(TrackDescription(id:row.id,name:row.name.map {String(cString:$0)} ?? "Track \(row.id)"));node=row.next}
        return result
    }
    func trackDescriptions(audio:Bool)->[TrackDescription] {requestPoll();return audio ? cachedAudioTracks:cachedSubtitleTracks}
    func selectedTrack(audio:Bool)->Int32 {audio ? cachedAudioTrack:cachedSubtitleTrack}
    func selectTrack(_ id:Int32,audio:Bool) {
        guard let api,let pointer else{return}
        if !audio {externalSubtitle=nil;subtitleOrdinal=nil;cachedSubtitleTrack=id} else {cachedAudioTrack=id}
        tracksNeedRefresh=true;trackRevision += 1
        commands.submit(key:audio ? "audio-track":"subtitle-track") {_ in _=api.fn(audio ? "libvlc_audio_set_track":"libvlc_video_set_spu",(@convention(c) (OpaquePointer,Int32)->Int32).self)(pointer,id)}
    }
    func subtitles(ordinal:Int?,external:URL?) {subtitleOrdinal=ordinal;externalSubtitle=external;if ready {applySubtitle()}}
    private func applySubtitle() {
        guard let api,let pointer else{return}
        let external=externalSubtitle,ordinal=subtitleOrdinal,generation=mediaGeneration,wasPaused = !wantsPlay,target=currentTime()
        commands.submit(key:"subtitle-track") { [weak self] _ in
            if let external {
                _=api.fn("libvlc_media_player_add_slave",(@convention(c) (OpaquePointer,Int32,UnsafePointer<CChar>,Int32)->Int32).self)(pointer,0,external.absoluteString,1)
                if wasPaused {DispatchQueue.main.async {if let self,self.mediaGeneration==generation {self.seek(to:target)}}}
            } else {
                let ids=Self.readTracks(api,pointer,audio:false).filter {$0.id>=0}.map(\.id)
                let id=ordinal.flatMap {ids.indices.contains($0) ? ids[$0]:nil} ?? -1
                _=api.fn("libvlc_video_set_spu",(@convention(c) (OpaquePointer,Int32)->Int32).self)(pointer,id)
            }
        }
        tracksNeedRefresh=true;trackRevision += 1
    }
}


final class VLCVideoView: NSView {
    let surface = NSView()
    var player: CantoPlayer? { didSet { player?.attach(surface) } }
    var showsControls=true {didSet {playButton.isHidden = !showsControls;slider.isHidden = !showsControls}}
    private let playButton = NSButton(title:L("播放／暫停"),target:nil,action:nil)
    private let slider = NSSlider(value:0,minValue:0,maxValue:1,target:nil,action:nil)
    private var timer: Timer?
    var videoBounds: CGRect { surface.bounds }
    override init(frame: NSRect) {
        super.init(frame:frame); wantsLayer = true; layer?.backgroundColor = NSColor.black.cgColor
        addSubview(surface); addSubview(playButton); addSubview(slider)
        playButton.target = self; playButton.action = #selector(toggle)
        slider.target = self; slider.action = #selector(seek)
        timer = Timer.scheduledTimer(withTimeInterval:0.2,repeats:true) { [weak self] _ in
            guard let self, let player = self.player else { return }
            self.slider.maxValue = max(1,player.duration); self.slider.doubleValue = player.currentTime().seconds
        }
    }
    required init?(coder: NSCoder) { fatalError() }
    deinit { timer?.invalidate() }
    override func layout() { super.layout(); surface.frame = bounds; playButton.frame = NSRect(x:8,y:4,width:100,height:28); slider.frame = NSRect(x:116,y:4,width:max(1,bounds.width-130),height:28) }
    @objc private func toggle() { if player?.rate == 0 { player?.play() } else { player?.pause() } }
    @objc private func seek() { player?.seek(to:CMTime(seconds:slider.doubleValue,preferredTimescale:1000)) }
}
