fn main() {
    println!("cargo:rerun-if-changed=icons/icon.png");
    println!("cargo:rerun-if-changed=icons/icon.ico");
    // This build already uses +crt-static for portable Windows distribution.
    // Do not also request Tauri's mixed dynamic-UCRT mode: it conflicts with
    // cargo-xwin's explicit UCRT library selection.
    let attributes=tauri_build::Attributes::new().windows_attributes(tauri_build::WindowsAttributes::new().static_vc_runtime(false).window_icon_path("icons/icon.ico"));
    tauri_build::try_build(attributes).expect("AniCanto host resources");
}
