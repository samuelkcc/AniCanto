use std::{fs,path::PathBuf,sync::atomic::{AtomicU64,Ordering}};
use anicanto_core::{digest,verify_package};
use anicanto_core::verify_package_with_progress;
#[test] fn verification_progress_counts_verified_files_and_can_cancel(){
    let t=Temp::new();fs::write(t.0.join("app.py"),b"safe").unwrap();let mut steps=Vec::new();
    verify_package_with_progress(&t.0,&manifest(),|done,total|{steps.push((done,total));Ok(())}).unwrap();
    assert_eq!(steps,vec![(0,1),(1,1)]);
    assert_eq!(verify_package_with_progress(&t.0,&manifest(),|_,_|Err("cancelled".into())).unwrap_err(),"cancelled");
    fs::write(t.0.join("app.py"),b"evil").unwrap();
    assert!(verify_package_with_progress(&t.0,&manifest(),|_,_|Ok(())).unwrap_err().contains("changed"));
}
struct Temp(PathBuf);
static NEXT_TEMP:AtomicU64=AtomicU64::new(0);
impl Temp {
    fn new()->Self {
        // Concurrent tests can observe the same wall-clock tick, especially on
        // Windows. Reserve each directory atomically and tolerate stale names.
        loop {
            let sequence=NEXT_TEMP.fetch_add(1,Ordering::Relaxed);
            let path=std::env::temp_dir().join(format!("anicanto-test-{}-{sequence}",std::process::id()));
            match fs::create_dir(&path) {
                Ok(())=>return Self(path),
                Err(error) if error.kind()==std::io::ErrorKind::AlreadyExists=>continue,
                Err(error)=>panic!("Cannot create test directory: {error}"),
            }
        }
    }
}
impl Drop for Temp {fn drop(&mut self){let _=fs::remove_dir_all(&self.0);}}
fn manifest()->String {serde_json::json!({"app.py":{"size":4,"sha256":digest(b"safe")}}).to_string()}
#[test] fn intact_package_passes(){let t=Temp::new();fs::write(t.0.join("app.py"),b"safe").unwrap();verify_package(&t.0,&manifest()).unwrap();}
#[test] fn changed_file_fails_even_at_same_size(){let t=Temp::new();fs::write(t.0.join("app.py"),b"evil").unwrap();assert!(verify_package(&t.0,&manifest()).unwrap_err().contains("changed"));}
#[test] fn missing_file_fails(){let t=Temp::new();assert!(verify_package(&t.0,&manifest()).is_err());}
#[test] fn unsafe_paths_fail(){let t=Temp::new();for path in ["../outside","/outside","C:/outside","folder\\outside"] {let m=serde_json::json!({path:{"size":0,"sha256":digest(b"")}});assert_eq!(verify_package(&t.0,&m.to_string()).unwrap_err(),"invalid-package-path");}}
#[test] fn empty_manifest_cannot_certify_package(){let t=Temp::new();assert!(verify_package(&t.0,"{}").is_err());}
#[cfg(unix)] #[test] fn symlink_file_fails(){let t=Temp::new();let outside=Temp::new();fs::write(outside.0.join("original"),b"safe").unwrap();std::os::unix::fs::symlink(outside.0.join("original"),t.0.join("app.py")).unwrap();assert_eq!(verify_package(&t.0,&manifest()).unwrap_err(),"package-symlink");}
