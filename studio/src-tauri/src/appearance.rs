// Only the appearance enum crosses into the early webview script. No runtime,
// models, project contents or other saved settings are needed for first paint.
use std::{path::Path, sync::{Arc,atomic::{AtomicBool,Ordering}}};
use tauri::window::Color;
pub struct StartupWindow(pub Arc<AtomicBool>);
pub fn normalize(value:&str)->&str {match value {"light"=>"light","dark"=>"dark",_=>"system"}}
pub fn saved(root:&Path)->String {
    let path=root.join("studio/desktop-state.json");
    std::fs::metadata(&path).ok().filter(|m|m.len()<=8*1024*1024)
        .and_then(|_|std::fs::read(path).ok())
        .and_then(|raw|serde_json::from_slice::<serde_json::Value>(&raw).ok())
        .and_then(|v|v["settings"]["appearance"].as_str().map(|s|normalize(s).to_owned()))
        .unwrap_or_else(||"system".into())
}
pub fn script(value:&str)->String {format!("window.__ANICANTO_APPEARANCE__={};",serde_json::to_string(normalize(value)).unwrap())}
pub fn theme(value:&str)->Option<tauri::Theme>{match normalize(value){"light"=>Some(tauri::Theme::Light),"dark"=>Some(tauri::Theme::Dark),_=>None}}
pub fn background(dark:bool)->Color {if dark {Color(28,26,34,255)}else{Color(246,245,248,255)}}
#[tauri::command]
pub fn studio_appearance(window:tauri::WebviewWindow,startup:tauri::State<'_,StartupWindow>,appearance:String,dark:bool)->Result<(),String>{
    let value=normalize(&appearance);
    let _=window.set_theme(theme(value));
    // Match the document even while its first composited frame is pending.
    let _=window.set_background_color(Some(background(if value=="system"{dark}else{value=="dark"})));
    if !startup.0.swap(true,Ordering::AcqRel){window.show().map_err(|e|e.to_string())?;}
    Ok(())
}
#[cfg(test)] mod tests {
    use super::*;
    #[test] fn only_valid_appearance_can_enter_script(){
        assert_eq!(normalize(""),"system");assert_eq!(normalize("<script>bad</script>"),"system");
        assert_eq!(script("dark"),"window.__ANICANTO_APPEARANCE__=\"dark\";");
        assert_eq!(script("';alert(1)"),"window.__ANICANTO_APPEARANCE__=\"system\";");
        assert_eq!(theme("system"),None);assert_eq!(theme("light"),Some(tauri::Theme::Light));
    }
    #[test] fn first_paint_reads_saved_preference_without_touching_state(){
        let folder=std::env::temp_dir().join(format!("anicanto-appearance-{}",std::process::id()));
        std::fs::create_dir_all(folder.join("studio")).unwrap();
        assert_eq!(saved(&folder),"system");
        let path=folder.join("studio/desktop-state.json");
        for value in ["dark","light","system","invalid"] {
            let raw=serde_json::json!({"settings":{"appearance":value},"queue":[{"id":"untouched"}]}).to_string();
            std::fs::write(&path,&raw).unwrap();assert_eq!(saved(&folder),normalize(value));
            assert_eq!(std::fs::read_to_string(&path).unwrap(),raw);
        }
        std::fs::write(&path,"{interrupted").unwrap();assert_eq!(saved(&folder),"system");
        std::fs::remove_dir_all(folder).unwrap();
    }
}
