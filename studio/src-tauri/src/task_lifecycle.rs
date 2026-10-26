// Native completion remains readable after a suspended/reloaded webview misses
// the transient event. Sleep inhibition belongs to this app, never a global setting.
use serde_json::Value;
use std::sync::Mutex;

pub struct PowerGuard {
    #[cfg(target_os="macos")] child:std::process::Child,
    #[cfg(windows)] stop:Option<std::sync::mpsc::Sender<()>>,
    #[cfg(windows)] thread:Option<std::thread::JoinHandle<()>>,
}
impl PowerGuard {
    pub fn start()->Result<Self,String>{
        #[cfg(target_os="macos")] {
            // -i permits display sleep; -w also releases the assertion if the
            // host crashes, even if Rust destructors cannot run.
            let child=std::process::Command::new("/usr/bin/caffeinate")
                .args(["-i","-w",&std::process::id().to_string()])
                .stdin(std::process::Stdio::null()).stdout(std::process::Stdio::null()).stderr(std::process::Stdio::null())
                .spawn().map_err(|e|e.to_string())?;
            return Ok(Self{child});
        }
        #[cfg(windows)] {
            // Windows assertions are thread-local. Create and release on the
            // same owned thread, not whichever async thread finishes the job.
            let (stop,wait)=std::sync::mpsc::channel();let (ready,ack)=std::sync::mpsc::channel();
            let thread=std::thread::spawn(move||{
                #[link(name="kernel32")] unsafe extern "system" {fn SetThreadExecutionState(flags:u32)->u32;}
                let ok=unsafe{SetThreadExecutionState(0x80000001)}!=0;
                let _=ready.send(ok);if ok{let _=wait.recv();unsafe{SetThreadExecutionState(0x80000000);}}
            });
            if !ack.recv().unwrap_or(false){drop(stop);let _=thread.join();return Err("Windows idle-sleep assertion unavailable".into());}
            return Ok(Self{stop:Some(stop),thread:Some(thread)});
        }
        #[cfg(not(any(target_os="macos",windows)))] Ok(Self{})
    }
}
impl Drop for PowerGuard {fn drop(&mut self){
    #[cfg(target_os="macos")] {let _=self.child.kill();let _=self.child.wait();}
    #[cfg(windows)] {self.stop.take();if let Some(thread)=self.thread.take(){let _=thread.join();}}
}}
#[derive(Default)] struct Record {finished:Option<Value>,power:Option<PowerGuard>}
#[derive(Default)] pub struct TaskLifecycle(Mutex<Record>);
impl TaskLifecycle {
    pub fn started(&self)->Result<(),String>{let mut record=self.0.lock().unwrap();if record.power.is_none(){record.power=Some(PowerGuard::start()?);}Ok(())}
    pub fn finished(&self,payload:Value){self.0.lock().unwrap().finished=Some(payload);}
    pub fn last_finished(&self)->Option<Value>{self.0.lock().unwrap().finished.clone()}
    pub fn release(&self,id:&str)->bool {
        let mut record=self.0.lock().unwrap();
        if record.finished.as_ref().is_some_and(|v|v["runID"]==id){record.power.take();true}else{false}
    }
    pub fn inhibited(&self)->bool {self.0.lock().unwrap().power.is_some()}
}
#[cfg(test)] mod tests {
    use super::*;
    #[test] fn completion_is_repeatable_and_stale_ack_cannot_release_new_run(){
        let life=TaskLifecycle::default();assert_eq!(life.last_finished(),None);
        life.finished(serde_json::json!({"runID":"first","rowID":"a","paused":false}));
        assert_eq!(life.last_finished(),life.last_finished());assert!(!life.release("old"));
        life.finished(serde_json::json!({"runID":"second","rowID":"b","paused":true}));
        assert!(!life.release("first"));assert!(life.release("second"));assert_eq!(life.last_finished().unwrap()["paused"],true);
    }
    #[test]
    #[cfg(target_os="macos")]
    fn actual_owned_idle_assertion_is_released_without_changing_display_sleep(){
        let guard=PowerGuard::start().unwrap();let pid=guard.child.id();
        let needle=format!("pid {pid}(caffeinate)");let mut observed=false;
        for _ in 0..30 {
            let raw=std::process::Command::new("/usr/bin/pmset").args(["-g","assertions"]).output().unwrap();
            let text=String::from_utf8_lossy(&raw.stdout);
            if text.lines().any(|line|line.contains(&needle)&&line.contains("PreventUserIdleSystemSleep")){observed=true;break;}
            std::thread::sleep(std::time::Duration::from_millis(100));
        }
        assert!(observed,"The owned idle-sleep assertion must actually exist");drop(guard);
        let raw=std::process::Command::new("/usr/bin/pmset").args(["-g","assertions"]).output().unwrap();assert!(!String::from_utf8_lossy(&raw.stdout).contains(&needle));
    }
}
