import AppKit
let folder = URL(fileURLWithPath: CommandLine.arguments[1])
let captions = ["你好，歡迎試用廣東話配音。", "所有處理都喺你部電腦完成。", "試完之後，可以加入自己嘅動畫。"]
for (i, caption) in captions.enumerated() {
    let size = NSSize(width: 960, height: 540)
    let image = NSImage(size: size)
    image.lockFocus()
    NSColor.black.withAlphaComponent(0.88).setFill()
    NSBezierPath(roundedRect: NSRect(x: 50, y: 24, width: 860, height: 80), xRadius: 12, yRadius: 12).fill()
    let paragraph = NSMutableParagraphStyle(); paragraph.alignment = .center
    let font = NSFont(name: "PingFang TC", size: 32) ?? NSFont.systemFont(ofSize: 32)
    (caption as NSString).draw(in: NSRect(x: 65, y: 42, width: 830, height: 44), withAttributes: [.font:font, .foregroundColor:NSColor.white, .paragraphStyle:paragraph])
    image.unlockFocus()
    let bitmap = NSBitmapImageRep(data: image.tiffRepresentation!)!
    try bitmap.representation(using: .png, properties: [:])!.write(to: folder.appendingPathComponent("caption-\(i).png"))
}
