import AppKit

@main struct PetAtlasTests {
    @MainActor static func main() throws {
        NSApplication.shared.setActivationPolicy(.prohibited)
        let root=URL(fileURLWithPath:CommandLine.arguments[1]),out=URL(fileURLWithPath:CommandLine.arguments[2])
        let themes=["studio","energy","ocean","ninja","retro","forest","future","mint","moonflower"]
        let sheet=NSImage(size:NSSize(width:12*140,height:9*155))
        sheet.lockFocus();NSColor(calibratedRed:0.94,green:0.94,blue:0.96,alpha:1).setFill();NSRect(x:0,y:0,width:1680,height:1395).fill();sheet.unlockFocus()
        var trimmed=0
        for (row,theme) in themes.enumerated() {
            let raw=NSImage(contentsOf:root.appendingPathComponent("pet-\(theme).png"))!.cgImage(forProposedRect:nil,context:nil,hints:nil)!
            let tiles=PetAtlas.tiles(raw);precondition(tiles.count==12,"No safe gutters: \(theme)")
            for pose in 0..<12 {
                let tile=tiles[pose],w=tile.width,h=tile.height
                let bounds=PetAtlas.subjectBounds(tile)!
                precondition(bounds.minX>=8 && bounds.minY>=8 && bounds.maxX<=CGFloat(w-8) && bounds.maxY<=CGFloat(h-8),"Pose crosses safe transparent gutter: \(theme) \(pose)")
                let clean=PetAtlas.frame(tile),cg=clean.cgImage(forProposedRect:nil,context:nil,hints:nil)!,rep=NSBitmapImageRep(cgImage:cg)
                let source=NSBitmapImageRep(cgImage:tile)
                var sourceOpaque=0,preserved=0,removed=0
                for y in 0..<h {for x in 0..<w {
                    let alpha=source.colorAt(x:x,y:y)!.alphaComponent
                    let new=rep.colorAt(x:min(rep.pixelsWide-1,x*rep.pixelsWide/w),y:min(rep.pixelsHigh-1,y*rep.pixelsHigh/h))!.alphaComponent
                    if alpha>0.1 {if bounds.contains(CGPoint(x:x,y:y)) {sourceOpaque+=1;if new>0.05 {preserved+=1}};if new<=0.05 {removed+=1}}
                }}
                precondition(Double(preserved)/Double(sourceOpaque)>0.98,"Subject clipped: \(theme) \(pose)")
                if removed>5 {trimmed+=1}
                if theme=="studio" && pose==5 {
                    precondition(bounds.minY>=5,"Previous-row fragments retained")
                    precondition(rep.colorAt(x:140*rep.pixelsWide/w,y:0)!.alphaComponent==0,"Top fragment still rendered")
                    try clean.tiffRepresentation.flatMap {NSBitmapImageRep(data:$0)?.representation(using:.png,properties:[:])}!.write(to:out.appendingPathComponent("studio-attention.png"))
                }
                sheet.lockFocus();clean.draw(in:NSRect(x:pose*140,y:(8-row)*155+15,width:140,height:140));("\(theme) \(pose)" as NSString).draw(at:NSPoint(x:pose*140+5,y:(8-row)*155),withAttributes:[.font:NSFont.systemFont(ofSize:9),.foregroundColor:NSColor.black]);sheet.unlockFocus()
            }
        }
        try NSBitmapImageRep(data:sheet.tiffRepresentation!)!.representation(using:.png,properties:[:])!.write(to:out.appendingPathComponent("all-108-poses.png"))
        print("PASS: 108 poses retain >98% of opaque subject-region pixels; \(trimmed) poses exclude visible fragments; reported studio attention residue absent.")
    }
}
