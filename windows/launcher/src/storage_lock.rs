//! Serialize package extraction and deferred cleanup for one application store.
use std::{fs::{self,File,OpenOptions},path::Path,time::{Duration,Instant}};
use fs2::FileExt;
pub fn phase(root:&Path,state:&str){let _=fs::write(root.join("launcher-state.json"),serde_json::json!({"phase":state,"pid":std::process::id()}).to_string());}
fn opened(root:&Path)->Result<File,String>{fs::create_dir_all(root).map_err(|e|e.to_string())?;OpenOptions::new().create(true).truncate(false).read(true).write(true).open(root.join("launcher.lock")).map_err(|e|e.to_string())}
pub fn acquire(root:&Path,mut progress:impl FnMut()->Result<(),String>)->Result<File,String>{
 let file=opened(root)?;let start=Instant::now();
 loop{
  match file.try_lock_exclusive(){Ok(())=>return Ok(file),Err(e) if e.raw_os_error()==fs2::lock_contended_error().raw_os_error()=>{},Err(e)=>return Err(e.to_string())}
  let state=fs::read(root.join("launcher-state.json")).ok().filter(|b|b.len()<4096).and_then(|b|serde_json::from_slice::<serde_json::Value>(&b).ok());
  if state.as_ref().and_then(|s|s["phase"].as_str())!=Some("cleaning"){return Err("AniCanto is already open for this library. Close it before reopening the EXE.".into());}
  if start.elapsed()>Duration::from_secs(120){return Err("The previous reset is still removing files. Wait for it to finish, then reopen the EXE. Saved work is retained.".into());}
  progress()?;std::thread::sleep(Duration::from_millis(100));
 }
}
#[cfg(test)] mod tests{
 use super::*;
 fn root()->std::path::PathBuf{let stamp=std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos();std::env::temp_dir().join(format!("anicanto-launch-lock-{stamp}"))}
 #[test] fn active_launcher_blocks_second_extraction(){let r=root();let first=acquire(&r,||Ok(())).unwrap();phase(&r,"opening");assert!(acquire(&r,||Ok(())).is_err());drop(first);assert!(acquire(&r,||Ok(())).is_ok());fs::remove_dir_all(r).unwrap();}
 #[test] fn cleanup_finishes_before_next_launcher_can_enter(){let r=root();let first=acquire(&r,||Ok(())).unwrap();phase(&r,"cleaning");let worker=std::thread::spawn(move||{std::thread::sleep(Duration::from_millis(60));drop(first);});let mut updates=0;let next=acquire(&r,||{updates+=1;Ok(())}).unwrap();worker.join().unwrap();assert!(updates>0);drop(next);fs::remove_dir_all(r).unwrap();}
}
