import Foundation
import SoundAnalysis
import CoreMedia

private let performanceLabels = ["music", "singing", "choir_singing", "speech", "rapping", "laughter", "baby_laughter", "belly_laugh", "crying_sobbing", "sigh", "breathing", "gasp", "screaming", "shout", "yell"]

private final class OpeningSoundObserver: NSObject, SNResultsObserving {
    var requireCompletePerformance = false
    var rows: [[String: Double]] = []
    var failure: Error?
    func request(_ request: SNRequest, didProduce result: SNResult) {
        guard let result = result as? SNClassificationResult else { return }
        var row = ["start": CMTimeGetSeconds(result.timeRange.start), "duration": CMTimeGetSeconds(result.timeRange.duration)]
        for key in performanceLabels {
            let classification = result.classification(forIdentifier: key)
            if requireCompletePerformance && classification == nil {
                failure = NSError(domain: "AniCanto.Performance", code: 1, userInfo: [NSLocalizedDescriptionKey: "Incomplete performance classification: \(key)"])
                return
            }
            row[key] = classification?.confidence ?? 0
        }
        rows.append(row)
    }
    func request(_ request: SNRequest, didFailWithError error: Error) { failure = error }
    func requestDidComplete(_ request: SNRequest) {}
}

func classifyOpeningAudio(_ path: String, detailed: Bool = false) throws {
    let observer = OpeningSoundObserver()
    observer.requireCompletePerformance = detailed
    let request = try SNClassifySoundRequest(classifierIdentifier: .version1)
    if detailed { request.windowDuration = CMTime(seconds: 1, preferredTimescale: 48000) }
    if detailed && !Set(performanceLabels).isSubset(of: Set(request.knownClassifications)) {
        throw NSError(domain: "AniCanto.Performance", code: 2, userInfo: [NSLocalizedDescriptionKey: "Unsupported performance taxonomy"])
    }
    request.overlapFactor = 0.5
    let analyzer = try SNAudioFileAnalyzer(url: URL(fileURLWithPath: path))
    try analyzer.add(request, withObserver: observer)
    analyzer.analyze()
    if let error = observer.failure { throw error }
    FileHandle.standardOutput.write(try JSONSerialization.data(withJSONObject: observer.rows))
}
