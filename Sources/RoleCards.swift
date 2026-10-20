import SwiftUI
import AppKit
import CryptoKit
private let roleImages:NSCache<NSString,NSImage>={let cache=NSCache<NSString,NSImage>();cache.countLimit=160;cache.totalCostLimit=128*1024*1024;return cache}()
func roleImage(_ path:String?)->NSImage? {
    guard let path else{return nil}
    if let image=roleImages.object(forKey:path as NSString) {return image}
    guard let image=NSImage(contentsOfFile:path) else{return nil}
    roleImages.setObject(image,forKey:path as NSString,cost:Int(image.size.width*image.size.height*4));return image
}
func roleColor(_ id:String)->Color {
    let hue:Double
    if id.hasPrefix("auto-"),let index=Int(id.split(separator:"-").last ?? ""),index>0 {
        // Adjacent automatic IDs need visibly different colors, rather than
        // nearly identical hues produced by hashing a numeric suffix.
        hue=(0.72+Double(index-1)*0.61803398875).truncatingRemainder(dividingBy:1)
    } else {
        let digest=SHA256.hash(data:Data(id.utf8))
        hue=Double(digest.prefix(2).reduce(0) {($0 << 8)+Int($1)})/65536
    }
    return Color(hue:hue,saturation:0.55,brightness:0.78)
}
struct RoleCard:View {
    let profile:VoiceProfile
    let code:String
    let count:Int
    var body:some View {
        HStack(spacing:12) {
            if let image=roleImage(profile.avatar) {
                Image(nsImage:image).resizable().scaledToFill().frame(width:64,height:76).clipped().clipShape(RoundedRectangle(cornerRadius:8))
            } else {Image(systemName:"person.crop.rectangle").font(.system(size:30)).frame(width:64,height:76).foregroundStyle(roleColor(profile.id))}
            VStack(alignment:.leading,spacing:6) {
                Text(code+" · "+localizedRoleName(profile.name)).font(.headline)
                Text(String(format:L("%d 段對白"),count)).font(.caption).foregroundStyle(.secondary)
                Text(profile.identityLabel).font(.caption).foregroundStyle(.secondary)
                Text(profile.avatar == nil ? L("未有可靠角色畫面；沿用聲音配對"):L("已保存角色畫面參考")).font(.caption).foregroundStyle(.secondary)
            }
            Spacer(minLength:0)
        }.padding(10).background(roleColor(profile.id).opacity(0.12),in:RoundedRectangle(cornerRadius:10))
        .onDrag {NSItemProvider(object:("anicanto-role:"+profile.id) as NSString)}
    }
}

struct RoleAvatarBadge:View {
    let profile:VoiceProfile
    private static let images=NSCache<NSString,NSImage>()
    private var image:NSImage? {
        guard let path=profile.avatar else{return nil}
        if let cached=Self.images.object(forKey:path as NSString) {return cached}
        guard let image=NSImage(contentsOfFile:path) else{return nil}
        Self.images.setObject(image,forKey:path as NSString);return image
    }
    var body:some View {
        HStack(spacing:5) {
            if let image {Image(nsImage:image).resizable().scaledToFill().frame(width:28,height:28).clipped().clipShape(RoundedRectangle(cornerRadius:5))}
            else {Image(systemName:profile.identityStatus=="independent" ? "waveform":"person.crop.square.fill").foregroundStyle(roleColor(profile.id)).frame(width:28,height:28)}
            Text(localizedRoleName(profile.name)).font(.system(size:12)).lineLimit(1)
        }.help(localizedRoleName(profile.name))
    }
}
