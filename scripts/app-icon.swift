import AppKit
// Package the original AniCanto illustration into standard macOS icon sizes.
let output=URL(fileURLWithPath:CommandLine.arguments[1])
let source=URL(fileURLWithPath:CommandLine.arguments.count>2 ? CommandLine.arguments[2] : "Resources/app-icon-art.png")
guard let image=NSImage(contentsOf:source) else {print("Missing icon source");exit(1)}
try FileManager.default.createDirectory(at:output,withIntermediateDirectories:true)
func render(_ pixels:Int)->Data {
    let rep=NSBitmapImageRep(bitmapDataPlanes:nil,pixelsWide:pixels,pixelsHigh:pixels,bitsPerSample:8,samplesPerPixel:4,hasAlpha:true,isPlanar:false,colorSpaceName:.deviceRGB,bytesPerRow:0,bitsPerPixel:0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current=NSGraphicsContext(bitmapImageRep:rep)
    NSGraphicsContext.current?.imageInterpolation = .high
    image.draw(in:NSRect(x:0,y:0,width:pixels,height:pixels))
    NSGraphicsContext.restoreGraphicsState()
    return rep.representation(using:.png,properties:[:])!
}
for size in [16,32,128,256,512] {
    try render(size).write(to:output.appendingPathComponent("icon_\(size)x\(size).png"))
    try render(size*2).write(to:output.appendingPathComponent("icon_\(size)x\(size)@2x.png"))
}
