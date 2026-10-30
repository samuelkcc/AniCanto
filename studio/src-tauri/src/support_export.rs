//! Emergency diagnostics must work without Python, models or the policy helper.
use std::{fs,io::{Read,Seek,SeekFrom,Write},path::{Path,PathBuf},time::{SystemTime,UNIX_EPOCH}};
const LIMIT:u64=128*1024;
fn redact(text:&str)->String {
    text.lines().map(|line|{
        let lower=line.to_ascii_lowercase();
        if ["api_key","api-key","apikey","access_token","access-token","accesstoken","authorization","password","secret","\"token\"","ghp_","github_pat_","akia"].iter().any(|key|lower.contains(key)){
            "[Credential-bearing line omitted]".to_owned()
        }else{line.to_owned()}
    }).collect::<Vec<_>>().join("\n")
}
pub fn report(root:&Path,paths:&[(&str,&Path)],cause:&str,version:&str)->String {
    let mut text=format!("AniCanto {version} — native support report\nNormal export failed: {}\nSystem: {} / {}\nNo model or conversion was started.\n",redact(cause),std::env::consts::OS,std::env::consts::ARCH);
    for (name,path) in paths {
        let info=fs::metadata(path);
        text.push_str(&format!("\n{name}: {}\nFile present: {} · Bytes: {}\n",path.display(),info.as_ref().is_ok_and(|m|m.is_file()),info.map(|m|m.len()).unwrap_or(0)));
    }
    let base=match root.canonicalize(){Ok(p)=>p,Err(_)=>return text};
    for name in ["logs/python-readiness.json","logs/cleanup-error.json","last-download-cleanup.json","logs/studio/process.log","developer-process.log","logs/native-ollama.log","logs/launcher-startup.json","first-run-deployment.json","native-ready.json","gpu-runtime-selection.json","drama3-windows-ready.json","model-selections.json","setup-invalidated.json"] {
        if text.len()>1024*1024 {text.push_str("\n[Remaining sections omitted: report size limit]\n");break;}
        let path=match root.join(name).canonicalize(){Ok(p) if p.starts_with(&base)&&p.is_file()=>p,_=>continue};
        let result=(||->std::io::Result<String>{
            let mut f=fs::File::open(path)?;let size=f.metadata()?.len();f.seek(SeekFrom::Start(size.saturating_sub(LIMIT)))?;
            let mut raw=Vec::new();f.take(LIMIT).read_to_end(&mut raw)?;
            Ok(format!("{}{}",if size>LIMIT{"[Earlier bytes omitted]\n"}else{""},redact(&String::from_utf8_lossy(&raw))))
        })();
        text.push_str(&format!("\n===== {name} =====\n{}\n",result.unwrap_or_else(|e|format!("[Section unavailable: {e}]"))));
    }
    text.push_str("\nThis report can contain dialogue and local paths. Review it before public sharing.\n");text
}
pub fn save(root:&Path,preferred:&Path,text:&str)->Result<(PathBuf,bool),String>{
    match fs::write(preferred,text.as_bytes()) {
        Ok(())=>Ok((preferred.to_path_buf(),false)),
        Err(original)=>{
            let folder=root.join("logs");fs::create_dir_all(&folder).map_err(|e|format!("Selected location: {original}; support folder: {e}"))?;
            let base=root.canonicalize().map_err(|e|e.to_string())?;
            if !folder.canonicalize().map_err(|e|e.to_string())?.starts_with(&base){return Err(format!("Selected location: {original}; invalid support folder."));}
            let stamp=SystemTime::now().duration_since(UNIX_EPOCH).map_err(|e|e.to_string())?.as_nanos();
            let path=folder.join(format!("AniCanto-debug-{stamp}.txt"));let mut file=fs::OpenOptions::new().write(true).create_new(true).open(&path).map_err(|e|e.to_string())?;
            file.write_all(text.as_bytes()).map_err(|e|e.to_string())?;Ok((path,true))
        }
    }
}
#[cfg(test)] mod tests {
 use super::*;
 struct Fixture(PathBuf);
 impl Fixture {fn new()->Self{let stamp=SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos();let p=std::env::temp_dir().join(format!("anicanto-support-{}-{stamp}",std::process::id()));fs::create_dir_all(p.join("logs/studio")).unwrap();Self(p)}}
 impl Drop for Fixture {fn drop(&mut self){let _=fs::remove_dir_all(&self.0);}}
 #[test] fn missing_components_still_export_raw_failure(){let f=Fixture::new();fs::write(f.0.join("logs/studio/process.log"),"core missing\nloading failed").unwrap();let p=f.0.join("shared/bin/anicanto-core.exe");let r=report(&f.0,&[("Shared core",&p)],"Python unavailable","test");assert!(r.contains("core missing"));assert!(r.contains("Python unavailable"));assert!(r.contains("File present: false"));}
 #[test] fn secrets_are_removed_from_error_and_logs(){let f=Fixture::new();fs::write(f.0.join("logs/studio/process.log"),"api_key=do-not-export\nkeep diagnostic").unwrap();let r=report(&f.0,&[],"password=also-private","test");assert!(!r.contains("do-not-export"));assert!(!r.contains("also-private"));assert!(r.contains("keep diagnostic"));}
 #[test] fn unreadable_selected_location_uses_owned_support_copy(){let f=Fixture::new();let (path,recovered)=save(&f.0,&f.0.join("missing/cloud/report.txt"),"diagnostic").unwrap();assert!(recovered);assert!(path.starts_with(f.0.join("logs")));assert_eq!(fs::read_to_string(path).unwrap(),"diagnostic");}
 #[test] fn readable_selected_location_is_used(){let f=Fixture::new();let dest=f.0.join("report.txt");let (path,recovered)=save(&f.0,&dest,"diagnostic").unwrap();assert!(!recovered);assert_eq!(path,dest);}
 #[test] fn large_logs_are_bounded_and_keep_the_tail(){let f=Fixture::new();let mut raw=vec![b'x';300000];raw.extend_from_slice(b"\nlatest error");fs::write(f.0.join("logs/studio/process.log"),raw).unwrap();let r=report(&f.0,&[],"failure","test");assert!(r.len()<140000);assert!(r.contains("latest error"));assert!(r.contains("Earlier bytes omitted"));}
 #[cfg(unix)] #[test] fn symlink_logs_outside_the_app_are_not_read(){let f=Fixture::new();let outside=Fixture::new();fs::write(outside.0.join("private"),"outside secret text").unwrap();std::os::unix::fs::symlink(outside.0.join("private"),f.0.join("logs/studio/process.log")).unwrap();assert!(!report(&f.0,&[],"failure","test").contains("outside secret text"));}
}
