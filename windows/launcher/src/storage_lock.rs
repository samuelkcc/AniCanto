//! Serialize package extraction and deferred cleanup for one application store.
use std::{fs::{self,File,OpenOptions},path::Path,time::{Duration,Instant}};
use fs2::FileExt;
pub fn phase(root:&Path,state:&str){let _=fs::write(root.join("launcher-state.json"),serde_json::json!({"phase":state,"pid":std::process::id()}).to_string());}
fn opened(root:&Path)->Result<File,String>{fs::create_dir_all(root).map_err(|e|e.to_string())?;OpenOptions::new().create(true).truncate(false).read(true).write(true).open(root.join("launcher.lock")).map_err(|e|e.to_string())}
pub fn acquire(root:&Path,mut progress:impl FnMut()->Result<(),String>)->Result<File,String>{
 acquire_with_limits(root,&mut progress,Duration::from_secs(120),Duration::from_secs(1800))
}
fn acquire_with_limits(root:&Path,progress:&mut dyn FnMut()->Result<(),String>,stale_limit:Duration,total_limit:Duration)->Result<File,String>{
 let file=opened(root)?;let start=Instant::now();let mut changed=Instant::now();let mut previous=String::new();
 loop{
  match file.try_lock_exclusive(){Ok(())=>return Ok(file),Err(e) if e.raw_os_error()==fs2::lock_contended_error().raw_os_error()=>{},Err(e)=>return Err(e.to_string())}
  let state=fs::read(root.join("launcher-state.json")).ok().filter(|b|b.len()<4096).and_then(|b|serde_json::from_slice::<serde_json::Value>(&b).ok());
  if state.as_ref().and_then(|s|s["phase"].as_str())!=Some("cleaning"){return Err("AniCanto is already open for this library. Close it before reopening the EXE.".into());}
  let snapshot=read_progress(root).to_string();
  if snapshot!=previous{previous=snapshot;changed=Instant::now();}
  if changed.elapsed()>stale_limit || start.elapsed()>total_limit{return Err("The previous reset is still removing files. Wait for it to finish, then reopen the EXE. Saved work is retained.".into());}
  progress()?;std::thread::sleep(Duration::from_millis(100));
 }
}
pub fn cleanup_progress(root:&Path,status:&serde_json::Value){
 let mut value=status.clone();value["pid"]=serde_json::json!(std::process::id());
 let temporary=root.join("cleanup-progress.tmp");
 if fs::write(&temporary,value.to_string()).is_ok(){let _=fs::rename(temporary,root.join("cleanup-progress.json"));}
}
fn read_progress(root:&Path)->serde_json::Value{
 let state=fs::read(root.join("launcher-state.json")).ok().and_then(|b|serde_json::from_slice::<serde_json::Value>(&b).ok()).unwrap_or_default();
 let progress=fs::read(root.join("cleanup-progress.json")).ok().filter(|b|b.len()<4096).and_then(|b|serde_json::from_slice::<serde_json::Value>(&b).ok()).unwrap_or_default();
 if state["pid"]==progress["pid"]{progress}else{serde_json::Value::Null}
}
pub fn cleanup_message(value:&serde_json::Value)->String{
 let phase=value["phase"].as_str().unwrap_or("checking");
 let stage=match phase{"deleting"=>"Removing downloaded files","tidying"=>"Removing empty folders","complete"=>"Reset complete","partial"=>"Reset finished; some changed or busy files were kept",_=>"Checking the approved removal list"};
 if let (Some(done),Some(total))=(value["processed"].as_u64(),value["total"].as_u64()){
  format!("{stage}: {done} / {total} files · {:.1} GB freed",value["freedBytes"].as_u64().unwrap_or(0) as f64/1e9)
 }else{stage.into()}
}
pub fn waiting_message(root:&Path)->String{
 let value=read_progress(root);if value.is_null(){"Finishing the previous reset — please wait…".into()}else{cleanup_message(&value)}
}
#[cfg(test)] mod tests{
 use super::*;
 fn root()->std::path::PathBuf{let stamp=std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos();std::env::temp_dir().join(format!("anicanto-launch-lock-{stamp}"))}
 #[test] fn active_launcher_blocks_second_extraction(){let r=root();let first=acquire(&r,||Ok(())).unwrap();phase(&r,"opening");assert!(acquire(&r,||Ok(())).is_err());drop(first);assert!(acquire(&r,||Ok(())).is_ok());fs::remove_dir_all(r).unwrap();}
 #[test] fn cleanup_finishes_before_next_launcher_can_enter(){let r=root();let first=acquire(&r,||Ok(())).unwrap();phase(&r,"cleaning");let worker=std::thread::spawn(move||{std::thread::sleep(Duration::from_millis(60));drop(first);});let mut updates=0;let next=acquire(&r,||{updates+=1;Ok(())}).unwrap();worker.join().unwrap();assert!(updates>0);drop(next);fs::remove_dir_all(r).unwrap();}

 #[test] fn advancing_cleanup_can_outlast_the_stale_wait_limit(){
  let r=root();let first=acquire(&r,||Ok(())).unwrap();phase(&r,"cleaning");let copy=r.clone();
  let worker=std::thread::spawn(move||{for n in 0..8{cleanup_progress(&copy,&serde_json::json!({"phase":"deleting","processed":n,"total":8,"freedBytes":n*10}));std::thread::sleep(Duration::from_millis(50));}drop(first);});
  let next=acquire_with_limits(&r,&mut ||Ok(()),Duration::from_millis(150),Duration::from_secs(3)).unwrap();worker.join().unwrap();drop(next);fs::remove_dir_all(r).unwrap();
 }
 #[test] fn stalled_cleanup_is_bounded_and_no_lock_is_broken(){
  let r=root();let first=acquire(&r,||Ok(())).unwrap();phase(&r,"cleaning");
  assert!(acquire_with_limits(&r,&mut ||Ok(()),Duration::from_millis(50),Duration::from_secs(1)).is_err());
  phase(&r,"opening");assert!(acquire(&r,||Ok(())).is_err());drop(first);fs::remove_dir_all(r).unwrap();
 }
 #[test] fn cleanup_window_uses_actual_counts_and_rejects_a_stale_owner(){
  let r=root();fs::create_dir_all(&r).unwrap();phase(&r,"cleaning");cleanup_progress(&r,&serde_json::json!({"phase":"deleting","processed":12,"total":20,"freedBytes":2000000000u64}));
  assert!(waiting_message(&r).contains("12 / 20 files"));assert!(waiting_message(&r).contains("2.0 GB"));
  fs::write(r.join("launcher-state.json"),serde_json::json!({"phase":"cleaning","pid":0}).to_string()).unwrap();assert!(waiting_message(&r).contains("previous reset"));fs::remove_dir_all(r).unwrap();
 }
}
