#![cfg_attr(target_os = "windows", windows_subsystem = "windows")]

use std::path::PathBuf;
use std::process::Command;
mod package;
mod splash;

// The portable EXE stays outside the downloaded runtime. Run cleanup only
// after the desktop and its loaded Python/DLL files have exited.
fn pending_cleanup(root:&std::path::Path,executable:&std::path::Path)->Result<(),String> {
    let file=root.join("download-cleanup-request.json");
    if !file.is_file() {return Ok(());}
    if std::fs::metadata(&file).map_err(|e|e.to_string())?.len()>16384 {return Err("Invalid cleanup request".into());}
    let req:serde_json::Value=serde_json::from_slice(&std::fs::read(&file).map_err(|e|e.to_string())?).map_err(|e|e.to_string())?;
    if req["launcherPID"].as_u64()!=Some(std::process::id() as u64) {return Ok(());}
    // Never remove a running EXE if the user stored it in a managed folder.
    if let (Ok(exe),Ok(storage))=(executable.canonicalize(),root.canonicalize()) {
        if exe.starts_with(storage) {return Err("Move AniCanto.exe outside the app data folder before removing downloads.".into());}
    }
    let request=serde_json::json!({"root":root,"mode":req["mode"],"token":req["token"]});
    let result=anicanto_core::cleanup::execute(&request);
    // A request is one-shot, including failure; always review a new plan.
    std::fs::remove_file(file).map_err(|e|e.to_string())?;
    let result=result?;
    if result["complete"]!=true {return Err(format!("Some downloaded files could not be removed. Projects and exports are kept. See last-download-cleanup.json in the app data folder. {}",result["failures"]));}
    Ok(())
}

#[cfg(target_os = "windows")]
fn show_error(message: &str) {
    #[link(name = "user32")]
    extern "system" {
        fn MessageBoxW(window: *mut std::ffi::c_void, text: *const u16,
                       caption: *const u16, style: u32) -> i32;
    }
    let text: Vec<u16> = message.encode_utf16().chain(Some(0)).collect();
    let title: Vec<u16> = "AniCanto Windows".encode_utf16().chain(Some(0)).collect();
    unsafe { MessageBoxW(std::ptr::null_mut(), text.as_ptr(), title.as_ptr(), 0x10); }
}

#[cfg(not(target_os = "windows"))]
fn show_error(message: &str) { eprintln!("{message}"); }

fn launch() -> Result<(), String> {
    let splash=splash::Splash::new();
    let started=std::time::Instant::now();
    let executable = std::env::current_exe().map_err(|error| error.to_string())?;
    let folder = package::folder(&executable,&splash)?;
    let package_seconds=started.elapsed().as_secs_f64();
    let bootstrap: PathBuf = folder.join("bootstrap.ps1");
    if !bootstrap.is_file() || !folder.join("desktop.py").is_file() {
        return Err("The embedded AniCanto desktop is incomplete. Copy AniCanto.exe again; saved projects are retained.".into());
    }
    // Once the isolated UI has been verified for this requirements identity,
    // launch it directly without a second console window on every start.
    let root = std::env::var_os("CANTOSYNC_WINDOWS_DATA").map(PathBuf::from)
        .or_else(|| std::env::var_os("LOCALAPPDATA").map(|p| PathBuf::from(p).join("CantoSync-Windows")))
        .ok_or("LOCALAPPDATA is unavailable")?;
    // Both platforms now use the same embedded Tauri view. It opens before
    // Python exists; first-run deployment belongs to that common Welcome UI.
    let studio=folder.join("tools/AniCanto-Studio.exe");
    if studio.is_file() {
        let logs=root.join("logs");std::fs::create_dir_all(&logs).map_err(|e|e.to_string())?;
        let ready=logs.join(format!("launch-ready-{}.json",std::process::id()));
        let _=std::fs::remove_file(&ready);
        let mut desktop=Command::new(studio);
        desktop.env("CANTOSYNC_WINDOWS_PACKAGE",&folder).env("CANTOSYNC_WINDOWS_DATA",&root)
            .env("CANTOSYNC_SHARED_RESOURCES",folder.join("shared")).env("CANTOSYNC_CORE",folder.join("shared/bin/anicanto-core.exe"))
            .env("CANTOSYNC_STUDIO_DATA",&root).env("CANTOSYNC_LAUNCHER_PID",std::process::id().to_string())
            .env("CANTOSYNC_LAUNCH_READY_PATH",&ready);
        #[cfg(target_os="windows")]
        {use std::os::windows::process::CommandExt;desktop.creation_flags(0x08000000);}
        splash.update("Opening the studio window…",0,0)?;
        let mut child=desktop.spawn().map_err(|e|e.to_string())?;
        while !ready.is_file() {
            if let Err(error)=splash.update("Opening the studio window…",0,0){let _=child.kill();let _=child.wait();return Err(error);}
            if let Some(status)=child.try_wait().map_err(|e|e.to_string())? {
                return Err(format!("The studio window could not open ({status}). Saved projects and models are retained."));
            }
            std::thread::sleep(std::time::Duration::from_millis(100));
        }
        let _=std::fs::remove_file(&ready);
        let timing=serde_json::json!({"packageSeconds":package_seconds,"windowReadySeconds":started.elapsed().as_secs_f64(),"integrityCheck":"full-sha256"});
        let _=std::fs::write(logs.join("launcher-startup.json"),timing.to_string());
        drop(splash);
        let status=child.wait().map_err(|e|e.to_string())?;
        pending_cleanup(&root,&executable)?;
        return if status.success(){Ok(())}else{Err("AniCanto Studio closed with an error. Projects and recordings are retained.".into())};
    }
    drop(splash); // The legacy adapter displays its own runtime setup window.
    let python = root.join("runtimes/ui/Scripts/pythonw.exe");
    let ready = root.join("ui-ready.txt");
    if python.is_file() && ready.is_file() {
        // Python checks the small requirements digest before the fast path;
        // a newer package requiring different wheels returns to bootstrap.
        let py = root.join("runtimes/ui/Scripts/python.exe");
        let mut check = Command::new(py);
        check.arg("-c").arg("import hashlib,pathlib,sys; import PySide6.QtWidgets,av,numpy,soundfile,imageio_ffmpeg,httpx; p=pathlib.Path(sys.argv[1]); sys.exit(0 if pathlib.Path(sys.argv[2]).read_text().strip()==hashlib.sha256(p.read_bytes()).hexdigest() else 2)")
            .arg(folder.join("requirements-ui.txt")).arg(&ready);
        #[cfg(target_os = "windows")]
        {use std::os::windows::process::CommandExt;check.creation_flags(0x08000000);}
        if check.status().is_ok_and(|s| s.success()) {
            let mut desktop = Command::new(python);
            desktop.arg(folder.join("desktop.py")).current_dir(&folder)
                .env("PYTHONUTF8","1").env("PYTHONDONTWRITEBYTECODE","1")
                .env("CANTOSYNC_WINDOWS_DATA",&root);
            desktop.env("CANTOSYNC_LAUNCHER_PID",std::process::id().to_string());
            #[cfg(target_os = "windows")]
            {use std::os::windows::process::CommandExt;desktop.creation_flags(0x08000000);}
            let log_dir=root.join("logs");std::fs::create_dir_all(&log_dir).map_err(|e|e.to_string())?;
            let log=std::fs::OpenOptions::new().create(true).append(true).open(log_dir.join("desktop-startup.log")).map_err(|e|e.to_string())?;
            desktop.stdout(log.try_clone().map_err(|e|e.to_string())?).stderr(log);
            let status=desktop.status().map_err(|e|e.to_string())?;
            pending_cleanup(&root,&executable)?;
            return if status.success(){Ok(())}else{Err("Desktop startup failed. See desktop-startup.log in the local AniCanto logs folder.".into())};
        }
    }
    let mut command = Command::new("powershell.exe");
    command.args(["-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-File"])
           .arg(bootstrap).current_dir(&folder);
    command.env("CANTOSYNC_LAUNCHER_PID",std::process::id().to_string());
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        // The first setup shows download progress; subsequent starts use the
        // same isolated runtime. No system Python or global package changes.
        command.creation_flags(0x08000000); // CREATE_NO_WINDOW; bootstrap owns its progress window
    }
    let status = command.status().map_err(|error| format!("Could not start Windows setup: {error}"))?;
    pending_cleanup(&root,&executable)?;
    if !status.success() {
        return Err("Setup or desktop startup failed. Read the newest log in %LOCALAPPDATA%\\CantoSync-Windows\\logs. Your saved recordings and projects are retained.".into());
    }
    Ok(())
}

fn main() {
    // Same hardware implementation and catalog as the macOS policy executable.
    if std::env::args().any(|arg| arg == "--diagnostics") {
        println!("{}", anicanto_core::hardware());
        return;
    }
    if let Err(error) = launch() {
        show_error(&error);
        std::process::exit(1);
    }
}

#[cfg(test)] mod tests {
    use super::*;
    #[test] fn cleanup_is_owned_by_the_requesting_launcher_only() {
        let root=std::env::temp_dir().join(format!("anicanto-launch-cleanup-{}",std::process::id()));
        std::fs::create_dir_all(root.join("runtimes/ui")).unwrap();
        std::fs::write(root.join("desktop-state.json"),"{}").unwrap();
        std::fs::write(root.join("runtimes/ui/python.exe"),"runtime").unwrap();
        std::fs::create_dir_all(root.join("exports")).unwrap();
        std::fs::write(root.join("exports/keep.mp4"),"export").unwrap();
        let plan=anicanto_core::cleanup::plan(&serde_json::json!({"root":root,"mode":"all"})).unwrap();
        let file=root.join("download-cleanup-request.json");
        let mut request=serde_json::json!({"mode":"all","token":plan["token"],"launcherPID":std::process::id() as u64+1});
        std::fs::write(&file,request.to_string()).unwrap();
        let exe=std::env::current_exe().unwrap();pending_cleanup(&root,&exe).unwrap();
        assert!(root.join("runtimes/ui/python.exe").is_file());assert!(file.exists());
        request["launcherPID"]=serde_json::json!(std::process::id());std::fs::write(&file,request.to_string()).unwrap();
        pending_cleanup(&root,&exe).unwrap();assert!(!root.join("runtimes/ui/python.exe").exists());assert!(root.join("exports/keep.mp4").is_file());assert!(!file.exists());
        std::fs::remove_dir_all(root).unwrap();
    }
}
