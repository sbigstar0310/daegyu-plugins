// winrec2: capture one window (owner + title) via ScreenCaptureKit and write raw BGRA frames
// to stdout at a constant frame rate (latest frame repeated). Pipe into ffmpeg for encoding.
// Usage: winrec2 <owner> <title> <W> <H> <fps>   (W,H even; content is scaled to fit)
//        winrec2 --size <owner> <title> <W>      prints "W H" (even) matching the window's aspect
import Foundation
import ScreenCaptureKit
import CoreMedia
import CoreVideo
import AppKit
_ = NSApplication.shared  // init window-server connection (avoids CGS_REQUIRE_INIT in CLI)

let a = CommandLine.arguments
if a.count == 5 && a[1] == "--size" {
    // Query only (no capture stream): print an even W H with the window's aspect ratio.
    Task {
        let content = try? await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: false)
        guard let win = content?.windows.first(where: {
            $0.owningApplication?.applicationName == a[2] && $0.title == a[3]
        }), win.frame.width > 0, let w0 = Int(a[4]) else { exit(1) }
        let w = w0 - w0 % 2
        var h = Int((Double(w) * win.frame.height / win.frame.width).rounded())
        h -= h % 2
        print(w, h); exit(0)
    }
    dispatchMain()
}
let argW = a.count == 6 ? Int(a[3]) ?? 0 : 0
let argH = a.count == 6 ? Int(a[4]) ?? 0 : 0
let fps = a.count == 6 ? Int(a[5]) ?? 0 : 0
if argW <= 0 || argH <= 0 || fps <= 0 {
    FileHandle.standardError.write("usage: winrec2 <owner> <title> <W> <H> <fps>\n".data(using: .utf8)!); exit(2)
}
signal(SIGPIPE, SIG_IGN)

final class Cap: NSObject, SCStreamOutput, SCStreamDelegate {
    var stream: SCStream!
    var W = 0, H = 0
    var frame: Data
    let lock = NSLock()
    let q = DispatchQueue(label: "cap")
    let out = FileHandle.standardOutput
    var timer: DispatchSourceTimer?

    override init() { frame = Data() }

    func start() async throws {
        let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: false)
        guard let win = content.windows.first(where: {
            $0.owningApplication?.applicationName == a[1] && $0.title == a[2]
        }) else { throw NSError(domain: "winrec2", code: 1, userInfo: [NSLocalizedDescriptionKey: "window not found"]) }
        W = argW; H = argH
        frame = Data(count: W * H * 4)  // black until first frame
        let cfg = SCStreamConfiguration()
        cfg.width = W; cfg.height = H
        cfg.pixelFormat = kCVPixelFormatType_32BGRA
        cfg.minimumFrameInterval = CMTime(value: 1, timescale: CMTimeScale(fps))
        cfg.showsCursor = false
        cfg.scalesToFit = true
        stream = SCStream(filter: SCContentFilter(desktopIndependentWindow: win), configuration: cfg, delegate: self)
        try stream.addStreamOutput(self, type: .screen, sampleHandlerQueue: q)
        try await stream.startCapture()
        FileHandle.standardError.write("\(W)x\(H)\n".data(using: .utf8)!)

        let t = DispatchSource.makeTimerSource(queue: DispatchQueue(label: "emit"))
        t.schedule(deadline: .now(), repeating: 1.0 / Double(fps), leeway: .milliseconds(2))
        t.setEventHandler { [unowned self] in
            lock.lock(); let f = frame; lock.unlock()
            do { try out.write(contentsOf: f) } catch { exit(0) }  // ffmpeg closed the pipe
        }
        t.resume(); timer = t
    }

    func stream(_ s: SCStream, didOutputSampleBuffer sb: CMSampleBuffer, of type: SCStreamOutputType) {
        guard type == .screen, let pb = sb.imageBuffer else { return }
        CVPixelBufferLockBaseAddress(pb, .readOnly); defer { CVPixelBufferUnlockBaseAddress(pb, .readOnly) }
        let pw = CVPixelBufferGetWidth(pb), ph = CVPixelBufferGetHeight(pb)
        guard let base = CVPixelBufferGetBaseAddress(pb) else { return }
        let stride = CVPixelBufferGetBytesPerRow(pb)
        var d = Data(count: W * H * 4)  // letterbox if SCK hands back a different size
        d.withUnsafeMutableBytes { dst in
            let rows = min(ph, H), cols = min(pw, W) * 4
            for r in 0..<rows { memcpy(dst.baseAddress! + r * W * 4, base + r * stride, cols) }
        }
        lock.lock(); frame = d; lock.unlock()
    }

    func stream(_ s: SCStream, didStopWithError error: Error) {
        FileHandle.standardError.write("stream stopped: \(error)\n".data(using: .utf8)!); exit(3)
    }
}

let cap = Cap()
var sigs: [DispatchSourceSignal] = []
for sig in [SIGINT, SIGTERM] {
    signal(sig, SIG_IGN)
    let s = DispatchSource.makeSignalSource(signal: sig, queue: .global())
    s.setEventHandler { exit(0) }
    s.resume(); sigs.append(s)
}
Task {
    do { try await cap.start() }
    catch { FileHandle.standardError.write("error: \(error)\n".data(using: .utf8)!); exit(1) }
}
dispatchMain()
