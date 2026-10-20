import Foundation

/// Requests are immutable Data values. Reuse their projection across UI reads;
/// comparing the bounded cache cannot expose a stale projection after an edit.
@MainActor enum WorkspaceRequestCache {
    private static var rows:[(Data,[String:Any])]=[]
    static func decode(_ data:Data)->[String:Any]? {
        if let row=rows.first(where:{$0.0==data}) {return row.1}
        guard let value=try? JSONSerialization.jsonObject(with:data) as? [String:Any] else{return nil}
        rows.insert((data,value),at:0)
        if rows.count>8 {rows.removeLast()}
        return value
    }
}
