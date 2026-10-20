import SwiftUI

struct LicenseRecord: Decodable,Identifiable {
    let name:String
    let version:String
    let license:String
    let origin:String
    let files:[String]
    let origins:[String]?
    let noticeSources:[String:[String]]?
    let fileRoot:String?
    var id:String { name+version+license+origin }
}
final class LicenseSearch: ObservableObject { @Published var text="";@Published var external:[LicenseRecord]=[] }
struct LicensesView: View {
    @AppStorage("studioLanguage") private var interfaceLanguage="system"
    @StateObject private var query=LicenseSearch()
    private var search:String { query.text }
    private static let inventory:[LicenseRecord] = {
        guard let url=Bundle.main.url(forResource:"license-inventory",withExtension:"json"),let data=try? Data(contentsOf:url) else{return []}
        return (try? JSONDecoder().decode([LicenseRecord].self,from:data)) ?? []
    }()
    private var records:[LicenseRecord] {Self.inventory+query.external}
    private static var support:URL {ProcessInfo.processInfo.environment["SAM_CANTO_DATA"].map {URL(fileURLWithPath:$0)} ?? FileManager.default.urls(for:.applicationSupportDirectory,in:.userDomainMask)[0].appendingPathComponent("SamCantoSync")}
    var body: some View {
        LazyVStack(alignment:.leading,spacing:12) {
            Label(L("第三方程式庫與授權"),systemImage:"doc.text.magnifyingglass").font(.title2.bold())
            Text(L("清單由呢個版本實際打包嘅程式庫產生。展開可閱讀 App 內嘅授權文件；不同執行環境可能使用不同版本。")).font(.caption).foregroundStyle(.secondary)
            TextField(L("搜尋名稱、版本或授權"),text:$query.text).textFieldStyle(.roundedBorder)
            ForEach(records.filter { search.isEmpty || ($0.name+" "+$0.version+" "+$0.license).localizedCaseInsensitiveContains(search) }) { row in
                DisclosureGroup {
                    VStack(alignment:.leading,spacing:8) {
                        ForEach(row.origins ?? [row.origin],id:\.self) {origin in
                            if let url=URL(string:origin),url.scheme=="https" {Link(origin,destination:url).font(.caption)} else {Text(origin).font(.caption).foregroundStyle(.secondary)}
                        }
                        if row.files.isEmpty { Text(L("套件未附獨立授權文件；請核對上游授權，未視為已完成發佈審核。")).font(.caption) }
                        ForEach(row.files,id:\.self) { path in
                            DisclosureGroup(URL(fileURLWithPath:path).lastPathComponent) {
                                if let sources=row.noticeSources?[path],sources.count>1 {Text(sources.joined(separator:"\n")).font(.caption).foregroundStyle(.secondary).textSelection(.enabled)}
                                if let root=row.fileRoot=="applicationSupport" ? Self.support:Bundle.main.resourceURL,let text=try? String(contentsOf:root.appendingPathComponent(path),encoding:.utf8) {
                                    ScrollView { Text(text).font(.system(size:11,design:.monospaced)).textSelection(.enabled).frame(maxWidth:.infinity,alignment:.leading).padding(8) }.frame(height:220)
                                } else { Text(L("未能讀取授權文件。")) }
                            }
                        }
                    }.padding(.vertical,8)
                } label: {
                    HStack { Text(row.name).font(.headline);Text(row.version).font(.caption.monospaced());Spacer();Text(row.license).font(.caption).foregroundStyle(.secondary).lineLimit(2) }
                }
                Divider()
            }
        }.task {
            let directory=Self.support
            query.external=await Task.detached(priority:.utility) {
                guard let data=try? Data(contentsOf:directory.appendingPathComponent("runtime-license-inventory.json")) else{return [LicenseRecord]()}
                return (try? JSONDecoder().decode([LicenseRecord].self,from:data)) ?? []
            }.value
        }
    }
}
struct AboutAniCanto: View {
    private static let introduction:[String:String] = {
        guard let url=Bundle.main.url(forResource:"app-information",withExtension:"json"),
              let data=try? Data(contentsOf:url),
              let info=try? JSONSerialization.jsonObject(with:data) as? [String:Any] else{return [:]}
        return info["introduction"] as? [String:String] ?? [:]
    }()
    @AppStorage("studioLanguage") private var interfaceLanguage="system"
    @Environment(\.locale) private var locale
    var body: some View {
        VStack(alignment:.leading,spacing:16) {
            HStack {
                Image(systemName:"waveform").font(.largeTitle).foregroundStyle(accent)
                VStack(alignment:.leading) {
                    Text("AniCanto").font(.largeTitle.bold())
                    Text("Version \(Bundle.main.object(forInfoDictionaryKey:"CFBundleShortVersionString") as? String ?? "") · Build \(Bundle.main.object(forInfoDictionaryKey:"CFBundleVersion") as? String ?? "") · Beta").font(.caption.monospaced())
                }
            }
            Text(L("© 2026 SCKC · Developer / 開發者：SCKC")).font(.headline)
            Text(Self.introduction[locale.identifier.hasPrefix("en") ? "en":"zh-HK"] ?? "")
            Divider()
            Text(L("應用程式授權")).font(.headline)
            Text("AniCanto original code · MIT").font(.callout)
            Text(L("第三方程式、模型權重同字型各自保留原授權。呢個 Beta 版本唔代表已完成對外重新分發嘅源碼及授權審核。")).font(.caption).foregroundStyle(.secondary)
            DisclosureGroup(L("閱讀 AniCanto MIT 授權")) {
                if let url=Bundle.main.resourceURL?.appendingPathComponent("Licenses/AniCanto-MIT.txt"),let text=try? String(contentsOf:url) {
                    ScrollView { Text(text).font(.system(size:11,design:.monospaced)).textSelection(.enabled).padding(8) }.frame(height:220)
                }
            }
            DisclosureGroup(L("模型與本機處理")) {
                Text(L("Qwen3.5、Drama 3、GPT-SoVITS、CosyVoice 3、VoxCPM2、WenetSpeech-Yue、Whisper 同分離模型係獨立組件。部分權重由你選擇下載，唔包含喺 App；實際版本見模型清單及下載 manifest。Qwen 可用於翻譯、角色分析及修復建議。轉換喺本機執行，首次部署及下載需要網絡。")).font(.caption)
                if let url=Bundle.main.url(forResource:"MODEL-NOTICES",withExtension:"txt"),let text=try? String(contentsOf:url) { Text(text).font(.caption.monospaced()).textSelection(.enabled) }
            }
            Divider()
            LicensesView()
        }.card()
    }
}

struct AboutStudioWindow:View {
    @AppStorage("studioLanguage") private var interfaceLanguage="system"
    var close:()->Void
    var body:some View {
        VStack(spacing:0) {
            HStack(spacing:12) {
                AppEmblem().frame(width:28,height:28)
                Text(L("關於與授權")).font(.title3.bold())
                Spacer()
                Button(action:close) {Image(systemName:"xmark")}.help(L("關閉")).accessibilityLabel(L("關閉")).keyboardShortcut(.cancelAction)
            }.padding(24)
            Divider()
            ScrollView {AboutAniCanto().padding(24)}
        }.frame(maxWidth:.infinity,maxHeight:.infinity).background(StudioPalette.panel)
    }
}
