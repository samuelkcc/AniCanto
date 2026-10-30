//! An existing venv executable is not evidence that its base still works.
use std::{collections::HashMap,fs,io::Read,path::{Path,PathBuf},process::{Command,Stdio},sync::{Mutex,OnceLock},time::{Duration,Instant,UNIX_EPOCH}};
type Stamp=Vec<(PathBuf,Option<(u64,u128)>)>;
static CACHE:OnceLock<Mutex<HashMap<PathBuf,(Stamp,bool)>>>=OnceLock::new();
fn stamp(p:&Path)->Stamp {
 let cfg=p.parent().and_then(Path::parent).unwrap_or(p).join("pyvenv.cfg");let mut paths=vec![p.to_path_buf(),cfg.clone()];
 if let Ok(meta)=fs::metadata(&cfg){if meta.len()<16384 {if let Ok(raw)=fs::read_to_string(&cfg){for line in raw.lines(){if let Some((key,home))=line.split_once('='){if key.trim()=="home"{let base=PathBuf::from(home.trim());for name in ["python.exe","python312.dll","Lib/encodings/__init__.py"]{paths.push(base.join(name));}}}}}}}
 paths.into_iter().map(|path|{let signature=fs::metadata(&path).ok().map(|m|(m.len(),m.modified().ok().and_then(|t|t.duration_since(UNIX_EPOCH).ok()).map(|d|d.as_nanos()).unwrap_or(0)));(path,signature)}).collect()
}
fn probe(p:&Path,timeout:Duration)->Result<(),String> {
 let mut command=Command::new(p);command.args(["-I","-c","import ssl,json,sys;assert sys.version_info[:2]==(3,12);print('ANICANTO_PYTHON_READY')"]).stdout(Stdio::piped()).stderr(Stdio::piped()).env_remove("PYTHONHOME").env_remove("PYTHONPATH");
 #[cfg(windows)]{use std::os::windows::process::CommandExt;command.creation_flags(0x08000000);}
 let mut child=command.spawn().map_err(|e|format!("{}: {e}",p.display()))?;let started=Instant::now();
 loop{
  match child.try_wait(){
   Ok(Some(status))=>{let mut output=String::new();let mut error=String::new();if let Some(pipe)=child.stdout.take(){let _=pipe.take(4096).read_to_string(&mut output);}if let Some(pipe)=child.stderr.take(){let _=pipe.take(4096).read_to_string(&mut error);}return if status.success()&&output.contains("ANICANTO_PYTHON_READY"){Ok(())}else{Err(format!("{}: {status}; {error}",p.display()))};},
   Err(e)=>{let _=child.kill();let _=child.wait();return Err(e.to_string());},
   Ok(None)=>{}
  }
  if started.elapsed()>=timeout {let _=child.kill();let _=child.wait();return Err(format!("{}: readiness check timed out",p.display()));}
  std::thread::sleep(Duration::from_millis(20));
 }
}
pub fn usable(p:&Path,root:&Path)->bool {
 if !p.is_file(){return false;}
 let signature=stamp(p);let mut cache=CACHE.get_or_init(||Mutex::new(HashMap::new())).lock().unwrap();
 if let Some((old,good))=cache.get(p){if *old==signature{return *good;}}
 let result=probe(p,Duration::from_secs(8));let good=result.is_ok();
 if let Err(error)=result {let folder=root.join("logs");if fs::create_dir_all(&folder).is_ok(){let _=fs::write(folder.join("python-readiness.json"),serde_json::json!({"executable":p,"ready":false,"error":error,"action":"Use Download and prepare; native cleanup remains available."}).to_string());}}
 cache.insert(p.to_path_buf(),(signature,good));good
}
#[cfg(test)] mod tests {
 use super::*;
 #[cfg(unix)] fn fixture(code:&str)->(PathBuf,PathBuf){use std::os::unix::fs::PermissionsExt;let id=std::time::SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos();let root=std::env::temp_dir().join(format!("anicanto-python-{id}"));let folder=root.join("runtimes/ui/Scripts");fs::create_dir_all(&folder).unwrap();let p=folder.join("python.exe");fs::write(&p,code).unwrap();fs::set_permissions(&p,fs::Permissions::from_mode(0o755)).unwrap();(root,p)}
 #[cfg(unix)] #[test] fn unusable_existing_executable_is_not_ready_and_logs_error(){let(root,p)=fixture("#!/bin/sh\nprintf 'missing base python.exe' >&2\nexit 3\n");assert!(!usable(&p,&root));assert!(fs::read_to_string(root.join("logs/python-readiness.json")).unwrap().contains("missing base python.exe"));fs::remove_dir_all(root).unwrap();}
 #[cfg(unix)] #[test] fn base_change_invalidates_both_success_and_failure(){let(root,p)=fixture("#!/bin/sh\nprintf ANICANTO_PYTHON_READY\n");let base=root.join("python/base");fs::create_dir_all(&base).unwrap();fs::write(p.parent().unwrap().parent().unwrap().join("pyvenv.cfg"),format!("home = {}",base.display())).unwrap();assert!(usable(&p,&root));let before=stamp(&p);fs::write(base.join("python.exe"),"new base").unwrap();assert_ne!(before,stamp(&p));fs::write(&p,"#!/bin/sh\nexit 4\n").unwrap();assert!(!usable(&p,&root));fs::write(&p,"#!/bin/sh\nprintf ANICANTO_PYTHON_READY\n").unwrap();assert!(usable(&p,&root));fs::remove_dir_all(root).unwrap();}
 #[cfg(unix)] #[test] fn hung_interpreter_is_bounded(){let(root,p)=fixture("#!/bin/sh\nexec sleep 5\n");let start=Instant::now();assert!(probe(&p,Duration::from_millis(60)).is_err());assert!(start.elapsed()<Duration::from_secs(1));fs::remove_dir_all(root).unwrap();}
}
