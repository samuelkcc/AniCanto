import Foundation
import SQLite3

/// Metadata stays in Application Support; media and worker checkpoints remain files.
final class ProjectDatabase {
    private let root:URL
    private var db: OpaquePointer?
    private let transient = unsafeBitCast(-1, to: sqlite3_destructor_type.self)
    init(root: URL) throws {
        self.root=root
        try FileManager.default.createDirectory(at:root,withIntermediateDirectories:true)
        guard sqlite3_open_v2(root.appendingPathComponent("projects.sqlite3").path,&db,SQLITE_OPEN_READWRITE|SQLITE_OPEN_CREATE|SQLITE_OPEN_FULLMUTEX,nil)==SQLITE_OK else {throw AppFailure(message:"未能開啟影片資料庫。")}
        sqlite3_busy_timeout(db,15000)
        try execute("PRAGMA journal_mode=WAL")
        try execute("CREATE TABLE IF NOT EXISTS projects(review TEXT PRIMARY KEY,video TEXT NOT NULL,status TEXT NOT NULL,updated REAL NOT NULL)")
        try execute("CREATE TABLE IF NOT EXISTS documents(path TEXT PRIMARY KEY,project TEXT NOT NULL,kind TEXT NOT NULL,payload TEXT NOT NULL,updated REAL NOT NULL)")
        try execute("CREATE TABLE IF NOT EXISTS outputs(path TEXT PRIMARY KEY,project TEXT NOT NULL,status TEXT NOT NULL,updated REAL NOT NULL)")
        try execute("CREATE TABLE IF NOT EXISTS removed_outputs(path TEXT PRIMARY KEY,removed REAL NOT NULL)")
    }
    deinit {sqlite3_close(db)}
    private func statement(_ sql:String,_ values:[String]) throws -> OpaquePointer {
        var query:OpaquePointer?
        guard sqlite3_prepare_v2(db,sql,-1,&query,nil)==SQLITE_OK,let query else {throw failure()}
        for (i,value) in values.enumerated() {sqlite3_bind_text(query,Int32(i+1),value,-1,transient)}
        return query
    }
    private func failure() -> AppFailure {AppFailure(message:"影片資料庫："+String(cString:sqlite3_errmsg(db)))}
    func execute(_ sql:String,_ values:[String]=[]) throws {
        let query=try statement(sql,values);defer {sqlite3_finalize(query)}
        var code=sqlite3_step(query)
        while code==SQLITE_ROW {code=sqlite3_step(query)}
        guard code==SQLITE_DONE else {throw failure()}
    }
    func rows(_ sql:String,_ values:[String]=[]) throws -> [[String]] {
        let query=try statement(sql,values);defer {sqlite3_finalize(query)}
        var result:[[String]]=[]
        while true {
            let code=sqlite3_step(query)
            if code==SQLITE_DONE {return result}
            guard code==SQLITE_ROW else {throw failure()}
            result.append((0..<sqlite3_column_count(query)).map {sqlite3_column_text(query,$0).map {String(cString:$0)} ?? ""})
        }
    }
    func put(_ url:URL,project:String,kind:String,data:Data) throws {
        guard let text=String(data:data,encoding:.utf8) else {throw AppFailure(message:"編輯資料編碼無效。")}
        try execute("INSERT OR REPLACE INTO documents VALUES(?,?,?,?,?)",[url.path,project,kind,text,String(Date().timeIntervalSince1970)])
    }
    func data(_ url:URL) throws -> Data? {
        try rows("SELECT payload FROM documents WHERE path=?",[url.path]).first?.first?.data(using:.utf8)
    }
    func sync(review:URL,output:URL?=nil,status:String?=nil) throws {
        let data=try Data(contentsOf:review)
        guard let obj=try JSONSerialization.jsonObject(with:data) as? [String:Any],let cfg=obj["config"] as? [String:Any],let video=cfg["video"] as? String else {return}
        let state=status ?? obj["status"] as? String ?? "review"
        try execute("BEGIN IMMEDIATE")
        do {
            try execute("INSERT OR REPLACE INTO projects VALUES(?,?,?,?)",[review.path,video,state,String(Date().timeIntervalSince1970)])
            try put(review,project:review.path,kind:"review.json",data:data)
            if let output,FileManager.default.fileExists(atPath:output.path),try !isRemoved(output) {
                try execute("INSERT OR REPLACE INTO outputs VALUES(?,?,?,?)",[output.resolvingSymlinksInPath().standardizedFileURL.path,review.path,state,String(Date().timeIntervalSince1970)])
            }
            try execute("COMMIT")
        } catch {try? execute("ROLLBACK");throw error}
        if let output,output.deletingLastPathComponent() != review.deletingLastPathComponent() {try archiveSidecars(output)}
    }
    private func archiveSidecars(_ output:URL) throws {
        guard OutputStore.isOutputName(output.lastPathComponent) else{return}
        var suffixes=[".report.json",".validation.json",".nonverbal-report.json",".srt"]
        for engine in ["cosyvoice3","gpt-sovits","qwen-tts","en-cosyvoice3","en-gpt-sovits","en-qwen-tts"] {
            suffixes += ["validation.json","timing.json","nonverbal-report.json"].map {"."+engine+"."+$0}
            suffixes += ["yue","english","dual","original","original-yue","original-english"].map {"."+engine+"."+$0+".srt"}
        }
        let archive=root.appendingPathComponent("legacy-export-sidecars")
        for suffix in suffixes {
            let source=output.deletingLastPathComponent().appendingPathComponent(output.deletingPathExtension().lastPathComponent+suffix)
            guard FileManager.default.fileExists(atPath:source.path),let values=try? source.resourceValues(forKeys:[.isRegularFileKey,.isSymbolicLinkKey]),values.isRegularFile==true,values.isSymbolicLink != true else {continue}
            try FileManager.default.createDirectory(at:archive,withIntermediateDirectories:true)
            let target=archive.appendingPathComponent(UUID().uuidString+"-"+source.lastPathComponent)
            let bytes=try Data(contentsOf:source);try bytes.write(to:target,options:.atomic)
            guard try Data(contentsOf:target)==bytes else {throw AppFailure(message:"輸出報告搬移驗證失敗，已保留原檔。")}
            try execute("INSERT OR REPLACE INTO documents VALUES(?,?,?,?,?)",[source.path,"", "legacy-export-sidecar",target.path,String(Date().timeIntervalSince1970)])
            try FileManager.default.removeItem(at:source)
        }
    }
    func isRemoved(_ output:URL) throws -> Bool {try !rows("SELECT path FROM removed_outputs WHERE path=?",[output.resolvingSymlinksInPath().standardizedFileURL.path]).isEmpty}
    func removeOutput(_ output:URL) throws {
        try execute("BEGIN IMMEDIATE")
        do {
            try execute("DELETE FROM outputs WHERE path=?",[output.resolvingSymlinksInPath().standardizedFileURL.path])
            try execute("INSERT OR REPLACE INTO removed_outputs VALUES(?,?)",[output.resolvingSymlinksInPath().standardizedFileURL.path,String(Date().timeIntervalSince1970)])
            try execute("COMMIT")
        } catch {try? execute("ROLLBACK");throw error}
    }
    func removeProject(_ review:URL,keepExportedOutputs:Bool=false) throws {
        try execute("BEGIN IMMEDIATE")
        do {
            try execute("DELETE FROM documents WHERE project=?",[review.path])
            if keepExportedOutputs {
                for row in try rows("SELECT path FROM outputs WHERE project=?",[review.path]) {
                    guard let path=row.first else{continue}
                    if path.hasPrefix(review.deletingLastPathComponent().path+"/") {try execute("DELETE FROM outputs WHERE path=?",[path])}
                    else {try execute("UPDATE outputs SET project='' WHERE path=?",[path])}
                }
            } else {try execute("DELETE FROM outputs WHERE project=?",[review.path])}
            if !(try rows("SELECT name FROM sqlite_master WHERE type='table' AND name='issues'")).isEmpty {try execute("DELETE FROM issues WHERE project=?",[review.path])}
            try execute("DELETE FROM projects WHERE review=?",[review.path])
            try execute("COMMIT")
        } catch {try? execute("ROLLBACK");throw error}
    }
}
