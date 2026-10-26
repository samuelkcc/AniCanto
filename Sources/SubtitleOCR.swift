import Foundation
import Vision
import ImageIO
import CryptoKit

// Pure batch orchestration is injectable so error/retry/resume can be tested
// without fabricating an Apple Vision failure or running the UI.
func subtitleOCRRows(_ folder: URL, recognize: (URL, Int) throws -> [[String: Any]]) -> [[String: Any]] {
    let fm=FileManager.default
    let files=((try? fm.contentsOfDirectory(at:folder,includingPropertiesForKeys:nil)) ?? [])
        .filter { $0.pathExtension.lowercased()=="jpg" }.sorted {$0.lastPathComponent<$1.lastPathComponent}
    let cache=folder.appendingPathComponent("ocr-frame-cache",isDirectory:true)
    try? fm.createDirectory(at:cache,withIntermediateDirectories:true)
    let started=Date();var rows=[[String:Any]]();var failed=0;var retries=0;var reused=0
    func save(_ value:Any,_ path:URL) {
        if let data=try? JSONSerialization.data(withJSONObject:value,options:[.sortedKeys]) {try? data.write(to:path,options:.atomic)}
    }
    func progress() {save(["completed":rows.count,"total":files.count,"failed":failed,"retries":retries,"reused":reused,
                           "seconds":Date().timeIntervalSince(started),"backend":"Apple Vision"],folder.appendingPathComponent("ocr-progress.json"))}
    progress()
    for (i,file) in files.enumerated() {
        let row: [String:Any] = autoreleasepool {
            let key=(try? Data(contentsOf:file)).map {SHA256.hash(data:Data("vision-subtitle-2".utf8)+$0).map {String(format:"%02x",$0)}.joined()}
            let checkpoint=cache.appendingPathComponent((key ?? UUID().uuidString)+".json")
            if key != nil, let data=try? Data(contentsOf:checkpoint),let old=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],old["status"] as? String=="complete" {
                reused+=1;var result=old;result["index"]=i;return result
            }
            var errors=[String]()
            for attempt in 0..<2 {
                if attempt>0 {retries+=1}
                do {
                    let boxes=try recognize(file,attempt)
                    let result:[String:Any]=["index":i,"text":boxes.compactMap {$0["text"] as? String}.joined(separator:" "),"boxes":boxes,"status":"complete","attempts":attempt+1]
                    if key != nil {save(result,checkpoint)}
                    return result
                } catch {errors.append(String(reflecting:error))}
            }
            failed+=1
            return ["index":i,"text":"","boxes":[[String:Any]](),"status":"failed","attempts":2,"errors":errors,"file":file.lastPathComponent]
        }
        rows.append(row);progress()
    }
    save(rows.filter {$0["status"] as? String=="failed"},folder.appendingPathComponent("ocr-frame-errors.json"))
    return rows
}

func recognizeSubtitleFrame(_ file:URL,_ attempt:Int) throws -> [[String:Any]] {
    let request=VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages=["zh-Hant","zh-Hans","ja-JP","en-US"]
    request.usesLanguageCorrection=false
    request.regionOfInterest=CGRect(x:0,y:0,width:1,height:1)
    if attempt==0 {try VNImageRequestHandler(url:file).perform([request])}
    else {
        // A fresh decoded CGImage avoids retaining a failed URL reader state.
        guard let source=CGImageSourceCreateWithURL(file as CFURL,nil),let image=CGImageSourceCreateImageAtIndex(source,0,[kCGImageSourceShouldCache:false] as CFDictionary) else {throw CocoaError(.fileReadCorruptFile)}
        try VNImageRequestHandler(cgImage:image).perform([request])
    }
    return (request.results ?? []).sorted {
        let a=Int(($0.boundingBox.midY*20).rounded()),b=Int(($1.boundingBox.midY*20).rounded())
        return a==b ? $0.boundingBox.minX<$1.boundingBox.minX : a>b
    }.compactMap { observation in
        guard let best=observation.topCandidates(1).first,best.confidence>=0.10 else {return nil}
        let b=observation.boundingBox
        return ["text":best.string,"confidence":best.confidence,"x":b.minX,"y":1-b.maxY,"width":b.width,"height":b.height]
    }
}
