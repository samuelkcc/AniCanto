import Foundation
import Darwin

/// Headless platform adapter for the shared desktop. The UI never reimplements
/// model selection, deployment, process ownership or conversion policy.
func runSharedStudioBridgeIfNeeded() -> Bool {
    let args = CommandLine.arguments
    guard args.count > 1, args[1].hasPrefix("--studio-") else { return false }
    let engine = Engine(port: 11447)
    let outputLock = NSLock()
    func output(_ value: Any) {
        guard let data = try? JSONSerialization.data(withJSONObject:value, options:[.sortedKeys]) else { return }
        outputLock.lock(); defer {outputLock.unlock()}
        FileHandle.standardOutput.write(data); FileHandle.standardOutput.write(Data([10]))
    }
    engine.notify = { event in
        // WorkerEvent intentionally decodes a bounded projection. Encode the
        // fields consumed by the shared studio rather than reflect Swift types.
        output(event.sharedStudioFields())
    }
    // Engine owns separate process groups for model runners; forward shutdown
    // to that owner, so pausing cannot strand a grandchild model process.
    signal(SIGTERM,SIG_IGN); signal(SIGINT,SIG_IGN)
    let termination=DispatchSource.makeSignalSource(signal:SIGTERM,queue:.global())
    termination.setEventHandler {engine.shutdown(); exit(143)};termination.resume()
    let interrupt=DispatchSource.makeSignalSource(signal:SIGINT,queue:.global())
    interrupt.setEventHandler {engine.shutdown(); exit(130)};interrupt.resume()
    let parent=Int32(ProcessInfo.processInfo.environment["CANTOSYNC_HOST_PID"] ?? "")
    let watchdog=DispatchSource.makeTimerSource(queue:.global())
    watchdog.schedule(deadline:.now()+2,repeating:2)
    watchdog.setEventHandler {if let parent, kill(parent,0) != 0, errno == ESRCH {engine.shutdown();exit(143)}}
    watchdog.resume()
    defer {watchdog.cancel();termination.cancel();interrupt.cancel();engine.shutdown()}
    do {
        switch args[1] {
        case "--studio-bootstrap":
            if !engine.runtimeReady {try engine.installRuntime()}
        case "--studio-plan":
            let requested=args.count>3 ? (try JSONSerialization.jsonObject(with:Data(args[3].utf8)) as? [String:String] ?? [:]):[:]
            output(try engine.firstRunModelPlan(engine:args.count>2 ? args[2]:"drama3",requested:requested))
        case "--studio-setup":
            let requested=args.count>3 ? (try JSONSerialization.jsonObject(with:Data(args[3].utf8)) as? [String:String] ?? [:]):[:]
            let plan=try engine.firstRunModelPlan(engine:args.count>2 ? args[2]:"drama3",requested:requested)
            let selections=try engine.deployFirstRun(plan)
            output(["stage":"Setup complete","message":"Models and runtimes verified.","selections":selections,"progress":1])
        case "--studio-task":
            guard args.count==4 else {throw AppFailure(message:"Missing studio action or request.")}
            let actions=Set(["speech-studio","batch","convert","render-project","prepare-reference","import-reference","preview-separation","translate-cue","shorten-cue","auto-speakers"])
            guard actions.contains(args[2]) else {throw AppFailure(message:"Unsupported studio action.")}
            let cfg=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:args[3]))) as! [String:Any]
            if !engine.runtimeReady {try engine.installRuntime()}
            if ["batch","convert"].contains(args[2]) {
                if cfg["autoSpeakers"] as? Bool==true {try engine.ensureAutoSpeakers(independent:cfg["roleAnalysisMode"] as? String=="independent")}
                try engine.ensureSpeechTiming(qualityChecks:cfg["productionMode"] as? String != "fast")
            }
            try engine.worker(args[2],config:cfg)
        default:throw AppFailure(message:"Unknown studio bridge command.")
        }
    } catch {
        output(["stage":"錯誤","message":error.localizedDescription]);engine.shutdown();exit(1)
    }
    return true
}
