import Foundation

struct PreviewCommandQueueTests {
    static func run() throws {
        let queue=PreviewCommandQueue()
        let started=DispatchSemaphore(value:0),release=DispatchSemaphore(value:0),done=DispatchSemaphore(value:0)
        let lock=NSLock();var results:[Int]=[]
        queue.always {started.signal();_ = release.wait(timeout:.now()+5)}
        precondition(started.wait(timeout:.now()+2) == .success)
        let began=Date()
        for i in 0..<1000 {queue.submit(key:"seek") {_ in lock.lock();results.append(i);lock.unlock()}}
        precondition(Date().timeIntervalSince(began)<0.1,"Submitting a seek waited for the decoder")
        queue.always {done.signal()};release.signal()
        precondition(done.wait(timeout:.now()+2) == .success)
        precondition(results==[999],"Rapid seeks must coalesce to the latest target")
        let started2=DispatchSemaphore(value:0),release2=DispatchSemaphore(value:0),done2=DispatchSemaphore(value:0)
        queue.always {started2.signal();_ = release2.wait(timeout:.now()+5)}
        precondition(started2.wait(timeout:.now()+2) == .success)
        queue.submit(key:"seek") {_ in preconditionFailure("Stale source command executed")}
        queue.invalidate()
        queue.submit(key:"seek") {_ in lock.lock();results.append(2000);lock.unlock()}
        queue.always {done2.signal()};release2.signal()
        precondition(done2.wait(timeout:.now()+2) == .success && results==[999,2000])
        print("PASS blocked decoder does not block caller; 1,000 seeks coalesced; source invalidation preserves latest target")
    }
}
