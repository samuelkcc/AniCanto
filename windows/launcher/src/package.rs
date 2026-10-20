use std::{fs,path::{Path,PathBuf},process::{Command,Stdio},thread,time::Duration};
use crate::splash::Splash;

static PAYLOAD:&[u8]=include_bytes!(concat!(env!("OUT_DIR"),"/payload.zip"));
static MANIFEST:&str=include_str!(concat!(env!("OUT_DIR"),"/manifest.json"));

/// Extract application code, never models/projects, into a content-addressed package cache.
pub fn folder(executable:&Path,progress:&Splash)->Result<PathBuf,String> {
    if PAYLOAD.is_empty() {return executable.parent().map(Path::to_path_buf).ok_or("Missing package directory".into());}
    let data=std::env::var_os("CANTOSYNC_WINDOWS_DATA").map(PathBuf::from).or_else(||std::env::var_os("LOCALAPPDATA").map(|p|PathBuf::from(p).join("CantoSync-Windows"))).ok_or("LOCALAPPDATA is unavailable")?;
    let packages=data.join("packages");fs::create_dir_all(&packages).map_err(|e|e.to_string())?;
    progress.update("Checking the portable app package…",0,0)?;
    let identity=anicanto_core::digest(PAYLOAD);
    let target=packages.join(&identity);
    if target.exists() {
        let verified=anicanto_core::verify_package_with_progress(&target,MANIFEST,
            |done,total|progress.update("Verifying installed app files…",done,total));
        if verified.is_ok() {return Ok(target);}
        // Cancellation is not evidence of a damaged cache.
        progress.update("Preparing app files…",0,0)?;
        // Repair only our content-addressed code cache. Never remove model or project data.
        let stamp=std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map_err(|e|e.to_string())?.as_nanos();
        fs::rename(&target,packages.join(format!("{identity}.rejected-{stamp}"))).map_err(|e|e.to_string())?;
    }
    let stage=packages.join(format!(".{}-{}",identity,std::process::id()));
    fs::create_dir(&stage).map_err(|e|format!("Cannot create package staging folder: {e}"))?;
    let result=(|| {
        let archive=stage.join("payload.zip");let content=stage.join("content");
        fs::write(&archive,PAYLOAD).map_err(|e|e.to_string())?;
        fs::create_dir(&content).map_err(|e|e.to_string())?;
        let total=serde_json::from_str::<serde_json::Value>(MANIFEST).map_err(|e|e.to_string())?
            .as_object().ok_or("Invalid package manifest")?.len();
        progress.update("Unpacking the app — first launch for this version…",0,total)?;
        // Native Windows tar supports ZIP and avoids slow PowerShell expansion.
        // Keep the legacy extractor only for systems without the native tool.
        let tar=std::env::var_os("SystemRoot").map(|p|PathBuf::from(p).join("System32/tar.exe"));
        let mut extraction=if let Some(tar)=tar.filter(|p|p.is_file()) {
            let mut c=Command::new(tar);c.arg("-xf").arg(&archive).arg("-C").arg(&content);c
        } else {
            let mut c=Command::new("powershell.exe");
            c.args(["-NoProfile","-NonInteractive","-Command",
                "$ErrorActionPreference='Stop'; Expand-Archive -LiteralPath $env:CANTO_PAYLOAD -DestinationPath $env:CANTO_DEST -Force"])
                .env("CANTO_PAYLOAD",&archive).env("CANTO_DEST",&content);c
        };
        let error_file=fs::File::create(stage.join("extraction.log")).map_err(|e|e.to_string())?;
        extraction.stdout(Stdio::null()).stderr(Stdio::from(error_file));
        #[cfg(target_os = "windows")]
        {use std::os::windows::process::CommandExt;extraction.creation_flags(0x08000000);}
        let mut child=extraction.spawn().map_err(|e|e.to_string())?;
        let status=loop {
            if let Err(error)=progress.update("Unpacking the app — first launch for this version…",file_count(&content),total) {
                let _=child.kill();let _=child.wait();return Err(error);
            }
            if let Some(status)=child.try_wait().map_err(|e|e.to_string())? {break status;}
            thread::sleep(Duration::from_millis(200));
        };
        if !status.success() {return Err("Portable package extraction failed; saved projects remain intact.".into());}
        anicanto_core::verify_package_with_progress(&content,MANIFEST,
            |done,total|progress.update("Verifying the new app package…",done,total))?;
        match fs::rename(&content,&target) {
            Ok(())=>Ok(target.clone()),
            Err(_) if target.exists()=>{anicanto_core::verify_package(&target,MANIFEST)?;Ok(target.clone())},
            Err(e)=>Err(e.to_string()),
        }
    })();
    let _=fs::remove_dir_all(stage);result
}

fn file_count(folder:&Path)->usize {
    fs::read_dir(folder).map(|rows|rows.filter_map(Result::ok).map(|entry|{
        match entry.file_type(){Ok(kind) if kind.is_dir()=>file_count(&entry.path()),Ok(kind) if kind.is_file()=>1,_=>0}
    }).sum()).unwrap_or(0)
}
