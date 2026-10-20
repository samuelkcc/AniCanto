import Foundation

/// Decoder calls may wait on input/video locks. No caller waits for this queue.
/// Source changes invalidate old commands; rapid seeks keep only the newest one.
final class PreviewCommandQueue {
    struct Ticket:Equatable {let generation:Int,key:String,revision:Int}
    private let queue:DispatchQueue
    private let lock=NSLock()
    private var generation=0
    private var revisions:[String:Int]=[:]
    init(label:String="AniCanto.preview-decoder",qos:DispatchQoS = .userInitiated) {queue=DispatchQueue(label:label,qos:qos)}
    func invalidate() {
        lock.lock();generation += 1;revisions.removeAll();lock.unlock()
    }
    func current(_ ticket:Ticket)->Bool {
        lock.lock();defer {lock.unlock()}
        return ticket.generation==generation && (ticket.key.isEmpty || revisions[ticket.key]==ticket.revision)
    }
    @discardableResult func submit(key:String="",_ operation:@escaping (Ticket)->Void)->Ticket {
        lock.lock()
        let revision=(revisions[key] ?? 0)+1
        if !key.isEmpty {revisions[key]=revision}
        let ticket=Ticket(generation:generation,key:key,revision:revision)
        lock.unlock()
        queue.async { [self] in if current(ticket) {operation(ticket)} }
        return ticket
    }
    func always(_ operation:@escaping ()->Void) {queue.async(execute:operation)}
    func finish(_ operation:@escaping ()->Void) {invalidate();always(operation)}
}
