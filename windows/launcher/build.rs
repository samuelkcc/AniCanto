use std::{env,fs,path::PathBuf,process::Command};
fn main() {
    println!("cargo:rerun-if-env-changed=CANTOSYNC_EMBEDDED_PACKAGE");
    let output=PathBuf::from(env::var("OUT_DIR").unwrap());
    if env::var("CARGO_CFG_TARGET_OS").as_deref()==Ok("windows") {
        let icon=PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap())
            .join("../../studio/src-tauri/icons/icon.ico").canonicalize().expect("AniCanto icon");
        println!("cargo:rerun-if-changed={}",icon.display());
        println!("cargo:rerun-if-env-changed=CANTOSYNC_RESOURCE_COMPILER");
        let rc=output.join("anicanto-icon.rc");let res=output.join("anicanto-icon.res");
        fs::write(&rc,format!("32512 ICON \"{}\"\n",icon.to_string_lossy().replace('\\',"/"))).unwrap();
        let compiler=env::var("CANTOSYNC_RESOURCE_COMPILER")
            .unwrap_or_else(|_|if cfg!(windows){"rc.exe".into()}else{"llvm-rc".into()});
        let mut command=Command::new(compiler);
        // LLVM's cross compiler treats POSIX /absolute paths as RC options.
        command.current_dir(&output).arg("/fo").arg("anicanto-icon.res").arg("anicanto-icon.rc");
        let status=command.status().expect("Windows resource compiler must be installed to embed the app icon");
        assert!(status.success(),"AniCanto icon resource compilation failed");
        for binary in ["AniCanto-Windows","AniCanto-helper"] {
            println!("cargo:rustc-link-arg-bin={binary}={}",res.display());
        }
    }
    if let Ok(source)=env::var("CANTOSYNC_EMBEDDED_PACKAGE") {
        let source=PathBuf::from(source);
        println!("cargo:rerun-if-changed={}",source.display());
        println!("cargo:rerun-if-changed={}",source.with_extension("manifest.json").display());
        fs::copy(&source,output.join("payload.zip")).expect("portable package");
        fs::copy(source.with_extension("manifest.json"),output.join("manifest.json")).expect("portable manifest");
    } else {
        fs::write(output.join("payload.zip"),[]).unwrap();
        fs::write(output.join("manifest.json"),"{}").unwrap();
    }
}
