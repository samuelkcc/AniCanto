import Foundation
import Metal

/// Generated data is shared with the Rust policy core and Python workers.
enum StudioContract {
    struct Voice:Decodable {let id:String,title:String,shortTitle:String,kind:String,memory:String,download:String;let languages:[String]}
    struct Catalog:Decodable {let schemaVersion:Int,defaultEngine:String;let engines:[Voice]}
    static let catalog = try! JSONDecoder().decode(Catalog.self,from:StudioContractCatalog.data)
    static var rows:[Voice] {catalog.engines}
    static func call(_ request:[String:Any],resources:URL) throws -> [String:Any] {
        if request["operation"] as? String != "catalog" {
            let bundled=try call(["operation":"catalog"],resources:resources)
            let expected=try JSONSerialization.jsonObject(with:StudioContractCatalog.data) as! [String:Any]
            guard let actual=bundled["catalog"] as? [String:Any],NSDictionary(dictionary:actual).isEqual(to:expected) else {
                throw AppFailure(message:"AniCanto core/catalog version mismatch. Rebuild or repair the app package.")
            }
        }
        let executable=resources.appendingPathComponent("bin/anicanto-core")
        guard FileManager.default.isExecutableFile(atPath:executable.path) else {throw AppFailure(message:"AniCanto shared core is missing. Rebuild or repair the app package.")}
        let process=Process(),input=Pipe(),output=Pipe()
        process.executableURL=executable;process.standardInput=input;process.standardOutput=output;process.standardError=FileHandle.nullDevice
        let data=try JSONSerialization.data(withJSONObject:request,options:.sortedKeys)
        try process.run()
        do {try input.fileHandleForWriting.write(contentsOf:data);try input.fileHandleForWriting.close()}
        catch {process.terminate();throw error}
        let response=output.fileHandleForReading.readDataToEndOfFile();process.waitUntilExit()
        guard let result=try JSONSerialization.jsonObject(with:response) as? [String:Any],process.terminationStatus==0,result["ok"] as? Bool==true,let value=result["result"] as? [String:Any] else {
            let result=(try? JSONSerialization.jsonObject(with:response)) as? [String:Any]
            throw AppFailure(message:result?["error"] as? String ?? "AniCanto shared core returned an invalid response.")
        }
        return value
    }
    static func hardware(resources:URL) throws -> [String:Any] {
        var info=try call(["operation":"hardware"],resources:resources)
        #if arch(arm64)
        if let device=MTLCreateSystemDefaultDevice() {
            info["backend"]="metal";info["acceleratorName"]=device.name
            info["acceleratorBudgetGB"]=Double(device.recommendedMaxWorkingSetSize)/1_073_741_824
        }
        #else
        info["backend"]="cpu"
        #endif
        return info
    }
}

extension Engine {
    /// Read-only first-run API. The welcome UI must show blockers before offering downloads.
    func firstRunModelPlan(engine:String="drama3",requested:[String:String]=[:]) throws -> [String:Any] {
        let data=try Data(contentsOf:resources.appendingPathComponent("model-options.json"))
        let models=try JSONSerialization.jsonObject(with:data)
        let inventory=ModelOption.all.filter {$0.ready(root) || $0.ready(resources)}
        let installed=inventory.map(\.id)
        let selected=(try? Data(contentsOf:root.appendingPathComponent("model-selections.json"))).flatMap {try? JSONSerialization.jsonObject(with:$0) as? [String:String]} ?? [:]
        var plan=try StudioContract.call(["operation":"deployment","hardware":StudioContract.hardware(resources:resources),"models":models,"engine":engine,"installedModels":installed,"selectedModels":selected,"requestedModels":requested,"singleModelPerCategory":true],resources:resources)
        plan["requestedModels"]=requested
        let rows=plan["downloads"] as? [[String:Any]] ?? []
        let runtimeRows=runtimeInventory(engine:plan["engine"] as? String ?? engine)
        let roles=plan["roles"] as? [String:String] ?? [:]
        let receiptsReady=["asr","speech","voice"].allSatisfy {role in
            guard let id=roles[role],let option=ModelOption.all.first(where:{$0.id==id}) else{return false}
            return deploymentReceiptReady(option)
        }
        let componentsReady=runtimeReady && separatorReady && speakersReady && receiptsReady && runtimeRows.allSatisfy {$0["ready"] as? Bool==true}
        plan["runtimeInventory"]=runtimeRows
        plan["setupReady"]=plan["canDeployModels"] as? Bool==true && !rows.isEmpty && rows.allSatisfy {$0["installed"] as? Bool==true} && componentsReady
        plan["existingInstallation"] = !installed.isEmpty
        plan["installedInventory"]=inventory.map {["id":$0.id,"title":$0.title,"precision":$0.precision,"bytes":$0.bytes] as [String:Any]}
        return plan
    }
    func productionPlan(_ settings:[String:Any]) throws -> [String:Any] {
        try StudioContract.call(["operation":"plan","settings":settings],resources:resources)
    }
}

enum WorkerModelSelection {
    /// Resolve the submitted snapshot, not whichever project/default the UI now shows.
    static func effective(_ config:[String:Any],action:String) -> [String:Any] {
        func read(_ path:String)->[String:Any] {guard let data=try? Data(contentsOf:URL(fileURLWithPath:path)) else{return [:]};return (try? JSONSerialization.jsonObject(with:data) as? [String:Any]) ?? [:]}
        var settings=config
        if let path=config["review"] as? String {settings=(read(path)["config"] as? [String:Any] ?? [:]).merging(config){_,new in new}}
        if let path=config["submission"] as? String {
            let draft=read(path)
            let base=(draft["review"] as? String).map {read($0)["config"] as? [String:Any] ?? [:]} ?? [:]
            settings=base.merging(config){_,new in new}.merging(draft["settings"] as? [String:Any] ?? [:]){_,new in new}
        }
        return settings
    }
    static func repairModel(_ settings:[String:Any]) -> String? {
        // An explicit frozen repair model remains reproducible. New jobs use the selected text model.
        for key in ["aiRepairModel","model"] {if let value=settings[key] as? String,!value.isEmpty {return value}}
        return nil
    }
}
