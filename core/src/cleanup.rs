//! Explicit, app-local download cleanup. Never traverses links or deletes projects.
use serde_json::{json,Value};
use std::{fs,path::{Path,PathBuf},time::UNIX_EPOCH};
use crate::digest;

const MODELS:&[&str]=&["models","gpt-sovits","model-ready","voice-model-ready","stt-ready","downloads","cache/huggingface"];
const ALL:&[&str]=&["runtimes","runtime","text-runtime","asr-runtime","separator-runtime","gsv-runtime","cosy-runtime","local-tts-runtime","qwen-runtime","runtime-receipts","python","packages","tools","sources","ollama","cache","ollama-darwin.tgz"];
const MARKERS:&[&str]=&["native-ready.json","ui-ready.txt","drama3-windows-ready.json","separator-windows-ready.json","separator-ready.json","speakers-ready.json","asr-windows-ready.json","asr-ready.json","speech-ready.json","gpt-windows-ready.json","cosy-windows-ready.json","local-tts-ready.json","drama3-ready.json","drama3-small-ready.json","stt-ready.json","gsv-ready.json","cosy-ready.json","mlx-text-ready.json","worker-runtime-ready.json","analysis-runtime-ready.json","asr-runtime-ready.json","gpt-runtime-ready.json","cosy-runtime-ready.json","local-runtime-ready.json"];
fn linked(meta:&fs::Metadata)->bool {
    #[cfg(windows)] {use std::os::windows::fs::MetadataExt;meta.file_type().is_symlink() || meta.file_attributes() & 0x400!=0}
    #[cfg(not(windows))] {meta.file_type().is_symlink()}
}
fn root(req:&Value)->Result<PathBuf,String> {
    let p=Path::new(req["root"].as_str().ok_or("missing-storage-root")?);
    if !p.is_absolute() || p.parent().is_none() {return Err("invalid-storage-root".into());}
    let m=fs::symlink_metadata(p).map_err(|e|e.to_string())?;
    if linked(&m) || !m.is_dir() {return Err("storage-root-is-not-a-real-directory".into());}
    let p=p.canonicalize().map_err(|e|e.to_string())?;
    if p.components().count()<3 {return Err("storage-root-too-broad".into());}
    for key in ["HOME","USERPROFILE","LOCALAPPDATA","APPDATA"] {
        if let Some(home)=std::env::var_os(key) {if Path::new(&home).canonicalize().ok().is_some_and(|h|h==p || h.starts_with(&p)) {return Err("storage-root-too-broad".into());}}
    }
    if !["SamCantoSync","CantoSync-Windows","AniCanto","AniCanto-Windows"].contains(&p.file_name().and_then(|s|s.to_str()).unwrap_or("")) && !["desktop-state.json","projects.sqlite3","model-selections.json"].iter().any(|n|p.join(n).is_file()) {
        return Err("unrecognized-app-storage-root".into());
    }
    Ok(p)
}
fn protected(path:&Path)->bool {
    let ext=path.extension().and_then(|s|s.to_str()).unwrap_or("").to_lowercase();
    ["mp4","mkv","mov","avi","webm","m4v","wav","mp3","m4a","flac","aac","ogg","srt","ass","vtt"].contains(&ext.as_str()) || path.file_name().and_then(|s|s.to_str()).unwrap_or("").to_lowercase().contains("-anicanto.") || path.file_name().and_then(|s|s.to_str()).unwrap_or("").to_lowercase().contains("-cantosync.")
}
struct Scan {files:Vec<(PathBuf,u64,u128)>,dirs:Vec<PathBuf>,kept:u64}
fn walk(root:&Path,path:&Path,scan:&mut Scan)->Result<(),String> {
    let meta=match fs::symlink_metadata(path) {Ok(m)=>m,Err(e) if e.kind()==std::io::ErrorKind::NotFound=>return Ok(()),Err(e)=>return Err(e.to_string())};
    if linked(&meta) {scan.kept+=1;return Ok(());}
    if meta.is_dir() {
        scan.dirs.push(path.to_path_buf());
        let mut children=fs::read_dir(path).map_err(|e|e.to_string())?.map(|e|e.map(|r|r.path())).collect::<Result<Vec<_>,_>>().map_err(|e|e.to_string())?;
        children.sort();for child in children {walk(root,&child,scan)?;}
    } else if meta.is_file() {
        if protected(path) {scan.kept+=1;return Ok(());}
        scan.files.push((path.strip_prefix(root).map_err(|e|e.to_string())?.to_path_buf(),meta.len(),meta.modified().ok().and_then(|t|t.duration_since(UNIX_EPOCH).ok()).map(|d|d.as_nanos()).unwrap_or(0)));
    } else {scan.kept+=1;}
    Ok(())
}
fn scan(req:&Value)->Result<(PathBuf,Scan,Value),String> {
    let root=root(req)?;let mode=req["mode"].as_str().unwrap_or("models");
    if !["models","all"].contains(&mode) {return Err("invalid-cleanup-mode".into());}
    let mut names:Vec<&str>=MODELS.to_vec();if mode=="all" {names.extend(ALL);names.retain(|n|*n!="cache/huggingface");}names.extend(MARKERS);
    let mut s=Scan{files:vec![],dirs:vec![],kept:0};let mut groups=vec![];
    for name in names {
        // Also reject a link in an intermediate path, e.g. cache -> shared cache.
        if Path::new(name).ancestors().skip(1).any(|a|a!=Path::new("") && fs::symlink_metadata(root.join(a)).is_ok_and(|m|linked(&m))) {s.kept+=1;continue;}
        let start=s.files.len();walk(&root,&root.join(name),&mut s)?;
        let bytes:u64=s.files[start..].iter().map(|r|r.1).sum();
        if s.files.len()>start {groups.push(json!({"path":name,"bytes":bytes,"files":s.files.len()-start}));}
    }
    s.files.sort_by(|a,b|a.0.cmp(&b.0));s.files.dedup_by(|a,b|a.0==b.0);
    let identity=json!([root.to_string_lossy(),mode,s.files.iter().map(|(p,n,t)|json!([p.to_string_lossy(),n,t.to_string()])).collect::<Vec<_>>()]);
    let result=json!({"root":root,"mode":mode,"bytes":s.files.iter().map(|r|r.1).sum::<u64>(),"files":s.files.len(),"protectedFiles":s.kept,"groups":groups,"token":digest(identity.to_string().as_bytes()),"preserves":["source-videos","projects","recordings","exports","settings","external-caches"]});
    Ok((root,s,result))
}
pub fn plan(req:&Value)->Result<Value,String> {Ok(scan(req)?.2)}
pub fn execute(req:&Value)->Result<Value,String> {execute_with_progress(req,&mut |_|{})}
pub fn execute_with_progress(req:&Value,notify:&mut dyn FnMut(Value))->Result<Value,String> {
    notify(json!({"phase":"checking","processed":0}));
    let (root,s,plan)=scan(req)?;
    if req["token"]!=plan["token"] {return Err("storage-changed-review-cleanup-again".into());}
    let total=s.files.len();let mut processed=0;
    let mut freed=0u64;let mut deleted=0;let mut failures=vec![];
    let mut last=std::time::Instant::now();
    notify(json!({"phase":"deleting","total":total,"processed":0,"freedBytes":0,"failed":0}));
    for (relative,size,_) in s.files {
        let path=root.join(&relative);
        if path.ancestors().take_while(|a|*a!=root).any(|a|fs::symlink_metadata(a).is_ok_and(|m|linked(&m))) {failures.push(relative.to_string_lossy().to_string()+": link changed");}
        else {match fs::remove_file(&path) {Ok(())=>{freed+=size;deleted+=1;},Err(e)=>failures.push(format!("{}: {e}",relative.display()))}}
        processed+=1;
        if processed==total || last.elapsed()>=std::time::Duration::from_millis(100) {
            notify(json!({"phase":"deleting","total":total,"processed":processed,"freedBytes":freed,"failed":failures.len()}));last=std::time::Instant::now();
        }
    }
    notify(json!({"phase":"tidying","total":total,"processed":processed,"freedBytes":freed,"failed":failures.len()}));
    let mut dirs=s.dirs;dirs.sort_by_key(|p|std::cmp::Reverse(p.components().count()));dirs.dedup();
    for dir in dirs {let _=fs::remove_dir(dir);}
    let result=json!({"mode":plan["mode"],"bytesFreed":freed,"filesDeleted":deleted,"protectedFiles":plan["protectedFiles"],"failures":failures,"complete":failures.is_empty()});
    // Keep a small audit receipt outside all removable directories.
    let _=fs::write(root.join("last-download-cleanup.json"),result.to_string());
    notify(json!({"phase":if failures.is_empty(){"complete"}else{"partial"},"total":total,"processed":processed,"freedBytes":freed,"failed":failures.len()}));
    Ok(result)
}
