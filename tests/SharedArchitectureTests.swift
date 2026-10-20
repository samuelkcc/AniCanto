import Foundation

@main struct SharedArchitectureTests {
    @MainActor static func main() throws {
        let root=URL(fileURLWithPath:FileManager.default.currentDirectoryPath)
        let temp=FileManager.default.temporaryDirectory.appendingPathComponent("anicanto-core-"+UUID().uuidString)
        try FileManager.default.createDirectory(at:temp.appendingPathComponent("bin"),withIntermediateDirectories:true)
        defer {try? FileManager.default.removeItem(at:temp)}
        try FileManager.default.createSymbolicLink(at:temp.appendingPathComponent("bin/anicanto-core"),withDestinationURL:root.appendingPathComponent(".build/core/release/anicanto-core"))
        let engines=["drama3","gpt-sovits-v2","gpt-sovits","cosyvoice3","voxcpm2","wsyue"]
        precondition(VoiceEngineChoice.all.map(\.id)==engines)
        precondition(VoiceEngineChoice.all.last!.languages==["yue"])
        let simple=SimpleProductionPlan(engine:"drama3",languageMode:"both",subtitles:["yue","english","original"],originalStreams:[3])
        let basic=try StudioContract.call(["operation":"plan","settings":simple.settings()],resources:temp)
        var professional=simple.settings();professional["interfaceMode"]="professional"
        let expert=try StudioContract.call(["operation":"plan","settings":professional],resources:temp)
        precondition(basic["identity"] as? String==expert["identity"] as? String)
        precondition(basic["dubbedTrackCount"] as? Int==2)
        precondition(basic["maximumAudioTrackCount"] as? Int==3)
        precondition(basic["burnSubtitles"] as? Bool==false)
        let hardware=try StudioContract.hardware(resources:temp)
        precondition((hardware["memoryGB"] as? Double ?? 0)>0)
        func write(_ value:Any,_ name:String)throws->String {
            let file=temp.appendingPathComponent(name)
            try JSONSerialization.data(withJSONObject:value).write(to:file)
            return file.path
        }
        let small="mlx:qwen3.5-4b:4bit",medium="mlx:qwen3.5-9b:4bit"
        let review=try write(["config":["model":small,"aiAutoFix":true]],"review.json")
        let submission=try write(["review":review,"settings":["aiRepairModel":medium]],"submission.json")
        let effective=WorkerModelSelection.effective(["submission":submission],action:"render-project")
        precondition(effective["model"] as? String==small)
        precondition(WorkerModelSelection.repairModel(effective)==medium)
        precondition(WorkerModelSelection.repairModel(["model":small])==small)
        precondition(WorkerModelSelection.repairModel([:])==nil)
        precondition(simple.settings()["aiRepairModel"]==nil,"Basic must inherit the frozen text-model selection, not force 35B")
        print("PASS Swift ↔ Rust: catalog/order, mode parity, soft subtitles, track count, real RAM, frozen 4B/9B model selection")
    }
}
