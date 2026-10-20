import Foundation
import Darwin

@main struct EngineLifecycleTests {
    static func main() throws {
        runManagedToolIfNeeded()
        let mode = CommandLine.arguments[1]
        let e = Engine(port: Int(CommandLine.arguments[2])!)
        if mode == "reuse" {
            try e.startServer()
            precondition(e.availableModels().contains("qwen3:14b"))
            try e.startServer()
            e.shutdown()
            precondition(e.ollamaIsReady(), "must not terminate another owner's service")
            print("PASS: existing Ollama reused, Qwen3 14B available, shared service preserved")
        } else if mode == "owned" {
            try e.startServer()
            try e.startServer()
            try e.request("/api/generate", timeout:120, body:["model":"qwen3:14b", "prompt":"只答好", "think":false, "stream":false, "keep_alive":"5m", "options":["num_predict":1]])
            let ps = try JSONSerialization.jsonObject(with:e.request("/api/ps")) as! [String:Any]
            precondition(!(ps["models"] as! [Any]).isEmpty)
            e.shutdown()
            precondition(!e.ollamaIsReady(), "owned server must stop")
            print("PASS: owned Ollama and loaded Qwen3 14B stopped")
        } else if mode == "worker" {
            let done=DispatchSemaphore(value:0)
            DispatchQueue.global().async {
                defer { done.signal() }
                do { try e.run(URL(fileURLWithPath:"/bin/sh"),["-c","trap '' TERM; /bin/sleep 60 & echo $! > child.pid; echo $$ > parent.pid; wait"]); fatalError("worker unexpectedly completed") }
                catch { print("worker cancelled") }
            }
            let childFile=e.root.appendingPathComponent("child.pid")
            let deadline=Date().addingTimeInterval(10)
            while !FileManager.default.fileExists(atPath:childFile.path) && Date()<deadline { Thread.sleep(forTimeInterval:0.05) }
            let child=Int32(try String(contentsOf:childFile).trimmingCharacters(in:.whitespacesAndNewlines))!
            let parent=Int32(try String(contentsOf:e.root.appendingPathComponent("parent.pid")).trimmingCharacters(in:.whitespacesAndNewlines))!
            e.shutdown()
            precondition(done.wait(timeout:.now()+5) == .success)
            Thread.sleep(forTimeInterval:0.2)
            precondition(kill(parent,0) != 0 && kill(child,0) != 0, "all worker descendants must stop")
            print("PASS: uncooperative worker and child stopped on shutdown")
        } else if mode == "reject" {
            precondition(!e.ollamaIsReady(), "an error response must not count as readiness")
            do { try e.request("/api/tags"); fatalError("HTTP error accepted") }
            catch { print("PASS: invalid/error HTTP service rejected") }
        }
    }
}
