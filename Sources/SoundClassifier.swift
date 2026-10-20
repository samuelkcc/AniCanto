import Foundation
import SoundAnalysis
import CoreMedia

private final class OpeningSoundObserver: NSObject, SNResultsObserving {
    var rows: [[String: Double]] = []
    var failure: Error?
    func request(_ request: SNRequest, didProduce result: SNResult) {
        guard let result = result as? SNClassificationResult else { return }
        var row = ["start": CMTimeGetSeconds(result.timeRange.start), "duration": CMTimeGetSeconds(result.timeRange.duration)]
        for key in ["music", "singing", "choir_singing", "speech", "rapping", "laughter", "baby_laughter", "belly_laugh", "crying_sobbing", "sigh", "breathing", "gasp", "screaming", "shout", "yell"] {
            row[key] = result.classification(forIdentifier: key)?.confidence ?? 0
        }
        rows.append(row)
    }
    func request(_ request: SNRequest, didFailWithError error: Error) { failure = error }
    func requestDidComplete(_ request: SNRequest) {}
}

func classifyOpeningAudio(_ path: String, detailed: Bool = false) throws {
    let observer = OpeningSoundObserver()
    let request = try SNClassifySoundRequest(classifierIdentifier: .version1)
    if detailed { request.windowDuration = CMTime(seconds: 1, preferredTimescale: 48000) }
    request.overlapFactor = 0.5
    let analyzer = try SNAudioFileAnalyzer(url: URL(fileURLWithPath: path))
    try analyzer.add(request, withObserver: observer)
    analyzer.analyze()
    if let error = observer.failure { throw error }
    FileHandle.standardOutput.write(try JSONSerialization.data(withJSONObject: observer.rows))
}
