//! Owned source playback. No loopback service can outlive the native host.
use std::{io::{BufRead,BufReader,Write},process::{Child,Command,Stdio},sync::Mutex,time::Duration};
use serde_json::Value;
struct Stream { child:Child,id:Option<String>, #[cfg(windows)] _job:Option<crate::OwnedJob> }
#[derive(Default)]
struct Sessions {
    closed: bool,
    streams: Vec<Stream>,
}
#[derive(Default)]
pub struct Service(Mutex<Sessions>);

fn terminate(stream:&mut Stream){
    #[cfg(unix)] unsafe {libc::kill(-(stream.child.id() as i32),libc::SIGKILL);}
    #[cfg(windows)] stream._job.take();
    let _=stream.child.kill();let _=stream.child.wait();
}
impl Service {
pub fn stop(&self,id:&str){
    let mut sessions=self.0.lock().unwrap();
    if let Some(index)=sessions.streams.iter().position(|stream|stream.id.as_deref()==Some(id)){
        terminate(&mut sessions.streams.remove(index));
    }
}
pub fn stop_all(&self){
    let mut sessions=self.0.lock().unwrap();
    sessions.closed=true;
    for mut stream in sessions.streams.drain(..){terminate(&mut stream);}
}
pub fn start(&self,python:&std::path::Path,script:&std::path::Path,mut config:Value)->Result<Value,String>{
    config["owner"]=serde_json::json!(std::process::id());
    let mut command=Command::new(python);command.arg(script).stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null());
    #[cfg(unix)] {use std::os::unix::process::CommandExt;command.process_group(0);}
    // Register the child before waiting for readiness. Quit can stop it during startup.
    let (pid,output)={
        let mut sessions=self.0.lock().unwrap();
        if sessions.closed{return Err("AniCanto is closing.".into());}
        let child=command.spawn().map_err(|error|error.to_string())?;
        #[cfg(windows)] let owned_job=match crate::OwnedJob::assign(&child){Ok(job)=>job,Err(error)=>{let mut child=child;let _=child.kill();let _=child.wait();return Err(error)}};
        let mut stream=Stream{child,id:None,#[cfg(windows)] _job:Some(owned_job)};
        let input=format!("{config}\n");
        if let Err(error)=stream.child.stdin.take().unwrap().write_all(input.as_bytes()){
            terminate(&mut stream);
            return Err(error.to_string());
        }
        let output=stream.child.stdout.take().unwrap();
        let pid=stream.child.id();
        sessions.streams.push(stream);
        (pid,output)
    };
    let(tx,rx)=std::sync::mpsc::channel();
    std::thread::spawn(move||{let mut line=String::new();let result=BufReader::new(output).read_line(&mut line).map(|_|line);let _=tx.send(result);});
    let response=rx.recv_timeout(Duration::from_secs(8)).map_err(|_|"Source playback did not start.".to_string()).and_then(|r|r.map_err(|e|e.to_string())).and_then(|line|serde_json::from_str::<Value>(&line).map_err(|e|e.to_string()));
    let mut sessions=self.0.lock().unwrap();
    let rows=&mut sessions.streams;
    let index=rows.iter().position(|stream|stream.child.id()==pid).ok_or("AniCanto is closing.")?;
    let result=match response{
        Ok(v) if v["streamID"].as_str().is_some_and(|s|s.len()>20)&&v["url"].as_str().is_some_and(|s|s.starts_with("http://127.0.0.1:"))=>v,
        _=>{terminate(&mut rows.remove(index));return Err("Source playback service could not start.".into());}
    };
    let mut stream=rows.remove(index);
    stream.id=result["streamID"].as_str().map(str::to_owned);
    rows.retain_mut(|s|s.id.is_none()||s.child.try_wait().ok().flatten().is_none());
    while rows.iter().filter(|s|s.id.is_some()).count()>=2 {
        let oldest=rows.iter().position(|s|s.id.is_some()).unwrap();
        terminate(&mut rows.remove(oldest));
    }
    rows.push(stream);
    Ok(result)
}
}

#[cfg(all(test,unix))]
mod tests {
 use super::*;
 #[test]
 fn native_owner_stops_only_its_selected_session(){
  let root=std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../Resources/studio_stream.py");
  let config=serde_json::json!({"source":"unused-fixture.mkv","duration":6,"audioStream":null,"ffmpeg":"unused-fixture"});
  let service=Service::default();
  let a=service.start(std::path::Path::new("/usr/bin/python3"),&root,config.clone()).unwrap();
  let b=service.start(std::path::Path::new("/usr/bin/python3"),&root,config.clone()).unwrap();
  assert_ne!(a["streamID"],b["streamID"]);service.stop(a["streamID"].as_str().unwrap());
  let address=b["url"].as_str().unwrap().strip_prefix("http://").unwrap().split('/').next().unwrap();
  assert!(std::net::TcpStream::connect(address).is_ok());service.stop_all();
  assert!(std::net::TcpStream::connect(address).is_err());
  assert!(service.start(std::path::Path::new("/usr/bin/python3"),&root,config).is_err());
 }
 #[test]
 fn closing_reaps_playback_even_before_it_reports_ready(){
    let service=Service::default();
    let fixture=std::env::temp_dir().join(format!("anicanto-preview-start-{}.sh",std::process::id()));
    std::fs::write(&fixture,"exec /bin/sleep 60\n").unwrap();
    std::thread::scope(|scope|{
        let waiting=scope.spawn(||service.start(std::path::Path::new("/bin/sh"),&fixture,serde_json::json!({})));
        let deadline=std::time::Instant::now()+Duration::from_secs(2);
        let pid=loop{
            if let Some(stream)=service.0.lock().unwrap().streams.first(){break stream.child.id();}
            assert!(std::time::Instant::now()<deadline,"The fixture did not start.");
            std::thread::sleep(Duration::from_millis(10));
        };
        service.stop_all();
        assert_eq!(waiting.join().unwrap().unwrap_err(),"AniCanto is closing.");
        assert_eq!(unsafe{libc::kill(pid as i32,0)},-1);
        assert_eq!(std::io::Error::last_os_error().raw_os_error(),Some(libc::ESRCH));
    });
    std::fs::remove_file(fixture).unwrap();
 }
}
