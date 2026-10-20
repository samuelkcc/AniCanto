import AppKit
import CoreText

// Offline subtitle glyph rendering with the font shipped in the app. Images are
// composed by FFmpeg, so playback does not depend on the viewer's installed fonts.
func renderSubtitleImages(_ request: URL) throws {
    guard let object = try JSONSerialization.jsonObject(with:Data(contentsOf:request)) as? [String:Any],
          let folder = object["folder"] as? String, let rows=object["captions"] as? [[String:Any]],
          let width=object["width"] as? Int, let height=object["height"] as? Int,
          (160...8192).contains(width), (120...8192).contains(height) else { throw AppFailure(message:"字幕圖像設定無效。") }
    let fontURL=Bundle.main.resourceURL!.appendingPathComponent("vlc/fonts/NotoSansCJKtc-Regular.otf")
    guard let descriptors=CTFontManagerCreateFontDescriptorsFromURL(fontURL as CFURL) as? [CTFontDescriptor], let descriptor=descriptors.first else { throw AppFailure(message:"內置中文字型遺失，未產生方框字幕。") }
    let scale=object["fontSize"] as? Double ?? 0.043
    let bottom=object["bottom"] as? Double ?? 0.045
    guard scale.isFinite, bottom.isFinite, (0.015...0.12).contains(scale), (0...0.8).contains(bottom) else {throw AppFailure(message:"字幕位置或字體大小無效。") }
    let size=max(18,Double(height)*scale)
    let font=CTFontCreateWithFontDescriptor(descriptor,size,nil)
    let destination=URL(fileURLWithPath:folder);try FileManager.default.createDirectory(at:destination,withIntermediateDirectories:true)
    for (i,row) in rows.enumerated() {
        guard let text=row["text"] as? String else { throw AppFailure(message:"字幕文字格式無效。") }
        guard let context=CGContext(data:nil,width:width,height:height,bitsPerComponent:8,bytesPerRow:width*4,space:CGColorSpaceCreateDeviceRGB(),bitmapInfo:CGImageAlphaInfo.premultipliedLast.rawValue) else { throw AppFailure(message:"未能建立字幕圖像。") }
        if !text.isEmpty {
            let style=NSMutableParagraphStyle();style.alignment = .center;style.lineBreakMode = .byWordWrapping
            let attributes: [NSAttributedString.Key:Any] = [.font:font,.foregroundColor:NSColor.white,.strokeColor:NSColor.black,.strokeWidth: -3.5,.paragraphStyle:style]
            let string=NSAttributedString(string:text,attributes:attributes)
            let setter=CTFramesetterCreateWithAttributedString(string)
            let available=Double(width)*0.9
            let extent=CTFramesetterSuggestFrameSizeWithConstraints(setter,CFRange(location:0,length:string.length),nil,CGSize(width:available,height:Double(height)*0.8),nil)
            let box=CGRect(x:Double(width)*0.05,y:Double(height)*bottom,width:available,height:ceil(extent.height)+8)
            let frame=CTFramesetterCreateFrame(setter,CFRange(location:0,length:string.length),CGPath(rect:box,transform:nil),nil)
            let visible=CTFrameGetVisibleStringRange(frame)
            guard visible.length==string.length else { throw AppFailure(message:"字幕太長，未截斷文字；請分段或縮短字幕。") }
            context.setFillColor(CGColor(gray:0,alpha:0.55));context.fill(box.insetBy(dx:-8,dy:-4))
            CTFrameDraw(frame,context)
        }
        guard let image=context.makeImage(),let data=NSBitmapImageRep(cgImage:image).representation(using:.png,properties:[:]) else { throw AppFailure(message:"未能寫入字幕圖像。") }
        try data.write(to:destination.appendingPathComponent(String(format:"%05d.png",i)),options:.atomic)
    }
}
