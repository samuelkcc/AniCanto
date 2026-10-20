import Foundation

extension Engine {
    /// Shared preflight -> existing resumable installers -> verified selection commit.
    /// Failed/interrupted downloads do not change the user's current production defaults.
    func deployFirstRun(_ plan:[String:Any]) throws -> [String:String] {
        guard let voiceEngine=plan["engine"] as? String,plan["canDeployModels"] as? Bool==true,
              let roles=plan["roles"] as? [String:String],let downloads=plan["downloads"] as? [[String:Any]] else {
            throw AppFailure(message:"The deployment plan has unresolved hardware or model requirements.")
        }
        let current=try firstRunModelPlan(engine:plan["requestedEngine"] as? String ?? voiceEngine,requested:plan["requestedModels"] as? [String:String] ?? [:])
        guard current["canDeployModels"] as? Bool==true,current["engine"] as? String==voiceEngine,(current["roles"] as? [String:String])==roles else {
            throw AppFailure(message:"Hardware or model choices changed. Refresh the deployment plan.")
        }
        let options=try downloads.map {row throws -> ModelOption in
            guard let id=row["id"] as? String,let option=ModelOption.all.first(where:{$0.id==id}),option.revision==row["revision"] as? String else {throw AppFailure(message:"The model catalog changed. Refresh the deployment plan.")}
            return option
        }
        guard Set(options.map(\.id))==Set(roles.values) else {throw AppFailure(message:"Incomplete deployment plan.")}
        try FileManager.default.createDirectory(at:root,withIntermediateDirectories:true)
        let journal=root.appendingPathComponent("first-run-deployment.json")
        var complete:[String]=[]
        func save(_ status:String,_ active:String) throws {
            try JSONSerialization.data(withJSONObject:["schemaVersion":1,"status":status,"active":active,"completed":complete,"plan":plan],options:[.prettyPrinted,.sortedKeys]).write(to:journal,options:.atomic)
        }
        try save("running","runtime")
        do {
            if !lightweightPackage && !runtimeReady {try installRuntime()}
            try prepareFirstRunRuntimes(engine:voiceEngine)
            for option in options {
                try checkCancellation();try save("running",option.id)
                if option.ready(root) || option.ready(resources) {
                    event("沿用模型",option.title+" · 已安裝，毋須重新下載。")
                    complete.append(option.id);continue
                }
                event("部署模型",option.title)
                try deployOption(option)
                guard option.ready(root) else {throw AppFailure(message:"Model verification failed: "+option.id)}
                complete.append(option.id)
            }
            // Files alone do not prove the runtime loaded this model. Check the
            // primary recognition and voice receipts after all shared installers
            // finish; a secondary Whisper variant can overwrite the global receipt.
            for role in ["asr","speech","voice"] {
                guard let id=roles[role],let option=options.first(where:{$0.id==id}) else {throw AppFailure(message:"Missing required model in deployment plan.")}
                if !deploymentReceiptReady(option) {
                    try checkCancellation();try save("running",id)
                    event("核對模型",option.title+" · 驗證載入並恢復部署記錄。")
                    try deployOption(option)
                    guard option.ready(root),deploymentReceiptReady(option) else {throw AppFailure(message:"Model deployment verification failed: "+id)}
                }
            }
            for component in ["separator","speakers"] {
                if component=="separator" ? separatorReady:speakersReady {complete.append(component);continue}
                try checkCancellation();try save("running",component);try installDubbing(component);complete.append(component)
            }
            guard runtimeReady,separatorReady,speakersReady else {throw AppFailure(message:"A required runtime is not ready.")}
            var selections=roles
            selections.removeValue(forKey:"voice");selections[voiceEngine]=roles["voice"]
            try selectVariants(selections)
            try save("complete","")
            return selections
        } catch {
            try? save("incomplete",error.localizedDescription)
            throw error
        }
    }

    func deploymentReceiptReady(_ option:ModelOption)->Bool {
        switch option.category {
        case "asr":return readyVariantMarker("asr-ready.json",option.id)
        case "speech":return readyVariantMarker("speech-ready.json",option.id)
        case "voice":
            switch option.engine {
            case "drama3":return readyVariantMarker("drama3-ready.json",option.id)
            case "voxcpm2","wsyue":return readyVariantMarker(option.engine+"-ready.json",option.id) && FileManager.default.fileExists(atPath:root.appendingPathComponent("local-tts-ready.json").path)
            case "gpt-sovits","gpt-sovits-v2","gpt-sovits-v3":return readyMarkerValue("gsv-"+option.id+"-ready.json","version",option.id) && FileManager.default.fileExists(atPath:root.appendingPathComponent("gsv-ready.json").path)
            case "cosyvoice3":return readyVariantMarker("cosy-ready.json",option.id)
            default:return false
            }
        default:return true
        }
    }

    private func prepareFirstRunRuntimes(engine:String) throws {
        if lightweightPackage {
            for name in requiredMacRuntimes(engine:engine) {try checkCancellation();try ensureMacRuntime(name)}
            return
        }
        // A freshly downloaded application may not contain the development machine's runtimes.
        // Install only into application data; never modify a signed bundled environment.
        do {try run(python,["-c","import faster_whisper"])}
        catch {
            guard !python.path.hasPrefix(resources.path) else {throw error}
            try installPythonPackages(python,["install","faster-whisper==1.2.1"])
            try run(python,["-c","import faster_whisper"])
        }
        let text=runtimePython("text-runtime")
        let probe=["-c","import mlx.core, mlx_lm, mlx_vlm; import mlx_lm.models.qwen3_5_moe"]
        if FileManager.default.isExecutableFile(atPath:text.path),(try? run(text,probe)) != nil {return}
        guard !text.path.hasPrefix(resources.path) else {throw AppFailure(message:"The bundled text runtime is incomplete. Repair the application package.")}
        if !FileManager.default.isExecutableFile(atPath:text.path) {
            try ensurePythonEnvironment("text-runtime")
        }
        try installPythonPackages(text,["install","-r",resources.appendingPathComponent("visual-requirements.lock").path])
        try run(text,probe)
    }
}

extension AppModel {
    /// UI-independent one-click action; Welcome can show the plan without duplicating policy.
    func deployFirstRun(_ plan:[String:Any]) {
        guard !busy else{return}
        let e=engine
        task("部署模型") {
            let selected=try e.deployFirstRun(plan)
            Task { @MainActor in
                if let id=selected["text"] {self.selectedModel=id}
                if let voice=plan["engine"] as? String,let id=selected[voice] {
                    self.setVoiceModel(voice,id);self.ttsBackend=voice;self.reviewBackend=voice;self.extraEngines=[]
                    if self.projectEditor.document != nil {
                        self.projectEditor.productionSelection(self).engines=[voice]
                        self.projectEditor.previewEngine=voice
                    }
                }
                self.separateBackground=true;self.autoSpeakers=true
                self.roleAnalysisMode=self.visualRoleAnalysisEnabled ? "audiovisual":"audio"
                self.saveStudioPreset()
                self.refresh()
            }
        }
    }
}
