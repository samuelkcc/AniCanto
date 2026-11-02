//! Move the data directory once. Keep old absolute paths valid through an alias.
use std::{fs, fs::OpenOptions, path::{Path, PathBuf}};
use fs2::FileExt;

fn link_directory(target: &Path, link: &Path) -> std::io::Result<()> {
    #[cfg(unix)] { std::os::unix::fs::symlink(target, link) }
    #[cfg(windows)] {
        if std::os::windows::fs::symlink_dir(target, link).is_ok(){return Ok(());}
        // A junction supports ordinary Windows accounts without symlink privileges.
        // Paths enter as environment values, never as PowerShell source text.
        use std::os::windows::process::CommandExt;
        let result=std::process::Command::new("powershell.exe")
            .args(["-NoProfile","-NonInteractive","-Command",
                "$ErrorActionPreference='Stop'; New-Item -ItemType Junction -Path $env:ANICANTO_ALIAS_PATH -Target $env:ANICANTO_ALIAS_TARGET | Out-Null"])
            .env("ANICANTO_ALIAS_PATH",link).env("ANICANTO_ALIAS_TARGET",target)
            .creation_flags(0x08000000).output()?;
        if result.status.success(){Ok(())}else{Err(std::io::Error::other("Could not create the legacy data alias."))}
    }
}

pub fn select(parent: &Path, legacy_name: &str) -> Result<PathBuf, String> {
    let current = parent.join("AniCanto");
    let legacy = parent.join(legacy_name);
    if current.exists() {
        if !current.is_dir(){return Err("AniCanto data path is not a directory. Keep the file and review this location.".into());}
        if legacy.exists() && !legacy.symlink_metadata().is_ok_and(|m|m.file_type().is_symlink()) {
            return Err("Both AniCanto and legacy data directories exist. Keep both and resolve their contents before migration.".into());
        }
        if legacy.symlink_metadata().is_ok_and(|m|m.file_type().is_symlink()) &&
            legacy.canonicalize().ok()!=current.canonicalize().ok(){
            return Err("The legacy data alias points to a different location. Keep both locations for review.".into());
        }
        return Ok(current);
    }
    if legacy.symlink_metadata().is_ok_and(|m| m.file_type().is_symlink()) {
        return Err("The legacy data directory is a link. Check its destination before migration.".into());
    }
    if !legacy.exists() { return Ok(current); }
    if !legacy.is_dir(){return Err("The legacy data path is not a directory.".into());}
    fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    let guard = OpenOptions::new().create(true).truncate(false).read(true).write(true)
        .open(parent.join(".anicanto-migration.lock")).map_err(|e| e.to_string())?;
    guard.try_lock_exclusive().map_err(|_| "Another data migration is active.".to_string())?;
    if current.exists() { return Ok(current); }
    let lock_path = legacy.join("studio/instance.lock");
    let _instance = if lock_path.exists() {
        let f = OpenOptions::new().read(true).write(true).open(&lock_path).map_err(|e|e.to_string())?;
        f.try_lock_exclusive().map_err(|_| "Close the other AniCanto window before moving its data directory.".to_string())?;
        Some(f)
    } else { None };
    // Windows can reject a directory rename while a child lock file is open.
    // Leave the original root intact when a move or alias cannot be completed.
    #[cfg(windows)] drop(_instance);
    if fs::rename(&legacy, &current).is_err() { return Ok(legacy); }
    if let Err(error) = link_directory(&current, &legacy) {
        fs::rename(&current, &legacy).map_err(|rollback|format!("Data alias failed: {error}; rollback failed: {rollback}. Data remains at {}",current.display()))?;
        return Ok(legacy);
    }
    Ok(current)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> PathBuf {
        let p = std::env::temp_dir().join(format!("anicanto-root-{}-{}", std::process::id(),
            std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos()));
        fs::create_dir_all(&p).unwrap(); p
    }
    #[test]
    fn old_absolute_paths_and_contents_survive() {
        let p=fixture();let old=p.join("SamCantoSync");fs::create_dir_all(old.join("jobs")).unwrap();
        fs::write(old.join("jobs/saved.json"),b"saved budget and takes").unwrap();
        let root=select(&p,"SamCantoSync").unwrap();
        assert_eq!(fs::read(root.join("jobs/saved.json")).unwrap(),b"saved budget and takes");
        assert_eq!(fs::read(old.join("jobs/saved.json")).unwrap(),b"saved budget and takes");
        assert_eq!(select(&p,"SamCantoSync").unwrap(),root);
        if old.symlink_metadata().is_ok_and(|m|m.file_type().is_symlink()){fs::remove_file(&old).unwrap();}
        fs::remove_dir_all(p).unwrap();
    }
    #[test]
    fn existing_new_root_never_merges_or_overwrites_old_data() {
        let p=fixture();fs::create_dir_all(p.join("AniCanto")).unwrap();fs::create_dir_all(p.join("SamCantoSync")).unwrap();
        fs::write(p.join("SamCantoSync/keep"),b"old").unwrap();
        assert!(select(&p,"SamCantoSync").is_err());
        assert_eq!(fs::read(p.join("SamCantoSync/keep")).unwrap(),b"old");fs::remove_dir_all(p).unwrap();
    }
    #[test]
    fn busy_legacy_library_does_not_move() {
        let p=fixture();let old=p.join("SamCantoSync");fs::create_dir_all(old.join("studio")).unwrap();
        let f=OpenOptions::new().create(true).truncate(false).read(true).write(true).open(old.join("studio/instance.lock")).unwrap();
        f.try_lock_exclusive().unwrap();assert!(select(&p,"SamCantoSync").is_err());assert!(old.is_dir());
        drop(f);fs::remove_dir_all(p).unwrap();
    }
    #[test]
    #[cfg(unix)]
    fn unexpected_legacy_alias_is_never_ignored() {
        let p=fixture();fs::create_dir_all(p.join("other")).unwrap();
        std::os::unix::fs::symlink(p.join("other"),p.join("SamCantoSync")).unwrap();
        assert!(select(&p,"SamCantoSync").is_err());
        fs::create_dir_all(p.join("AniCanto")).unwrap();assert!(select(&p,"SamCantoSync").is_err());
        fs::remove_file(p.join("SamCantoSync")).unwrap();fs::remove_dir_all(p).unwrap();
    }
}
