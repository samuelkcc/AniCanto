use std::{fs,path::{Path,PathBuf},sync::atomic::{AtomicU64,Ordering}};
use serde_json::json;
use anicanto_core::cleanup;
static NEXT:AtomicU64=AtomicU64::new(0);
struct Temp(PathBuf);
impl Temp {
 fn new()->Self {let p=std::env::temp_dir().join(format!("anicanto-cleanup-{}-{}",std::process::id(),NEXT.fetch_add(1,Ordering::Relaxed)));fs::create_dir(&p).unwrap();fs::write(p.join("desktop-state.json"),"{}").unwrap();Self(p)}
 fn put(&self,name:&str)->PathBuf {let p=self.0.join(name);fs::create_dir_all(p.parent().unwrap()).unwrap();fs::write(&p,b"keep or remove").unwrap();p}
}
impl Drop for Temp {fn drop(&mut self){let _=fs::remove_dir_all(&self.0);}}
fn run(t:&Temp,mode:&str)->serde_json::Value {let mut r=json!({"root":t.0,"mode":mode});r["token"]=cleanup::plan(&r).unwrap()["token"].clone();cleanup::execute(&r).unwrap()}
#[test] fn all_removes_downloads_but_preserves_projects_and_media() {
 let t=Temp::new();for name in ["models/voice.gguf","models/a.partial","runtimes/ui/python.exe","packages/old/main.py","cache/uv/file","tools/cuda/cublas.dll","native-ready.json"] {t.put(name);}
 let kept=["jobs/a/take.wav","exports/movie.mp4","exports/movie.report.json","voices/reference.wav","projects.sqlite3","batch-queue.json","models/original.mkv","cache/source.wav","models/clip-AniCanto.report.json"];
 for name in kept {t.put(name);}
 let out=run(&t,"all");assert_eq!(out["complete"],true);assert_eq!(out["filesDeleted"],7);
 for name in kept {assert!(t.0.join(name).is_file(),"{name}");}assert!(!t.0.join("native-ready.json").exists());
}
#[test] fn model_only_keeps_runtimes_and_global_cache() {let t=Temp::new();t.put("models/a.gguf");t.put("runtimes/ui/python.exe");t.put("cache/uv/file");run(&t,"models");assert!(!t.0.join("models/a.gguf").exists());assert!(t.0.join("runtimes/ui/python.exe").exists());assert!(t.0.join("cache/uv/file").exists());}
#[test] fn changed_plan_cannot_delete_new_files() {let t=Temp::new();let mut req=json!({"root":t.0,"mode":"all"});req["token"]=cleanup::plan(&req).unwrap()["token"].clone();t.put("models/new.gguf");assert!(cleanup::execute(&req).unwrap_err().contains("storage-changed"));assert!(t.0.join("models/new.gguf").exists());}
#[test] fn arbitrary_scope_and_broad_roots_are_rejected() {let t=Temp::new();assert!(cleanup::plan(&json!({"root":t.0,"mode":"../jobs"})).is_err());assert!(cleanup::plan(&json!({"root":"/","mode":"all"})).is_err());assert!(cleanup::plan(&json!({"root":Path::new("relative"),"mode":"all"})).is_err());}
#[cfg(unix)] #[test] fn external_links_and_nested_cache_links_are_never_followed() {
 let t=Temp::new();let outside=Temp::new();let model=outside.put("a.gguf");
 fs::create_dir(t.0.join("models")).unwrap();std::os::unix::fs::symlink(&outside.0,t.0.join("models/shared")).unwrap();std::os::unix::fs::symlink(&outside.0,t.0.join("cache")).unwrap();
 let out=run(&t,"all");assert_eq!(out["filesDeleted"],0);assert!(model.exists());assert!(t.0.join("models/shared").is_symlink());
}

#[test] fn progress_tracks_actual_removal_and_keeps_projects() {
 let t=Temp::new();for name in ["models/a.gguf","models/b.partial","jobs/dialogue.wav"] {t.put(name);}
 let mut req=json!({"root":t.0,"mode":"models"});req["token"]=cleanup::plan(&req).unwrap()["token"].clone();
 let mut events=vec![];let result=cleanup::execute_with_progress(&req,&mut |event|events.push(event)).unwrap();
 assert_eq!(events.first().unwrap()["phase"],"checking");assert_eq!(events.last().unwrap()["phase"],"complete");
 assert!(events.iter().any(|e|e["phase"]=="deleting"&&e["processed"]==0&&e["total"]==2));
 assert!(events.iter().any(|e|e["phase"]=="deleting"&&e["processed"]==2));
 assert_eq!(events.last().unwrap()["freedBytes"],result["bytesFreed"]);assert_eq!(result["filesDeleted"],2);assert!(t.0.join("jobs/dialogue.wav").is_file());
}
#[test] fn invalid_token_never_reports_completed_deletion() {
 let t=Temp::new();let model=t.put("models/a.gguf");let mut events=vec![];
 assert!(cleanup::execute_with_progress(&json!({"root":t.0,"mode":"models","token":"stale"}),&mut |e|events.push(e)).is_err());
 assert!(model.exists());assert!(events.iter().all(|e|e["phase"]=="checking"));
}
