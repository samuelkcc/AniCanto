import Foundation

extension Engine {
    private static let runtimeCatalog:[String:[String:Any]] = {
        guard let url=Bundle.main.url(forResource:"mac-runtime-identities",withExtension:"json"),let data=try? Data(contentsOf:url) else{return [:]}
        return (try? JSONSerialization.jsonObject(with:data) as? [String:[String:Any]]) ?? [:]
    }()
    var lightweightPackage:Bool {FileManager.default.fileExists(atPath:resources.appendingPathComponent("LIGHTWEIGHT-PACKAGE.json").path)}
    func runtimeVerified(_ name:String)->Bool {
        guard FileManager.default.isExecutableFile(atPath:runtimePython(name).path) else{return false}
        if !lightweightPackage {return true}
        guard let expected=Self.runtimeCatalog[name]?["identity"] as? String,
              let data=try? Data(contentsOf:root.appendingPathComponent("runtime-receipts/\(name).json")),
              let row=try? JSONSerialization.jsonObject(with:data) as? [String:Any] else{return false}
        return row["identity"] as? String==expected && row["importsPassed"] as? Bool==true
    }
    func ensurePythonEnvironment(_ name:String) throws {
        guard !name.isEmpty, name.range(of:"^[a-z][a-z0-9-]*$",options:.regularExpression) != nil else {throw AppFailure(message:"Invalid runtime name")}
        let target=root.appendingPathComponent("\(name)/bin/python3")
        if FileManager.default.isExecutableFile(atPath:target.path) {return}
        try run(URL(fileURLWithPath:"/bin/sh"),[resources.appendingPathComponent("python-bootstrap.sh").path,root.path,resources.path],protocolOutput:true)
        let data=try Data(contentsOf:resources.appendingPathComponent("python-installer.json"))
        guard let catalog=try JSONSerialization.jsonObject(with:data) as? [String:Any],
              let platforms=catalog["platforms"] as? [String:[String:Any]],let row=platforms["macos-arm64"],
              let directory=row["directory"] as? String,let executable=row["executable"] as? String,
              directory.range(of:"^cpython-3\\.11\\.[0-9]+-aarch64-apple-darwin$",options:.regularExpression) != nil,executable=="bin/python3"
        else {throw AppFailure(message:"Invalid private Python manifest")}
        let base=root.appendingPathComponent("python/\(directory)/\(executable)")
        try run(base,[resources.appendingPathComponent("runtime_installer.py").path,root.path,"env",name],protocolOutput:true)
    }
    func installPythonPackages(_ target:URL,_ args:[String]) throws {
        if !FileManager.default.isExecutableFile(atPath:python.path) {try ensurePythonEnvironment("runtime")}
        try run(python,[resources.appendingPathComponent("runtime_installer.py").path,root.path,"pip",target.path]+args)
    }
    func ensureMacRuntime(_ name:String) throws {
        if !lightweightPackage {return}
        if !FileManager.default.isExecutableFile(atPath:python.path) {
            event("執行環境",L("下載 App 專用 Python 3.11，儲存於 Application Support。"))
            try ensurePythonEnvironment("runtime")
        }
        try run(python,[resources.appendingPathComponent("mac_runtime.py").path,root.path,name],protocolOutput:true)
        guard runtimeVerified(name) else {throw AppFailure(message:"Runtime verification did not complete: "+name)}
    }
    func requiredMacRuntimes(engine:String)->[String] {
        let voice=["drama3":"text-runtime","gpt-sovits-v2":"gsv-runtime","gpt-sovits":"gsv-runtime","cosyvoice3":"cosy-runtime","voxcpm2":"local-tts-runtime","wsyue":"local-tts-runtime"][engine] ?? "text-runtime"
        return Array(Set(["runtime","text-runtime","asr-runtime","separator-runtime",voice])).sorted()
    }
    func runtimeInventory(engine:String)->[[String:Any]] {
        requiredMacRuntimes(engine:engine).map {name in
            var ready=runtimeVerified(name)
            if ready && lightweightPackage {
                let p=Process();p.executableURL=python
                p.arguments=[resources.appendingPathComponent("mac_runtime.py").path,"--check",root.path,name]
                p.environment=environment();p.standardOutput=FileHandle.nullDevice;p.standardError=FileHandle.nullDevice
                do {try p.run();p.waitUntilExit();ready=p.terminationStatus==0} catch {ready=false}
            }
            return ["name":name,"ready":ready,"destination":root.appendingPathComponent(name).path]
        }
    }
}
