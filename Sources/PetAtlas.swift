import AppKit

/// Atlas cells may contain disconnected pixels from an adjacent pose. Keep the
/// dominant silhouette and nearby substantial accessories at the original pivot.
enum PetAtlas {
    /// Generated atlases can have unequal row baselines. Cut only through a
    /// substantial transparent band, never through an assumed one-third line.
    static func tiles(_ image:CGImage)->[CGImage] {
        let w=image.width,h=image.height
        var pixels=[UInt8](repeating:0,count:w*h*4)
        let drawn=pixels.withUnsafeMutableBytes {bytes -> Bool in
            guard let c=CGContext(data:bytes.baseAddress,width:w,height:h,bitsPerComponent:8,bytesPerRow:w*4,space:CGColorSpaceCreateDeviceRGB(),bitmapInfo:CGImageAlphaInfo.premultipliedLast.rawValue) else{return false}
            c.draw(image,in:CGRect(x:0,y:0,width:w,height:h));return true
        }
        guard drawn else{return []}
        var gaps:[Range<Int>]=[],start:Int?=nil
        for y in 0..<h {
            let opaque=(0..<w).reduce(0) {$0+(pixels[(y*w+$1)*4+3]>=24 ? 1:0)}
            if opaque<=2 {if start==nil {start=y}}
            else if let begin=start {if y-begin>=16 {gaps.append(begin..<y)};start=nil}
        }
        if let begin=start,h-begin>=16 {gaps.append(begin..<h)}
        var cuts=[0]
        for row in 1...2 {
            let expected=h*row/3
            guard let gap=gaps.filter({abs(($0.lowerBound+$0.upperBound)/2-expected)<h/7}).min(by:{abs(($0.lowerBound+$0.upperBound)/2-expected)<abs(($1.lowerBound+$1.upperBound)/2-expected)}) else{return []}
            cuts.append((gap.lowerBound+gap.upperBound)/2)
        }
        cuts.append(h)
        guard cuts[0]<cuts[1],cuts[1]<cuts[2],cuts[2]<cuts[3] else{return []}
        return (0..<12).compactMap {index in
            image.cropping(to:CGRect(x:(index%4)*w/4,y:cuts[index/4],width:w/4,height:cuts[index/4+1]-cuts[index/4]))
        }
    }

    static func subjectBounds(_ image:CGImage)->CGRect? {
        let w=image.width,h=image.height
        var pixels=[UInt8](repeating:0,count:w*h*4)
        let drawn=pixels.withUnsafeMutableBytes {bytes -> Bool in
            guard let c=CGContext(data:bytes.baseAddress,width:w,height:h,bitsPerComponent:8,bytesPerRow:w*4,space:CGColorSpaceCreateDeviceRGB(),bitmapInfo:CGImageAlphaInfo.premultipliedLast.rawValue) else{return false}
            c.draw(image,in:CGRect(x:0,y:0,width:w,height:h));return true
        }
        guard drawn else{return nil}
        var seen=[Bool](repeating:false,count:w*h)
        var parts:[(Int,CGRect)]=[]
        for seed in 0..<w*h where !seen[seed] && pixels[seed*4+3]>=24 {
            var queue=[seed],head=0,minX=w,minY=h,maxX=0,maxY=0;seen[seed]=true
            while head<queue.count {
                let p=queue[head];head+=1;let x=p%w,y=p/w
                minX=min(minX,x);maxX=max(maxX,x);minY=min(minY,y);maxY=max(maxY,y)
                for dy in -1...1 {for dx in -1...1 {
                    let nx=x+dx,ny=y+dy
                    guard nx>=0,nx<w,ny>=0,ny<h else{continue}
                    let n=ny*w+nx
                    if !seen[n] && pixels[n*4+3]>=24 {seen[n]=true;queue.append(n)}
                }}
            }
            parts.append((queue.count,CGRect(x:minX,y:minY,width:maxX-minX+1,height:maxY-minY+1)))
        }
        guard let main=parts.max(by:{$0.0<$1.0}),main.0>100 else{return nil}
        var bounds=main.1
        // Preserve floating sleep bubbles and substantial accessories, but never
        // include little fragments along the crop boundary.
        let nearby=main.1.insetBy(dx:-16,dy:-16)
        for part in parts where part.0>=100 && nearby.intersects(part.1) {
            if part.1.minX>1 && part.1.minY>1 && part.1.maxX<CGFloat(w-1) && part.1.maxY<CGFloat(h-1) {bounds=bounds.union(part.1)}
        }
        return bounds.insetBy(dx:-2,dy:-2).intersection(CGRect(x:0,y:0,width:w,height:h)).integral
    }
    @MainActor static func frame(_ image:CGImage,canvas:NSSize?=nil)->NSImage {
        let size=canvas ?? NSSize(width:image.width,height:image.height)
        guard let bounds=subjectBounds(image),let crop=image.cropping(to:bounds) else{return NSImage(cgImage:image,size:size)}
        let result=NSImage(size:size)
        result.lockFocus()
        NSColor.clear.setFill();NSRect(origin:.zero,size:size).fill(using:.copy)
        NSImage(cgImage:crop,size:bounds.size).draw(in:NSRect(x:bounds.minX+(size.width-CGFloat(image.width))/2,y:canvas == nil ? CGFloat(image.height)-bounds.maxY:32,width:bounds.width,height:bounds.height),from:.zero,operation:.copy,fraction:1)
        result.unlockFocus();return result
    }
}
