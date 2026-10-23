//! Private media dispatcher: never re-extract/hash the large portable payload
//! for every OCR/ASR/caption request from the shared production worker.
use std::path::PathBuf;
use std::process::{Command, Stdio};

fn run() -> Result<i32, String> {
    let args: Vec<_> = std::env::args_os().skip(1).collect();
    let first = args.first().and_then(|a| a.to_str()).ok_or("Missing media action")?;
    let runtime = match first {
        "--traditional-text" | "--simplified-text" | "--ocr" | "--render-subtitles" => "worker",
        "--classify-opening" | "--classify-performance" => "analysis",
        _ => return Err("Unsupported AniCanto media action".into()),
    };
    let executable = std::env::current_exe().map_err(|e| e.to_string())?;
    let package = executable.parent().and_then(|p| p.parent()).ok_or("Invalid helper location")?;
    let root = if let Some(value) = std::env::var_os("CANTOSYNC_WINDOWS_DATA") {
        PathBuf::from(value)
    } else {
        PathBuf::from(std::env::var_os("LOCALAPPDATA").ok_or("LOCALAPPDATA is unavailable")?)
            .join("CantoSync-Windows")
    };
    let python = root.join("runtimes").join(runtime).join("Scripts/python.exe");
    let script = package.join("native_tools.py");
    if !python.is_file() || !script.is_file() {
        return Err("Complete or repair the AniCanto native setup before processing media".into());
    }
    let paths = std::env::join_paths([package.to_path_buf(), package.join("shared")])
        .map_err(|e| e.to_string())?;
    let mut command = Command::new(python);
    command.arg(script).args(args).current_dir(package)
        .env("PYTHONUTF8", "1").env("PYTHONDONTWRITEBYTECODE", "1")
        .env("PYTHONPATH", paths).env("CANTOSYNC_WINDOWS_PACKAGE", package)
        .stdin(Stdio::inherit()).stdout(Stdio::inherit()).stderr(Stdio::inherit());
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000); // CREATE_NO_WINDOW
    }
    let status = command.status().map_err(|e| format!("Media helper could not start: {e}"))?;
    Ok(status.code().unwrap_or(1))
}

fn main() {
    match run() {
        Ok(code) => std::process::exit(code),
        Err(error) => { eprintln!("{error}"); std::process::exit(1); }
    }
}
