import Foundation

enum JourneyStep:Int,CaseIterable {
    case prepare,subtitles,translation,voice,export
    var title:String { ["準備影片","字幕辨識","廣東話翻譯","角色配音","影片輸出"][rawValue] }
    var icon:String { ["film","text.bubble.fill","character.bubble.fill","mic.fill","flag.checkered"][rawValue] }
    static func matching(_ stage:String)->Self? {
        if ["合成","輸出","解碼驗證"].contains(where:stage.contains) {return .export}
        if ["場景","翻譯","口語","校稿","原意","配音改稿","台詞"].contains(where:stage.contains) {return .translation}
        if ["配音編排","自動配角色","逐句聲音配對","逐句參考","原聲","日語","字幕","辨識"].contains(where:stage.contains) {return .subtitles}
        if ["配音","時長調整","沿用音軌"].contains(where:stage.contains) {return .voice}
        if ["分析","範圍","分離","背景已就緒","保留 OP","試片範圍"].contains(where:stage.contains) {return .prepare}
        return nil
    }
}

/// Counts describe a pass; backend fractions describe approximate workflow position.
/// Neither is a wall-clock estimate. Missing progress remains indeterminate.
struct WorkProgress {
    let value: Double?
    let label: String
    init(pass: Double?, count: String, backend: Double?) {
        func valid(_ value: Double?) -> Double? {
            guard let value, value.isFinite else { return nil }
            return min(1, max(0, value))
        }
        if let p = valid(pass) { value = p; label = count }
        else { value = valid(backend); label = "流程位置（估算）" }
    }
}

// Estimate only a numbered pass, never extrapolate weighted overall UI progress.
struct ProcessingClock {
    private(set) var journeyStep:JourneyStep?
    private(set) var journeyVisited:Set<JourneyStep> = []
    private(set) var voiceTrackLabel = ""
    var started: Date?
    var ended: Date?
    private var phase = ""
    private var phaseStage = ""
    private var phaseStarted: Date?
    private var passIdentity=""
    private var accumulated: [String: Double] = [:]
    private var samples: [(Date, Double)] = []
    private var total = 0.0
    private var latest: Date?
    private var current = 0.0
    private var baseline: Date?
    private var baselineCount = 0.0
    private var rateIdentity = ""
    private var historicalRates:[String:[Double]] = [:]
    private var completedRates:[String:[Double]] = [:]
    private var phaseCached=false
    private var rateRecorded=false
    var passProgress: Double? { total > 0 ? Double(current) / Double(total) : nil }
    var passLabel: String { total > 0 ? String(format:"%g / %g",current,total) : "" }
    private var profile = ""
    private var sourceSeconds = 0.0
    private var expectedTotal: Double?
    private var successful = false
    private var cacheSeen = false
    mutating func configure(profile: String, seconds: Double, directory: URL) {
        self.profile = profile; sourceSeconds = seconds; historicalRates=[:]; expectedTotal=nil
        let files = (try? FileManager.default.contentsOfDirectory(at:directory,includingPropertiesForKeys:nil)) ?? []
        let rates: [Double] = files.compactMap { file in
            guard let data = try? Data(contentsOf:file), let row = try? JSONSerialization.jsonObject(with:data) as? [String:Any], row["profile"] as? String == profile, row["successful"] as? Bool == true,
                  row["cacheSeen"] as? Bool != true, let duration = row["sourceSeconds"] as? Double, duration > 0, let elapsed = row["elapsedSeconds"] as? Double else { return nil }
            return elapsed / duration
        }.sorted()
        if !rates.isEmpty { expectedTotal = rates[rates.count/2] * seconds }
        for file in files {
            guard let data=try? Data(contentsOf:file),let row=try? JSONSerialization.jsonObject(with:data) as? [String:Any],row["profile"] as? String==profile,
                  let measured=row["workRates"] as? [String:[Double]] else {continue}
            for (key,values) in measured {historicalRates[key,default:[]] += values.filter {$0.isFinite && $0>0}}
        }
    }
    mutating func markSuccessful() { successful = true }
    func overallRemaining(at now: Date) -> Double? {
        guard ended == nil, !cacheSeen, let expectedTotal else { return nil }
        let left = expectedTotal - elapsed(at:now)
        return left > 0 ? left : nil
    }


    mutating func start(at now: Date = Date()) { self = ProcessingClock(); started = now }
    mutating func stop(at now: Date = Date()) {
        if ended == nil, let date = phaseStarted { accumulated[phase, default: 0] += max(0, now.timeIntervalSince(date)) }
        ended = now; phaseStarted = nil
    }
    func stages(at now: Date) -> [(String, Double)] {
        var result = accumulated
        if ended == nil, let date = phaseStarted { result[phase, default: 0] += max(0, now.timeIntervalSince(date)) }
        return result.sorted { $0.value > $1.value }.map { ($0.key, $0.value) }
    }
    func save(to directory: URL) {
        let report: [String: Any] = ["profile":profile, "sourceSeconds":sourceSeconds, "successful":successful, "cacheSeen":cacheSeen, "workRates":completedRates, "elapsedSeconds": elapsed(at: Date()), "stages": Dictionary(uniqueKeysWithValues: stages(at: Date())), "completedAt": ISO8601DateFormatter().string(from: ended ?? Date())]
        if let data = try? JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]) {
            try? FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
            try? data.write(to: directory.appendingPathComponent("timing-" + UUID().uuidString + ".json"), options: .atomic)
        }
    }
    func phaseElapsed(at now:Date)->Double {phaseStarted.map {max(0,(ended ?? now).timeIntervalSince($0))} ?? 0}
    mutating func observe(stage: String, message: String, passID:String?=nil, workID:String?=nil, historyID:String?=nil, cached:Bool=false, completed:Double?=nil, units:Double?=nil, at now: Date = Date()) {
        guard started != nil, ended == nil, stage != "工具" else { return }
        if cached {cacheSeen=true;phaseCached=true;samples=[];baseline=now;baselineCount=current;return}
        if let step=JourneyStep.matching(stage) {journeyStep=step;journeyVisited.insert(step)}
        if message.hasPrefix("音軌 ") {voiceTrackLabel=message.components(separatedBy:" · ").prefix(2).joined(separator:" · ")}
        // Cosmetic warning/retry/reference events must not reset a measured pass.
        let transient=["重試","補稿","需修正","待修正","參考錄音","覆核資料","字幕對齊修正"].contains(where:stage.contains)
        let sameTrack = passID != nil && passID==passIdentity
        let key = workID.map { (passID ?? stage) + "|" + $0 } ?? ((sameTrack || phaseStage==stage) ? phase:passID ?? stage)
        if !transient && phase != key {
            if let date=phaseStarted {accumulated[phase,default:0] += max(0,now.timeIntervalSince(date))}
            phase=key;phaseStage=stage;passIdentity=passID ?? "";phaseStarted=now
            samples=[];total=0;current=0;baseline=now;baselineCount=0
            rateIdentity=(historyID ?? stage)+"|"+(workID ?? "count")
            phaseCached=false;rateRecorded=false
        }
        if stage == "沿用音軌" {cacheSeen=true}
        if transient {return}
        let body=message.hasPrefix("音軌 ") ? message.components(separatedBy:" · ").dropFirst(3).joined(separator:" · "):message
        var values:[Double]=[]
        if let completed,let units {values=[completed,units]}
        else if let regex=try? NSRegularExpression(pattern:#"\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?"#),let match=regex.matches(in:body,range:NSRange(body.startIndex...,in:body)).last,let range=Range(match.range,in:body) {
            values=body[range].split(separator:"/").compactMap {Double($0.trimmingCharacters(in:.whitespaces))}
        }
        guard values.count==2,values.allSatisfy(\.isFinite),values[1]>0,values[0]>=0,values[0]<=values[1] else{return}
        if total==0 || total != values[1] || values[0]<current {
            if total>0,values[0]<current {
                if let date=phaseStarted {accumulated[phase,default:0] += max(0,now.timeIntervalSince(date))}
                phaseStarted=now;phaseCached=false
            }
            samples=[];baseline=now;baselineCount=values[0];rateRecorded=false
        }
        total=values[1];current=values[0];latest=now
        if message.contains("沿用") {cacheSeen=true;phaseCached=true;samples=[];baseline=now;baselineCount=current;return}
        if samples.last?.1 != current {
            // Whisper yields many segment timestamps in one decoder batch. Keep
            // the phase baseline and coalesce its burst, not a tiny final segment.
            if let last=samples.last,now.timeIntervalSince(last.0)<1 {samples[samples.count-1]=(now,current)}
            else {samples.append((now,current))}
        }
        if samples.count>256 {samples.removeFirst()}
        if current==total,!rateRecorded,!phaseCached,baselineCount==0,let baseline,current>0 {
            let rate=now.timeIntervalSince(baseline)/current
            if rate.isFinite,rate>0,now.timeIntervalSince(baseline)>=1 {completedRates[rateIdentity,default:[]].append(rate);rateRecorded=true}
        }
    }
    func elapsed(at now:Date)->TimeInterval {max(0,(ended ?? now).timeIntervalSince(started ?? now))}
    private var secondsPerUnit:Double? {
        let prior=((historicalRates[rateIdentity] ?? [])+(completedRates[rateIdentity] ?? [])).sorted()
        let historical=prior.isEmpty ? nil:prior[prior.count/2]
        guard let last=samples.last,let baseline else{return historical}
        let count=last.1-baselineCount,span=last.0.timeIntervalSince(baseline)
        guard count>0,span>=1 else{return historical}
        var measured=span/count
        if let first=samples.first(where:{last.0.timeIntervalSince($0.0)<=120}),last.0.timeIntervalSince(first.0)>=60,last.1-first.1>=max(1,total*0.02) {
            measured=(measured+(last.0.timeIntervalSince(first.0)/(last.1-first.1)))/2
        }
        if let historical {
            let weight=min(1,count/max(1,total*0.1))
            measured=historical*(1-weight)+measured*weight
        }
        return measured
    }
    func remaining(at now:Date)->TimeInterval? {
        guard ended==nil,total>0,current<total,let rate=secondsPerUnit else{return nil}
        // Waiting is not a measured throughput sample. Update rates only when
        // work completes; between reports count down instead of inflating ETA.
        let age=max(0,now.timeIntervalSince(samples.last?.0 ?? baseline ?? now))
        return max(0,rate*(total-current)-age)
    }
    func estimateDelayed(at now:Date)->Bool {
        guard ended==nil,total>current,let anchor=samples.last?.0 ?? baseline,let rate=secondsPerUnit else{return false}
        let batch=samples.count>=2 ? max(1,samples.last!.1-samples[samples.count-2].1):max(1,current-baselineCount)
        return now.timeIntervalSince(anchor)>max(90,rate*batch*3) || (remaining(at:now) ?? 1)<=0
    }
    func estimateBasis(at now:Date)->String {
        if estimateDelayed(at:now) {return "此批次較慢，完成後更新估算"}
        let measured=(samples.last?.1 ?? baselineCount)>baselineCount
        return measured ? "按已完成同類步驟估算":"按相同設定嘅歷史步驟估算"
    }
    var waitingReason:String {
        if total>0 && current>=total {return "本階段已完成，準備下一步"}
        return total>0 ? "等待首個完成項目以估算時間":"載入或準備中，尚未有可量度進度"
    }
    static func duration(_ seconds: TimeInterval, english:Bool = false) -> String {
        if english {
            if seconds < 60 {return "\(max(0,Int(seconds))) s"}
            let minutes=max(1,Int(ceil(seconds/60)))
            return minutes < 60 ? "\(minutes) min":"\(minutes/60) h \(minutes%60) min"
        }
        if seconds < 60 { return "\(max(0,Int(seconds))) 秒" }
        let minutes = max(1, Int(ceil(seconds / 60)))
        return minutes < 60 ? "\(minutes) 分鐘" : "\(minutes / 60) 小時 \(minutes % 60) 分鐘"
    }
}
