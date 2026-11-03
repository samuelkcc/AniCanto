//! Opt-in, read-only diagnostics. This service never invokes application RPC.
use std::{fs,io::{Read,Seek,SeekFrom,Write},net::{IpAddr,Ipv4Addr,SocketAddr,TcpListener,TcpStream,UdpSocket},path::{Path,PathBuf},sync::{Arc,Mutex,atomic::{AtomicBool,Ordering}},thread,time::Duration};
use serde_json::{json,Value};
#[derive(Default)]
pub struct Service(Mutex<Option<Running>>);
struct Running {stop:Arc<AtomicBool>,thread:Option<thread::JoinHandle<()>>,address:SocketAddr,token:String}
impl Drop for Running {fn drop(&mut self){self.stop.store(true,Ordering::Relaxed);if let Some(t)=self.thread.take(){let _=t.join();}}}
fn local(ip:IpAddr)->bool {match ip {IpAddr::V4(v)=>v.is_private()||v.is_loopback()||v.is_link_local(),_=>false}}
fn secret()->Result<String,String>{
 let mut bytes=[0u8;24];
 #[cfg(unix)] fs::File::open("/dev/urandom").and_then(|mut f|f.read_exact(&mut bytes)).map_err(|e|e.to_string())?;
 #[cfg(windows)] {#[link(name="bcrypt")] unsafe extern "system" {fn BCryptGenRandom(handle:isize,buffer:*mut u8,length:u32,flags:u32)->i32;}if unsafe{BCryptGenRandom(0,bytes.as_mut_ptr(),24,2)}!=0{return Err("Cannot create diagnostic access code.".into());}}
 Ok(bytes.iter().map(|b|format!("{b:02x}")).collect())
}
impl Service {
 pub fn status(&self)->Value {let guard=self.0.lock().unwrap();match guard.as_ref(){None=>json!({"enabled":false}),Some(r)=>{
 let mut urls=vec![format!("http://127.0.0.1:{}",r.address.port())];
 if r.address.ip().is_unspecified(){if let Ok(s)=UdpSocket::bind("0.0.0.0:0"){if s.connect("192.0.2.1:80").is_ok(){if let Ok(a)=s.local_addr(){if local(a.ip()){urls.insert(0,format!("http://{}:{}",a.ip(),r.address.port()));}}}}}else{urls=vec![format!("http://{}",r.address)];}
 json!({"enabled":true,"address":r.address.ip().to_string(),"port":r.address.port(),"urls":urls,"accessCode":r.token})}}}
 pub fn stop(&self){self.0.lock().unwrap().take();}
 pub fn start(&self,root:PathBuf,address:&str,port:u16)->Result<Value,String>{
 let ip:Ipv4Addr=address.parse().map_err(|_|"Enter a local IPv4 address or 0.0.0.0.")?;
 if !ip.is_unspecified()&&!local(IpAddr::V4(ip)){return Err("Use a private, link-local or loopback IPv4 address.".into());}
 let mut guard=self.0.lock().unwrap();if guard.is_some(){return Err("Stop diagnostics before changing the address or port.".into());}
 let listener=TcpListener::bind((ip,port)).map_err(|e|format!("Cannot open diagnostic address: {e}"))?;listener.set_nonblocking(true).map_err(|e|e.to_string())?;
 let address=listener.local_addr().map_err(|e|e.to_string())?;let token=secret()?;let key=token.clone();let stop=Arc::new(AtomicBool::new(false));let flag=stop.clone();
 let thread=thread::spawn(move||{while !flag.load(Ordering::Relaxed){match listener.accept(){Ok((mut stream,peer))=>{if local(peer.ip()){serve(&mut stream,&key,&root,address.port());}},Err(e) if e.kind()==std::io::ErrorKind::WouldBlock=>thread::sleep(Duration::from_millis(50)),Err(_)=>break}}});
 *guard=Some(Running{stop,thread:Some(thread),address,token});drop(guard);Ok(self.status())
 }
}
fn reply(stream:&mut TcpStream,status:&str,kind:&str,body:&str){let header=format!("HTTP/1.1 {status}\r\nContent-Type: {kind}; charset=utf-8\r\nContent-Length: {}\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nReferrer-Policy: no-referrer\r\nContent-Security-Policy: default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; form-action 'none'\r\nConnection: close\r\n\r\n",body.len());let _=stream.write_all(header.as_bytes());let _=stream.write_all(body.as_bytes());}
fn serve(stream:&mut TcpStream,key:&str,root:&Path,port:u16){
 let _=stream.set_read_timeout(Some(Duration::from_millis(500)));let _=stream.set_write_timeout(Some(Duration::from_millis(500)));
 let deadline=std::time::Instant::now();let mut raw=Vec::new();let mut b=[0;1024];while deadline.elapsed()<Duration::from_secs(1)&&raw.len()<8192&&!raw.ends_with(b"\r\n\r\n"){match stream.read(&mut b){Ok(0)=>break,Ok(n)=>raw.extend_from_slice(&b[..n]),Err(_)=>return}}
 if raw.len()>=8192||!raw.ends_with(b"\r\n\r\n"){reply(stream,"400 Bad Request","text/plain","Invalid request");return;}
 let text=String::from_utf8_lossy(&raw);let mut lines=text.split("\r\n");let request=lines.next().unwrap_or("");let headers:Vec<_>=lines.filter_map(|l|l.split_once(':')).map(|(k,v)|(k.to_ascii_lowercase(),v.trim())).collect();
 let get=|name:&str|headers.iter().find(|(k,_)|k==name).map(|(_,v)|*v);
 let valid_host=get("host").and_then(|h|h.parse::<SocketAddr>().ok()).is_some_and(|a|a.port()==port&&local(a.ip()));
 if !valid_host||get("origin").is_some_and(|o|Some(o.strip_prefix("http://").unwrap_or(""))!=get("host")){reply(stream,"403 Forbidden","text/plain","Local access only");return;}
 match request {
 "GET / HTTP/1.1"=>reply(stream,"200 OK","text/html",include_str!("../../diagnostics.html")),
 "GET /api/snapshot HTTP/1.1"=>{if get("authorization")!=Some(format!("Bearer {key}").as_str()){reply(stream,"401 Unauthorized","text/plain","Access code required");return;}reply(stream,"200 OK","application/json",&snapshot(root).to_string());},
 _=>reply(stream,"404 Not Found","text/plain","Read-only diagnostic endpoint not found")}
}
fn clean_json(v:&mut Value){match v {Value::Object(m)=>{for(k,v)in m.iter_mut(){let k=k.to_ascii_lowercase();if ["password","secret","token","authorization","api_key","apikey","api-key","credential"].iter().any(|x|k.contains(x)){*v=json!("[Credential omitted]");}else{clean_json(v);}}},Value::Array(a)=>for v in a{clean_json(v)},Value::String(t)=>*t=crate::support_export::redact(t),_=>{}}}
fn read_owned(root:&Path,path:&Path,limit:u64)->Value {
 let base=match root.canonicalize(){Ok(p)=>p,Err(e)=>return json!({"error":e.to_string()})};
 let p=match path.canonicalize(){Ok(p) if p.starts_with(&base)&&p.is_file()=>p,_=>return json!({"unavailable":true})};
 let result=(||->std::io::Result<Value>{let mut f=fs::File::open(p)?;let size=f.metadata()?.len();f.seek(SeekFrom::Start(size.saturating_sub(limit)))?;let mut data=Vec::new();f.take(limit).read_to_end(&mut data)?;let raw=String::from_utf8_lossy(&data);let text=if size<=limit {if let Ok(mut v)=serde_json::from_str::<Value>(&raw){clean_json(&mut v);serde_json::to_string_pretty(&v).unwrap_or_default()}else{crate::support_export::redact(&raw)}}else{crate::support_export::redact(&raw)};Ok(json!({"bytes":size,"truncated":size>limit,"text":text}))})();result.unwrap_or_else(|e|json!({"error":e.to_string()}))
}
fn snapshot(root:&Path)->Value {
 let mut files=serde_json::Map::new();
 for name in ["studio/desktop-state.json","model-selections.json","native-ready.json","gpu-runtime-selection.json","logs/python-readiness.json","logs/cleanup-error.json","logs/launcher-startup.json","source-preparation/current.json","developer-process.log","logs/studio/process.log","logs/native-host.log","logs/native-ollama.log","mlx-text.log","ollama.log"] {files.insert(name.into(),read_owned(root,&root.join(name),if name.ends_with("desktop-state.json"){2*1024*1024}else{65536}));}
 // Read only known evidence under app-owned job and attempt roots.
 if let Ok(raw)=fs::read(root.join("studio/desktop-state.json")){if raw.len()<=2*1024*1024 {if let Ok(state)=serde_json::from_slice::<Value>(&raw){if let Some(queue)=state["queue"].as_array(){for row in queue.iter().rev().take(12){for (directory,names) in [(row["job"].as_str(), &["production-progress.json","report.json","processing-time.json","segment-issues.json","process.log"][..]),(row["attempt"]["path"].as_str(), &["process.log","attempt.json","request.json"][..])] {if let Some(dir)=directory {let dir=PathBuf::from(dir);let base=root.canonicalize().unwrap_or_default();if !dir.canonicalize().is_ok_and(|p|p.starts_with(base.join("jobs"))||p.starts_with(base.join("attempts"))){continue;}for name in names {let p=dir.join(name);if p.is_file(){files.insert(p.strip_prefix(root).unwrap_or(&p).to_string_lossy().into_owned(),read_owned(root,&p,32768));}}}}}}}}}
 // Enumerate only app-owned attempts and logs. No user media or model weights.
 for folder in ["attempts","logs"] {let dir=root.join(folder);if !dir.canonicalize().is_ok_and(|p|p.starts_with(root.canonicalize().unwrap_or_default())){continue;}if let Ok(entries)=fs::read_dir(dir){let mut paths:Vec<_>=entries.filter_map(Result::ok).map(|e|e.path()).collect();paths.sort_by_key(|p|std::cmp::Reverse(p.metadata().and_then(|m|m.modified()).ok()));for p in paths.into_iter().take(16){for p in [p.join("process.log"),p.join("attempt.json"),p.clone()] {if p.extension().is_some_and(|e|e=="log"||e=="json")&&p.is_file(){let name=p.strip_prefix(root).unwrap().to_string_lossy().into_owned();files.insert(name,read_owned(root,&p,32768));}}}}}
 json!({"format":"AniCanto LAN diagnostics v1","version":env!("CARGO_PKG_VERSION"),"system":std::env::consts::OS,"hostPID":std::process::id(),"observedAt":std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap_or_default().as_secs(),"scope":"Saved settings and frozen requests; bounded log tails. Missing and truncated sources are marked. Credentials are omitted by line. No media or model files.","files":files})
}
#[cfg(test)] mod tests {
 use super::*;
 #[test] fn lifecycle_auth_and_snapshot(){let root=std::env::temp_dir().join(format!("anicanto-lan-{}",std::process::id()));fs::create_dir_all(root.join("studio")).unwrap();fs::write(root.join("studio/desktop-state.json"),"{\n\"settings\": {\"test\": 7},\n\"password\": \"hidden\"\n}").unwrap();let s=Service::default();assert_eq!(s.status()["enabled"],false);let v=s.start(root.clone(),"127.0.0.1",0).unwrap();let port=v["port"].as_u64().unwrap();let request=|auth:&str|{let mut c=TcpStream::connect(format!("127.0.0.1:{port}")).unwrap();write!(c,"GET /api/snapshot HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n{auth}\r\n").unwrap();let mut out=String::new();c.read_to_string(&mut out).unwrap();out};assert!(request("").contains("401 Unauthorized"));let out=request(&format!("Authorization: Bearer {}\r\n",v["accessCode"].as_str().unwrap()));assert!(out.contains("200 OK"));assert!(out.contains("test"));assert!(!out.contains("hidden"));s.stop();assert_eq!(s.status()["enabled"],false);assert!(TcpStream::connect(format!("127.0.0.1:{port}")).is_err());fs::remove_dir_all(root).unwrap();}
 #[test] fn structured_credentials_do_not_hide_settings(){let mut v=json!({"settings":{"model":"test","apiKey":"private-value"},"queue":[{"request":{"seed":7}}]});clean_json(&mut v);assert_eq!(v["settings"]["model"],"test");assert_eq!(v["queue"][0]["request"]["seed"],7);assert!(!v.to_string().contains("private-value"));}
 #[cfg(unix)] #[test] fn external_link_is_unavailable(){let root=std::env::temp_dir().join(format!("anicanto-lan-link-{}",std::process::id()));fs::create_dir_all(&root).unwrap();std::os::unix::fs::symlink("/etc/hosts",root.join("escape")).unwrap();assert_eq!(read_owned(&root,&root.join("escape"),100)["unavailable"],true);fs::remove_dir_all(root).unwrap();}
 #[test] fn unsafe_bind_rejected(){assert!(Service::default().start(PathBuf::new(),"8.8.8.8",0).is_err());}
}
