//! Owned source playback. No loopback service can outlive the native host.
use std::{io::{BufRead,BufReader,Write},process::{Child,Command,Stdio},sync::{Mutex,OnceLock},time::Duration};
use serde_json::Value;
struct Stream { child:Child,id:String }
static STREAMS:OnceLock<Mutex<Vec<Stream>>>=OnceLock::new();
fn streams()-> &'static Mutex<Vec<Stream>> {STREAMS.get_or_init(||Mutex::new(Vec::new()))}
fn terminate(stream:&mut Stream){
    #[cfg(unix)] unsafe {libc::kill(-(stream.child.id() as i32),libc::SIGTERM);}
    let _=stream.child.kill();let _=stream.child.wait();
}
pub fn stop(id:&str){let mut rows=streams().lock().unwrap();if let Some(n)=rows.iter().position(|s|s.id==id){terminate(&mut rows.remove(n));}}
pub fn stop_all(){let mut rows=streams().lock().unwrap();for s in rows.iter_mut(){terminate(s);}rows.clear();}
pub fn start(python:&std::path::Path,script:&std::path::Path,mut config:Value)->Result<Value,String>{
    config["owner"]=serde_json::json!(std::process::id());
    let mut command=Command::new(python);command.arg(script).stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null());
    #[cfg(unix)] {use std::os::unix::process::CommandExt;unsafe{command.pre_exec(||{if libc::setpgid(0,0)==-1{return Err(std::io::Error::last_os_error());}Ok(())});}}
    let mut child=command.spawn().map_err(|e|e.to_string())?;
    let input=format!("{}\n",config);if let Err(e)=child.stdin.take().unwrap().write_all(input.as_bytes()){let _=child.kill();let _=child.wait();return Err(e.to_string());}
    let output=child.stdout.take().unwrap();let(tx,rx)=std::sync::mpsc::channel();
    std::thread::spawn(move||{let mut line=String::new();let result=BufReader::new(output).read_line(&mut line).map(|_|line);let _=tx.send(result);});
    let response=rx.recv_timeout(Duration::from_secs(8)).map_err(|_|"Source playback did not start.".to_string()).and_then(|r|r.map_err(|e|e.to_string())).and_then(|line|serde_json::from_str::<Value>(&line).map_err(|e|e.to_string()));
    let result=match response{Ok(v) if v["streamID"].as_str().is_some_and(|s|s.len()>20)&&v["url"].as_str().is_some_and(|s|s.starts_with("http://127.0.0.1:"))=>v,_=>{let _=child.kill();let _=child.wait();return Err("Source playback service could not start.".into());}};
    let mut rows=streams().lock().unwrap();rows.retain_mut(|s|s.child.try_wait().ok().flatten().is_none());
    // The page closes previous streams. Bound even stale or failed IPC callers.
    while rows.len()>=2 {terminate(&mut rows.remove(0));}
    rows.push(Stream{child,id:result["streamID"].as_str().unwrap().into()});Ok(result)
}

#[cfg(all(test,unix))]
mod tests {
 use super::*;
 #[test]
 fn native_owner_stops_only_its_selected_session(){
  let root=std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../Resources/studio_stream.py");
  let config=serde_json::json!({"source":"unused-fixture.mkv","duration":6,"audioStream":null,"ffmpeg":"unused-fixture"});
  let a=start(std::path::Path::new("/usr/bin/python3"),&root,config.clone()).unwrap();
  let b=start(std::path::Path::new("/usr/bin/python3"),&root,config).unwrap();
  assert_ne!(a["streamID"],b["streamID"]);stop(a["streamID"].as_str().unwrap());
  let address=b["url"].as_str().unwrap().strip_prefix("http://").unwrap().split('/').next().unwrap();
  assert!(std::net::TcpStream::connect(address).is_ok());stop(b["streamID"].as_str().unwrap());
  assert!(std::net::TcpStream::connect(address).is_err());
 }
}
