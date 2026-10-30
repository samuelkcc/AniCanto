#![cfg_attr(target_os = "windows", windows_subsystem = "windows")]
use std::{collections::HashSet, fs::{File,OpenOptions}, io::{BufRead,BufReader,Write}, path::PathBuf,
    process::{Child,Command,Stdio}, sync::{Arc,Mutex,atomic::{AtomicBool,Ordering}}, time::Instant};
use serde_json::{json,Value};
use tauri::{Emitter,Manager,State};
use fs2::FileExt;
mod appearance;
mod support_export;
mod preview_stream;
mod task_lifecycle;
mod native_queue;
use native_queue::QueueControl;
use task_lifecycle::TaskLifecycle;
use appearance::{StartupWindow,studio_appearance};

#[cfg(windows)]
struct OwnedJob(isize);
#[cfg(windows)]
impl OwnedJob {
    fn assign(child:&Child)->Result<Self,String> {
        use std::{ffi::c_void,os::windows::io::AsRawHandle};
        #[repr(C)] struct Basic {process_time:i64,job_time:i64,flags:u32,min_working:usize,max_working:usize,active:u32,affinity:usize,priority:u32,scheduling:u32}
        #[repr(C)] struct Limits {basic:Basic,io:[u64;6],process_memory:usize,job_memory:usize,peak_process:usize,peak_job:usize}
        #[link(name="kernel32")] unsafe extern "system" {
            fn CreateJobObjectW(attributes:*mut c_void,name:*const u16)->isize;
            fn SetInformationJobObject(job:isize,class:i32,info:*const c_void,length:u32)->i32;
            fn AssignProcessToJobObject(job:isize,process:*mut c_void)->i32;
        }
        unsafe {let job=Self(CreateJobObjectW(std::ptr::null_mut(),std::ptr::null()));if job.0==0{return Err(std::io::Error::last_os_error().to_string());}
            let mut limits:Limits=std::mem::zeroed();limits.basic.flags=0x2000;
            if SetInformationJobObject(job.0,9,&limits as *const _ as *const c_void,std::mem::size_of::<Limits>() as u32)==0 || AssignProcessToJobObject(job.0,child.as_raw_handle())==0 {return Err(std::io::Error::last_os_error().to_string());}Ok(job)
        }
    }
}
#[cfg(windows)] impl Drop for OwnedJob {fn drop(&mut self){#[link(name="kernel32")] unsafe extern "system" {fn CloseHandle(handle:isize)->i32;}unsafe{CloseHandle(self.0);}}}
struct Active { child:Child, id:String, row:Option<String>, paused:bool, setup:bool, action:String, model_id:Option<String>, started:Instant, #[cfg(windows)] _job:Option<OwnedJob> }
struct Host { root:PathBuf, shared:PathBuf, windows:PathBuf, backend:PathBuf, helper:PathBuf,
    recovery_checked:AtomicBool, rpc_lock:Mutex<()>, task_lock:Mutex<()>, active:Mutex<Option<Active>>, media:Arc<Mutex<HashSet<u32>>>, _instance:File }
const DESKTOP_OPERATIONS:&[&str]=&["export-logs","finish-current","speech-library","speech-upload","speech-import","speech-save","speech-draft","speech-new","speech-select","speech-load","speech-delete","speech-rename","speech-export-file","state","configure","add","select","reset-video-plan","reset-video","move-video","remove-videos","restore-videos","remove","snapshot","save-draft","review-resolution","models","model-choices","model-removal-plan","remove-model","remove-retired-model","project-cache-plan","project-cache-status","clear-project-cache","plan","media-status","logs","log-sources","licenses","use-terms","accept-use-terms","revoke-use-terms","source-language","source-prepare-status","source-prepare-cancel","compute-status","project-terms","set-project-terms","performance-choice","update-recording-plan","media-thumbnail","media-subtitles","set-subtitle-source","set-external-subtitle","review-triage","recording-impact","audio-waveforms","boundary-proposals","apply-boundary","subtitle-alignment-preview","set-subtitle-alignment"];

impl Host {
    fn desktop_rpc(&self,op:&str,params:Value)->Result<Value,String>{
        if !DESKTOP_OPERATIONS.contains(&op){return Err(format!("Unsupported desktop operation: {op}"));}
        if op=="export-logs" {return Ok(json!(self.debug_contents()));}
        // Hydration can wait for a File Provider. Progress and cancellation
        // must remain available while the normal Python RPC is occupied.
        if ["source-prepare-status","source-prepare-cancel"].contains(&op) {
            let directory=self.root.join("source-preparation");
            let token=params["operationID"].as_str();
            let path=if let Some(id)=token {
                if id.is_empty()||id.len()>64||!id.bytes().all(|b|b.is_ascii_alphanumeric()||b==b'-'){return Err("Invalid source preparation operation.".into());}
                directory.join(id).join("status.json")
            }else{directory.join("current.json")};
            if path.symlink_metadata().is_ok_and(|m|m.file_type().is_symlink()){return Err("Invalid preparation receipt.".into());}
            let value=std::fs::read(&path).ok().filter(|v|v.len()<65536).and_then(|v|serde_json::from_slice::<Value>(&v).ok()).unwrap_or(Value::Null);
            if op=="source-prepare-cancel" {
                let id=token.ok_or("Missing source preparation operation.")?;
                if value.is_null()||value["state"]=="preparing" {let own=directory.join(id);if own.symlink_metadata().is_ok_and(|m|m.file_type().is_symlink()){return Err("Invalid preparation directory.".into());}std::fs::create_dir_all(&own).map_err(|e|e.to_string())?;std::fs::write(own.join("cancel"),b"cancel").map_err(|e|e.to_string())?;}
                return Ok(json!({"cancelRequested":true}));
            }
            return Ok(if value["state"]=="preparing"&&value["hostPID"].as_u64()!=Some(std::process::id() as u64){Value::Null}else{value});
        }
        // Read only this fixed receipt without the mutation RPC lock. Calling
        // Python here would queue behind cleanup and hide all live progress.
        if op=="project-cache-status" {
            let id=params["operationID"].as_str().ok_or("Invalid cleanup operation.")?;
            if id.is_empty()||id.len()>80||!id.bytes().all(|c|c.is_ascii_alphanumeric()||c==b'-'){return Err("Invalid cleanup operation.".into());}
            let path=self.root.join("project-cache-progress.json");
            if path.symlink_metadata().is_ok_and(|m|m.file_type().is_symlink()){return Ok(Value::Null);}
            let value=std::fs::read(path).ok().filter(|v|v.len()<65536).and_then(|raw|serde_json::from_slice::<Value>(&raw).ok()).unwrap_or(Value::Null);
            return Ok(if value["operationID"]==id{value}else{Value::Null});
        }
        let removing_model=["model-removal-plan","remove-model","remove-retired-model","project-cache-plan","clear-project-cache","source-language"].contains(&op);
        let speech_mutation=["speech-new","speech-select","speech-load","speech-delete","speech-rename","speech-export-file"].contains(&op);
        let reset_mutation=["reset-video-plan","reset-video"].contains(&op);
        let _task=if removing_model || speech_mutation || reset_mutation {Some(self.task_lock.lock().unwrap())} else {None};
        if removing_model && (self.active.lock().unwrap().is_some() || self.older_app_open()){
            return Err(if op=="source-language"{"Pause processing before checking another source language."}else if op.contains("cache"){"Pause processing before clearing cache."}else{"Pause processing before removing a model."}.into());
        }
        if ["speech-new","speech-select","speech-load","speech-delete","speech-rename","speech-export-file"].contains(&op) && self.active.lock().unwrap().is_some(){return Err("Pause processing before changing saved speech recordings.".into());}
        if ["review-resolution","review-triage","set-subtitle-source","set-external-subtitle","set-project-terms","performance-choice","update-recording-plan","set-subtitle-alignment"].contains(&op) && self.active.lock().unwrap().is_some(){return Err("Pause processing before making an explicit review choice.".into());}
        if reset_mutation && (self.active.lock().unwrap().is_some() || self.older_app_open()){return Err("Pause processing before resetting a video.".into());}
        if op=="remove" && self.active.lock().unwrap().is_some(){return Err("Pause processing before deleting a project.".into());}
        if self.python().is_none(){
            if op=="plan" {return self.cold_plan(&params);}
            if op=="model-choices" {return self.cold_model_choices();}
        }
        self.rpc(op,params)
    }
    fn older_app_open(&self)->bool {
        #[cfg(target_os="macos")] {
            if let Ok(output)=Command::new("/usr/bin/pgrep").args(["-f","/(AniCanto|CantoSync).app/Contents/MacOS/(AniCanto|CantoSync)$"]).output(){
                return String::from_utf8_lossy(&output.stdout).lines().filter_map(|s|s.parse::<u32>().ok()).any(|pid|pid!=std::process::id());
            }
        }false
    }
    fn discover()->Result<Self,String> {
        let exe=std::env::current_exe().map_err(|e|e.to_string())?;
        #[cfg(debug_assertions)]
        let development=PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
        #[cfg(not(debug_assertions))]
        let development=exe.parent().and_then(|p|p.parent()).ok_or("Application directory is unavailable")?.to_path_buf();
        let resources=exe.parent().unwrap().join("../Resources");
        let packaged=resources.join("studio/backend.py").is_file();
        let windows=if packaged{resources.join("windows")}else{std::env::var_os("CANTOSYNC_WINDOWS_PACKAGE").map(PathBuf::from).unwrap_or_else(||if cfg!(windows){development.clone()}else{development.join("windows")})};
        let shared=if packaged{resources.clone()}else if let Some(p)=std::env::var_os("CANTOSYNC_SHARED_RESOURCES"){p.into()}else if cfg!(windows)&&windows.join("shared").is_dir(){windows.join("shared")}else{development.join("Resources")};
        let backend=if packaged{resources.join("studio/backend.py")}else if cfg!(windows)&&windows.join("studio/backend.py").is_file(){windows.join("studio/backend.py")}else{development.join("studio/backend.py")};
        let root=if let Some(root)=std::env::var_os("CANTOSYNC_STUDIO_DATA"){PathBuf::from(root)}else if cfg!(windows){
            PathBuf::from(std::env::var_os("LOCALAPPDATA").ok_or("LOCALAPPDATA is unavailable")?).join("CantoSync-Windows")
        }else{PathBuf::from(std::env::var_os("HOME").ok_or("HOME is unavailable")?).join("Library/Application Support/SamCantoSync")};
        std::fs::create_dir_all(root.join("studio")).map_err(|e|e.to_string())?;
        let instance=OpenOptions::new().create(true).truncate(false).read(true).write(true).open(root.join("studio/instance.lock")).map_err(|e|e.to_string())?;
        instance.try_lock_exclusive().map_err(|_|"AniCanto Studio is already open for this library.".to_string())?;
        let helper=if packaged{exe.parent().unwrap().join("AniCanto-worker")}else{
            std::env::var_os("CANTOSYNC_MAC_HELPER").map(PathBuf::from).unwrap_or(development.join("dist/AniCanto.app/Contents/MacOS/AniCanto"))};
        Ok(Self{root,shared,windows,backend,helper,recovery_checked:AtomicBool::new(false),rpc_lock:Mutex::new(()),task_lock:Mutex::new(()),active:Mutex::new(None),media:Arc::new(Mutex::new(HashSet::new())),_instance:instance})
    }
    fn debug_contents(&self)->String {
        let report=self.rpc("export-logs",json!({})).and_then(|r|r.as_str().map(str::to_owned).ok_or_else(||"The Python debug report returned invalid output.".to_owned()));
        match report {
            Ok(text)=>format!("AniCanto {}\n{}",env!("CARGO_PKG_VERSION"),text),
            Err(error)=>{
                let core=self.shared.join(if cfg!(windows){"bin/anicanto-core.exe"}else{"bin/anicanto-core"});
                let python=self.python().unwrap_or_else(||self.root.join("missing-python"));
                support_export::report(&self.root,&[("Shared core",&core),("Python",&python),("Backend",&self.backend),("Shared resources",&self.shared),("Windows package",&self.windows)],&error,env!("CARGO_PKG_VERSION"))
            }
        }
    }
    fn python(&self)->Option<PathBuf> {
        let candidates=if cfg!(windows){vec![self.root.join("runtimes/ui/Scripts/python.exe"),self.root.join("runtimes/worker/Scripts/python.exe")]}else{
            vec![self.root.join("runtime/bin/python3"),self.shared.join("runtimes/runtime/bin/python3")]};
        std::env::var_os("CANTOSYNC_STUDIO_PYTHON").map(PathBuf::from).filter(|p|p.is_file()).or_else(||candidates.into_iter().find(|p|p.is_file()))
    }
    fn environment(&self,cmd:&mut Command) {
        cmd.env("PYTHONUTF8","1").env("PYTHONUNBUFFERED","1").env("PYTHONDONTWRITEBYTECODE","1")
            .env("PYTHONNOUSERSITE","1").env("SAM_CANTO_DATA",&self.root).env("CANTOSYNC_WINDOWS_DATA",&self.root)
            .env("CANTOSYNC_HOST_PID",std::process::id().to_string())
            .env("CANTOSYNC_SHARED_RESOURCES",&self.shared).env("CANTOSYNC_WINDOWS_PACKAGE",&self.windows)
            .env("CANTOSYNC_CORE",self.shared.join(if cfg!(windows){"bin/anicanto-core.exe"}else{"bin/anicanto-core"}));
        #[cfg(windows)] {use std::os::windows::process::CommandExt;cmd.creation_flags(0x08000000);}
    }
    fn rpc(&self,op:&str,params:Value)->Result<Value,String> {
        let _lock=self.rpc_lock.lock().map_err(|e|e.to_string())?;
        // About must remain useful before first-run Python deployment.
        if op=="licenses" && self.python().is_none(){
            let raw=std::fs::read_to_string(self.shared.join("license-inventory.json")).map_err(|e|e.to_string())?;
            let mut rows:Vec<Value>=serde_json::from_str(&raw).map_err(|e|e.to_string())?;
            let base=self.shared.canonicalize().map_err(|e|e.to_string())?;
            for row in &mut rows{
                let mut texts=Vec::new();let mut seen=HashSet::new();
                if let Some(files)=row["files"].as_array(){for name in files.iter().filter_map(Value::as_str){
                    if let Ok(path)=self.shared.join(name).canonicalize(){
                        if path.starts_with(&base)&&path.is_file()&&path.metadata().map(|m|m.len()<5_000_000).unwrap_or(false){
                            if let Ok(text)=std::fs::read_to_string(path){if seen.insert(text.clone()){texts.push(text);}}
                        }
                    }
                }}
                row["text"]=json!(texts.join("\n\n"));
            }
            return Ok(json!(rows));
        }
        let python=self.python().ok_or("The desktop runtime is missing. Use Welcome → Prepare runtime.")?;
        let mut cmd=Command::new(python);cmd.arg(&self.backend).arg("--root").arg(&self.root).arg("--shared").arg(&self.shared).arg("--helper").arg(&self.helper)
            .stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped());
        self.environment(&mut cmd);
        #[cfg(unix)] if ["media","media-subtitles"].contains(&op) {use std::os::unix::process::CommandExt;cmd.process_group(0);}
        let mut child=cmd.spawn().map_err(|e|e.to_string())?;
        let media_pid=if ["media","media-subtitles"].contains(&op){self.media.lock().unwrap().insert(child.id());Some(child.id())}else{None};
        #[cfg(windows)] let _media_job=if ["media","media-subtitles"].contains(&op){Some(OwnedJob::assign(&child)?)}else{None};
        let recover=!self.recovery_checked.load(Ordering::SeqCst)&&self.active.lock().unwrap().is_none()&&!self.older_app_open();
        child.stdin.take().unwrap().write_all(json!({"op":op,"params":params,"recoverOrphans":recover}).to_string().as_bytes()).map_err(|e|e.to_string())?;
        let output=child.wait_with_output().map_err(|e|e.to_string())?;
        if let Some(pid)=media_pid{self.media.lock().unwrap().remove(&pid);}
        let text=String::from_utf8_lossy(&output.stdout);
        let result:Value=text.lines().rev().find_map(|s|serde_json::from_str(s).ok()).ok_or_else(||format!("Desktop adapter failed: {}",String::from_utf8_lossy(&output.stderr)))?;
        if result["ok"]==true {self.recovery_checked.store(true,Ordering::SeqCst);Ok(result["result"].clone())} else {Err(result["error"].as_str().unwrap_or("Desktop adapter failed").to_string())}
    }
    fn cold_model_choices(&self)->Result<Value,String>{
        let models:Vec<Value>=serde_json::from_slice(&std::fs::read(self.shared.join("model-options.json")).map_err(|e|e.to_string())?).map_err(|e|e.to_string())?;
        #[cfg(windows)] {
            let native:Vec<Value>=serde_json::from_slice(&std::fs::read(self.windows.join("native-models.json")).map_err(|e|e.to_string())?).map_err(|e|e.to_string())?;
            let mut combined:Vec<Value>=models.into_iter().filter(|m|m["platform"]!="darwin").collect();
            combined.extend(native);
            return Ok(json!(Self::select_cold_choices(combined)));
        }
        #[cfg(not(windows))]
        Ok(json!(Self::select_cold_choices(models)))
    }
    fn select_cold_choices(models:Vec<Value>)->Vec<Value>{
        models.into_iter().filter(|m|{
            let category=m["category"].as_str().unwrap_or("");
            let id=m["id"].as_str().unwrap_or("");
            let text_supported=category!="text" || {
                #[cfg(windows)] { ["qwen3.5:9b","qwen3.5:35b"].contains(&id) }
                #[cfg(not(windows))] { ["mlx:qwen3.5-9b:4bit","mlx:qwen3.5-35b-a3b:4bit"].contains(&id) }
            };
            let platform_supported={
                #[cfg(windows)] { m["platform"]!="darwin" && (m["nativeFormat"].is_string() || m["engine"].as_str().is_some_and(|e|e.starts_with("gpt-") || e=="whisper")) }
                #[cfg(not(windows))] { m["engine"]!="ollama" && !id.starts_with("asr-native") }
            };
            platform_supported && text_supported && ["text","voice","speech","asr"].contains(&category)
                && m["retired"]!=true && m["licenseReviewRequired"]!=true
                && !(category=="voice" && ["qwen-tts","gpt-sovits-v3"].contains(&m["engine"].as_str().unwrap_or("")))
                && m["files"].as_array().is_some_and(|f|!f.is_empty())
                && m["bytes"].as_u64().unwrap_or(0)>0
        }).map(|m|json!({"id":m["id"],"title":m["title"],"category":m["category"],"engine":m["engine"],"bytes":m["bytes"],"estimatedMemoryGB":m["estimatedMemoryGB"],"license":m["license"]})).collect()
    }
    fn cold_plan(&self,params:&Value)->Result<Value,String>{
        let engine=params["engine"].as_str().unwrap_or("drama3");
        let requested=params["models"].as_object().cloned().unwrap_or_default();
        #[cfg(not(windows))] {
            let models=serde_json::to_string(&requested).map_err(|e|e.to_string())?;
            let mut cmd=Command::new(&self.helper);cmd.args(["--studio-plan",engine,&models]);self.environment(&mut cmd);
            let output=cmd.output().map_err(|e|e.to_string())?;
            return String::from_utf8_lossy(&output.stdout).lines().rev().find_map(|s|serde_json::from_str(s).ok()).ok_or("The Mac setup planner did not return a plan.".into());
        }
        #[cfg(windows)] {
            let load=|p:PathBuf|->Result<Value,String>{serde_json::from_slice(&std::fs::read(p).map_err(|e|e.to_string())?).map_err(|e|e.to_string())};
            let mut models=load(self.shared.join("model-options.json"))?.as_array().cloned().ok_or("Invalid model catalog")?;
            models.extend(load(self.windows.join("native-models.json"))?.as_array().cloned().ok_or("Invalid native catalog")?);
            // Match native_setup.catalog before Python exists. Without this,
            // GPT appears unsupported only on the first Windows launch.
            for m in &mut models {
                if m["engine"].as_str().is_some_and(|e|e.starts_with("gpt-")){m["nativeFormat"]=json!("pytorch");}
                if m["engine"]=="whisper"{m["nativeFormat"]=json!("ctranslate2");}
            }
            let mut hardware=anicanto_core::hardware();hardware["nativeWorkflowVersion"]=json!(1);hardware["nativeDramaCUDA"]=json!(true);hardware["backend"]=json!("cpu");
            hardware["nativeDramaSmallCPU"]=json!(self.windows.join("tools/audiocpp_small_server.exe").is_file());
            hardware["nativeDramaSmallCUDA"]=json!(self.windows.join("tools/drama-small-cuda/audiocpp_server.exe").is_file());
            let adapters=hardware["displayAdapters"].as_array().cloned().unwrap_or_default();
            let nvidia=adapters.iter().filter(|a|a["vendorId"]==0x10de && a["dedicatedMemoryGB"].as_f64().unwrap_or(0.)>0.)
                .max_by(|a,b|a["dedicatedMemoryGB"].as_f64().unwrap_or(0.).total_cmp(&b["dedicatedMemoryGB"].as_f64().unwrap_or(0.)));
            let amd_supported=["RX 9070","RX 9070 XT","RX 9060 XT","RX 7900 XTX","RX 7700","AI PRO R9700","PRO W7900","PRO W7900 DUAL SLOT"];
            let amd=adapters.iter().filter(|a|{
                let name=a["name"].as_str().unwrap_or("").trim().to_ascii_uppercase();
                let name=name.strip_suffix(" GRAPHICS").unwrap_or(&name);
                a["vendorId"]==0x1002 && a["dedicatedMemoryGB"].as_f64().unwrap_or(0.)>0.
                    && amd_supported.iter().any(|model|name.ends_with(&format!(" {model}")))
            }).max_by(|a,b|a["dedicatedMemoryGB"].as_f64().unwrap_or(0.).total_cmp(&b["dedicatedMemoryGB"].as_f64().unwrap_or(0.)));
            if let Some((adapter,backend,vendor))=nvidia.map(|a|(a,"cuda","nvidia")).or_else(||amd.map(|a|(a,"rocm","amd"))){
                hardware["backend"]=json!(backend);hardware["suggestedSetupBackend"]=json!(vendor);
                hardware["acceleratorMemoryGB"]=adapter["dedicatedMemoryGB"].clone();hardware["acceleratorName"]=adapter["name"].clone();
                hardware["memorySource"]=json!("DXGI dedicated video memory; inference not yet verified");
            }else{
                let mut probe=Command::new("nvidia-smi");probe.args(["--query-gpu=name,memory.total","--format=csv,noheader,nounits"]);self.environment(&mut probe);
                if let Ok(output)=probe.output(){if output.status.success(){if let Some((name,gib))=String::from_utf8_lossy(&output.stdout).lines().filter_map(|l|l.rsplit_once(',').and_then(|(name,n)|n.trim().parse::<f64>().ok().map(|n|(name.trim().to_owned(),n/1024.)))).next(){hardware["backend"]=json!("cuda");hardware["acceleratorName"]=json!(name);hardware["acceleratorMemoryGB"]=json!(gib);hardware["memorySource"]=json!("nvidia-smi; inference not yet verified");}}}
            }
            let installed:Vec<Value>=models.iter().filter(|m|{
                let relative=m["legacy"].as_str().map(str::to_owned).unwrap_or_else(||format!("models/{}/{}",if m["category"]=="voice"{"voice-variants"}else{"variants"},m["id"].as_str().unwrap_or("").replace(':',"-")));
                m["files"].as_array().is_some_and(|files|!files.is_empty()&&files.iter().all(|f|self.root.join(&relative).join(f["path"].as_str().unwrap_or("")).metadata().is_ok_and(|s|Some(s.len())==f["size"].as_u64())))
            }).map(|m|m["id"].clone()).collect();
            let mut result=anicanto_core::deployment(&json!({"hardware":hardware,"models":models,"engine":engine,"dramaBackend":params["dramaBackend"].as_str().unwrap_or("auto"),"requestedModels":requested,"singleModelPerCategory":true,"installedModels":installed,"selectedModels":load(self.root.join("model-selections.json")).unwrap_or(json!({}))}))?;
            let tools=load(self.windows.join("native-tools.json"))?;
            let names=hardware["displayAdapters"].to_string()+hardware["acceleratorName"].as_str().unwrap_or("");
            let upper=names.to_ascii_uppercase();
            let modern=upper.contains("BLACKWELL") || upper.contains("RTX 50") || upper.contains("RTX PRO ") || upper.contains("B200") || upper.contains("R200");
            let major=if modern {"13"}else{"12"};
            let decorate=|value:&mut Value| {
                let mut components=Vec::new();
                if value["engine"]=="drama3" && value["voiceBackend"]=="cuda" {
                    for stem in ["drama-full-cuda","drama-full-cudart"] {
                        let key=format!("{stem}{major}");let tool=&tools[&key];
                        let base=self.root.join("tools").join(&key);
                        let receipt=load(base.join("verified.json")).unwrap_or(json!({}));
                        let installed=receipt["sha256"]==tool["sha256"] && tool["requiredFiles"].as_array().is_some_and(|files|files.iter().all(|file| {
                            let name=file.as_str().unwrap_or("");base.join(name).metadata().is_ok_and(|m|Some(m.len())==receipt["files"][name]["bytes"].as_u64())
                        }));
                        components.push(json!({"id":key,"title":if stem.ends_with("cudart"){format!("NVIDIA CUDA {} libraries",tool["cudaVersion"].as_str().unwrap_or(""))}else{format!("Drama 3 · NVIDIA CUDA {}",tool["cudaVersion"].as_str().unwrap_or(""))},"kind":"tool","bytes":tool["size"],"installed":installed,"required":true}));
                    }
                }
                let extra:u64=components.iter().filter(|r|r["installed"]!=true).map(|r|r["bytes"].as_u64().unwrap_or(0)).sum();
                value["tools"]=json!(components);value["toolDownloadBytes"]=json!(extra);
                value["totalDownloadBytes"]=json!(value["modelDownloadBytes"].as_u64().unwrap_or(0)+extra);
            };
            decorate(&mut result);
            if let Some(presets)=result["qualityPresets"].as_array_mut(){for preset in presets{if preset["plan"]["downloads"].is_array(){decorate(&mut preset["plan"]);}}}
            result["bootstrapRequired"]=json!(true);Ok(result)
        }
    }
}

#[tauri::command]
async fn studio_rpc(op:String,params:Value,host:State<'_,Arc<Host>>)->Result<Value,String> {
    let host=host.inner().clone();tauri::async_runtime::spawn_blocking(move||host.desktop_rpc(&op,params)).await.map_err(|e|e.to_string())?
}
fn continue_native_queue(host:Arc<Host>,app:tauri::AppHandle,epoch:u64){
    std::thread::spawn(move||{
        let _gate=host.task_lock.lock().unwrap();
        if !app.state::<QueueControl>().matches(epoch){let _=host.rpc("queue-stop",json!({}));return;}
        if host.active.lock().unwrap().is_some(){return;}
        match host.rpc("queue-next",json!({"epoch":epoch})) {
            Ok(spec) if !spec.is_null()=>{
                if !app.state::<QueueControl>().matches(epoch){
                    if let Some(id)=spec["rowID"].as_str(){let _=host.rpc("finish",json!({"id":id,"code":1,"paused":true,"stderr":"Queue paused before launch"}));}
                    let _=host.rpc("queue-stop",json!({}));return;
                }
                if let Err(error)=launch(host.clone(),app.clone(),spec.clone()){
                    if let Some(id)=spec["rowID"].as_str(){let _=host.rpc("finish",json!({"id":id,"code":1,"stderr":error}));}
                    let _=app.emit("studio-log",format!("Native queue launch failed: {error}"));
                    continue_native_queue(host.clone(),app.clone(),epoch);
                }
            },
            result=>{app.state::<QueueControl>().finish(epoch);let _=host.rpc("queue-stop",json!({}));if host.active.lock().unwrap().is_none(){if let Some(receipt)=app.state::<TaskLifecycle>().last_finished(){if let Some(id)=receipt["runID"].as_str(){app.state::<TaskLifecycle>().release(id);}}}if let Err(e)=result{let _=app.emit("studio-log",format!("Native queue: {e}"));}}
        }
    });
}
#[tauri::command]
async fn studio_status(app:tauri::AppHandle,host:State<'_,Arc<Host>>,lifecycle:State<'_,TaskLifecycle>)->Result<Value,String> {
    let active=host.active.lock().unwrap();
    Ok(json!({"cleanupResult":std::fs::metadata(host.root.join("last-download-cleanup.json")).ok().filter(|m|m.len()<65536).and_then(|_|std::fs::read(host.root.join("last-download-cleanup.json")).ok()).and_then(|b|serde_json::from_slice::<Value>(&b).ok()),"lastFinished":lifecycle.last_finished(),"idleSleepInhibited":lifecycle.inhibited(),"nativeQueue":app.state::<QueueControl>().enabled(),"runtimeReady":host.python().is_some(),"running":active.as_ref().map(|a|json!({"id":a.id,"rowID":a.row,"seconds":a.started.elapsed().as_secs_f64(),"paused":a.paused,"setup":a.setup,"action":a.action,"modelID":a.model_id})),"storage":host.root}))
}
#[tauri::command]
fn studio_ack_finished(run_id:String,app:tauri::AppHandle,host:State<'_,Arc<Host>>,lifecycle:State<'_,TaskLifecycle>)->bool{
    let active=host.active.lock().unwrap();if active.is_some()||app.state::<QueueControl>().enabled(){return false;}lifecycle.release(&run_id)
}
#[tauri::command]
async fn studio_pick(kind:String)->Result<Vec<String>,String> {
    tauri::async_runtime::spawn_blocking(move||{
        let dialog=rfd::FileDialog::new();
        let paths=match kind.as_str(){
            "video"=>dialog.add_filter("Videos",&["mkv","mp4","mov","m4v","avi","webm","ts"]).pick_files().unwrap_or_default(),
            "subtitle"=>dialog.add_filter("Subtitles",&["srt","ass","ssa","vtt"]).pick_file().into_iter().collect(),
            "audio"=>dialog.add_filter("Reference audio",&["wav","mp3","m4a","flac","webm","ogg"]).pick_file().into_iter().collect(),
            "folder"=>dialog.pick_folder().into_iter().collect(),_=>return Err("Unsupported file picker".to_string())};
        Ok(paths.iter().map(|p|p.to_string_lossy().into_owned()).collect())
    }).await.map_err(|e|e.to_string())?
}

#[tauri::command]
async fn studio_export_speech(id:String,source:Option<bool>,host:State<'_,Arc<Host>>)->Result<Value,String>{
    let host=host.inner().clone();tauri::async_runtime::spawn_blocking(move||{
        let _gate=host.task_lock.lock().map_err(|e|e.to_string())?;
        if host.active.lock().unwrap().is_some(){return Err("Pause processing before exporting speech.".into());}
        let record=host.rpc("speech-export-file",json!({"id":id,"source":source.unwrap_or(false)}))?;
        let input=PathBuf::from(record["path"].as_str().ok_or("Recording is missing")?);
        let extension=record["extension"].as_str().unwrap_or("wav");
        let title:String=record["title"].as_str().unwrap_or("AniCanto recording").chars().map(|c|if c.is_control() || "<>:\"/\\|?*".contains(c){'_'}else{c}).take(100).collect();
        let Some(output)=rfd::FileDialog::new().set_file_name(format!("{title}.{extension}")).add_filter("Audio",&[extension]).save_file() else{return Ok(json!({"cancelled":true}));};
        let parent=output.parent().ok_or("Invalid destination")?.canonicalize().map_err(|e|e.to_string())?;
        let root=host.root.canonicalize().map_err(|e|e.to_string())?;
        if parent.starts_with(root){return Err("Choose an export folder outside AniCanto's recording library.".into());}
        std::fs::copy(input,&output).map_err(|e|e.to_string())?;
        Ok(json!({"cancelled":false,"path":output.to_string_lossy()}))
    }).await.map_err(|e|e.to_string())?
}

#[tauri::command]
async fn studio_export_logs(language:Option<String>,host:State<'_,Arc<Host>>)->Result<Value,String> {
    let host=host.inner().clone();
    tauri::async_runtime::spawn_blocking(move||{
        let Some(path)=rfd::FileDialog::new().set_title(if language.as_deref()==Some("zh-HK"){"匯出除錯記錄"}else{"Export debug report"})
            .set_file_name("AniCanto-debug.txt").add_filter("Text report", &["txt"]).save_file() else {
                return Ok(json!({"cancelled":true}));
            };
        let contents=host.debug_contents();
        let (saved,recovered_location)=support_export::save(&host.root,&path,&contents)?;
        Ok(json!({"path":saved,"cancelled":false,"recoveredLocation":recovered_location}))
    }).await.map_err(|e|e.to_string())?
}

fn launch(host:Arc<Host>,app:tauri::AppHandle,spec:Value)->Result<Value,String> {
    let mut active=host.active.lock().unwrap();if active.is_some(){return Err("A task is already running. Pause it before starting another.".into());}
    if let Some(epoch)=spec["nativeQueue"].as_u64(){if !app.state::<QueueControl>().matches(epoch){return Err("Queue was paused before launch".into());}}
    let program=spec["program"].as_str().ok_or("Missing native adapter")?;
    let args:Vec<&str>=spec["args"].as_array().ok_or("Missing task arguments")?.iter().filter_map(|v|v.as_str()).collect();
    let mut cmd=Command::new(program);cmd.args(args).stdout(Stdio::piped()).stderr(Stdio::piped());host.environment(&mut cmd);
    let mut child=cmd.spawn().map_err(|e|e.to_string())?;
    #[cfg(windows)] let owned_job=match OwnedJob::assign(&child){Ok(job)=>job,Err(error)=>{let _=child.kill();return Err(error)}};
    if let Err(error)=app.state::<TaskLifecycle>().started(){let _=app.emit("studio-log",format!("Idle-sleep protection unavailable: {error}"));}
    let out=child.stdout.take().unwrap();let err=child.stderr.take().unwrap();let row=spec["rowID"].as_str().map(str::to_owned);
    let id=format!("{}-{}",child.id(),std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos());
    *active=Some(Active{child,id:id.clone(),row:row.clone(),paused:false,setup:["setup","runtime"].contains(&spec["action"].as_str().unwrap_or("")),action:spec["action"].as_str().unwrap_or("").to_owned(),model_id:spec["modelID"].as_str().map(str::to_owned),started:Instant::now(),#[cfg(windows)] _job:Some(owned_job)});drop(active);
    let log_dir=spec["attempt"]["path"].as_str().map(PathBuf::from).unwrap_or(host.root.join("logs/studio"));
    std::fs::create_dir_all(&log_dir).map_err(|e|e.to_string())?;
    let log=Arc::new(Mutex::new(OpenOptions::new().create(true).append(true).open(log_dir.join("process.log")).map_err(|e|e.to_string())?));
    let stderr=Arc::new(Mutex::new(String::new()));
    let errbuf=stderr.clone();let errlog=log.clone();let errapp=app.clone();
    let err_thread=std::thread::spawn(move||{for line in BufReader::new(err).lines().map_while(Result::ok){
        let _=writeln!(errlog.lock().unwrap(),"{line}");let mut b=errbuf.lock().unwrap();b.push_str(&line);b.push('\n');if b.len()>24000 {let cut=b.len()-12000;let cut=(cut..b.len()).find(|i|b.is_char_boundary(*i)).unwrap();b.drain(..cut);}drop(b);
        let _=errapp.emit("studio-log",line);
    }});
    let run_id=id.clone();
    std::thread::spawn(move||{
        for line in BufReader::new(out).lines().map_while(Result::ok){
            let _=writeln!(log.lock().unwrap(),"{line}");
            if let Ok(event)=serde_json::from_str::<Value>(&line){if event.is_object(){
                if let Some(ref row)=row{let _=host.rpc("record-event",json!({"id":row,"event":event}));}
                let _=app.emit("studio-event",json!({"runID":run_id,"rowID":row,"event":event}));continue;
            }}let _=app.emit("studio-log",line);
        }
        let (mut code,paused)=loop {
            let result={let mut active=host.active.lock().unwrap();match active.as_mut(){
                Some(owned)=>match owned.child.try_wait(){Ok(Some(s))=>Some((s.code().unwrap_or(1),owned.paused)),Err(_)=>Some((1,owned.paused)),Ok(None)=>None},
                None=>Some((1,false))}};
            if let Some(r)=result{break r;}std::thread::sleep(std::time::Duration::from_millis(50));
        };
        let _=err_thread.join();
        if let Some(token)=spec["modelSwitchToken"].as_str(){
            if let Err(error)=host.rpc("finish-model-switch",json!({"token":token,"success":code==0&&!paused})){
                code=1;let _=app.emit("studio-log",format!("Model switch retained existing packages: {error}"));
            }
        }
        let mut finalization_error=None;
        if let Some(ref row)=row{if let Err(error)=host.rpc("finish",json!({"id":row,"code":code,"paused":paused,"stderr":*stderr.lock().unwrap()})){
            code=1;let _=writeln!(log.lock().unwrap(),"Queue finalization failed: {error}");
            let _=app.emit("studio-log",format!("Queue finalization failed: {error}"));finalization_error=Some(error);
        }}
        if spec["action"]=="speech-studio" {
            if let Err(error)=host.rpc("speech-finish",json!({"id":spec["speechClipID"],"code":code,"paused":paused,"stderr":*stderr.lock().unwrap()})) {
                code=1;finalization_error=Some(error);
            }
        }
        let payload=json!({"runID":run_id,"rowID":row,"code":code,"paused":paused,"action":spec["action"],"modelID":spec["modelID"],"finalizationError":finalization_error,"nativeQueue":spec["nativeQueue"]});
        // Publish status and clear ownership atomically with respect to status
        // polling. A poll must never see idle without its completion receipt.
        {let mut active=host.active.lock().unwrap();app.state::<TaskLifecycle>().finished(payload.clone());active.take();}
        let _=app.emit("studio-finished",payload);
        if let Some(epoch)=spec["nativeQueue"].as_u64(){
            if paused || finalization_error.is_some(){app.state::<QueueControl>().stop();let _=host.rpc("queue-stop",json!({}));}
            else {continue_native_queue(host.clone(),app.clone(),epoch);}
        }
        // Hold the assertion across a normal queue hand-off. If the frontend
        // has failed permanently, do not inhibit sleep forever while idle.
        let grace_host=host.clone();let grace_app=app.clone();let completed_id=run_id.clone();
        std::thread::spawn(move||{
            std::thread::sleep(std::time::Duration::from_secs(120));
            let active=grace_host.active.lock().unwrap();if active.is_none()&&!grace_app.state::<QueueControl>().enabled(){grace_app.state::<TaskLifecycle>().release(&completed_id);}
        });
    });
    Ok(json!({"id":id}))
}
#[tauri::command]
async fn studio_start(op:String,params:Value,app:tauri::AppHandle,host:State<'_,Arc<Host>>)->Result<Value,String> {
    if !["speech-studio","start","render","retry-review","setup","maintain-model","maintain-models"].contains(&op.as_str()){return Err("Unsupported task".into());}
    let host=host.inner().clone();tauri::async_runtime::spawn_blocking(move||{
        let _gate=host.task_lock.lock().map_err(|e|e.to_string())?;
        if ["setup","maintain-model","maintain-models"].contains(&op.as_str())&&host.older_app_open(){return Err("Close the previous AniCanto app before switching or removing models.".into());}
        if host.root.join("batch-inflight.json").is_file()&&host.older_app_open(){return Err("Close the previous AniCanto app before starting a task here. Its saved conversion is retained.".into());}
        // Reserve across preparation and spawn, without holding a mutex while
        // native callbacks need it. RPC serialization also protects drafts.
        if host.active.lock().unwrap().is_some(){return Err("A task is already running.".into());}
        let queued=op=="start"&&params["nativeQueue"]==true;let include_attention=params["includeAttention"]==true;
        let mut spec=host.rpc(&op,params)?;
        if queued {
            let epoch=app.state::<QueueControl>().arm();
            if let Err(error)=host.rpc("queue-arm",json!({"id":spec["rowID"],"epoch":epoch,"includeAttention":include_attention})){app.state::<QueueControl>().stop();if let Some(id)=spec["rowID"].as_str(){let _=host.rpc("finish",json!({"id":id,"code":1,"paused":true,"stderr":error}));}return Err(error);}
            spec["nativeQueue"]=json!(epoch);
        }
        match launch(host.clone(),app,spec.clone()) {Ok(v)=>Ok(v),Err(error)=>{
            if let Some(id)=spec["rowID"].as_str(){let _=host.rpc("finish",json!({"id":id,"code":1,"stderr":error}));}
            if let Some(id)=spec["speechClipID"].as_str(){let _=host.rpc("speech-finish",json!({"id":id,"code":1,"stderr":error}));}Err(error)
        }}
    }).await.map_err(|e|e.to_string())?
}
#[tauri::command]
async fn studio_pause(app:tauri::AppHandle,host:State<'_,Arc<Host>>)->Result<(),String> {
    // Cancellation is visible before waiting for slow source preparation.
    app.state::<QueueControl>().stop();
    let mut active=host.active.lock().unwrap();
    if let Some(ref mut task)=*active{task.paused=true;
        #[cfg(unix)] unsafe {libc::kill(task.child.id() as i32,libc::SIGTERM);}
        #[cfg(windows)] {task._job.take();let _=task.child.kill();}
    }Ok(())
}
#[tauri::command]
async fn studio_media(params:Value,host:State<'_,Arc<Host>>)->Result<Value,String> {
    let host=host.inner().clone();tauri::async_runtime::spawn_blocking(move||{
        // Media transcoding must not hold the state lock for its whole duration.
        // A separate adapter instance only reads state for this operation.
        let shadow=Host{root:host.root.clone(),shared:host.shared.clone(),windows:host.windows.clone(),backend:host.backend.clone(),helper:host.helper.clone(),recovery_checked:AtomicBool::new(true),rpc_lock:Mutex::new(()),task_lock:Mutex::new(()),active:Mutex::new(None),media:host.media.clone(),_instance:host._instance.try_clone().map_err(|e|e.to_string())?};
        let mut result=shadow.rpc("media",params)?;
        if result["mode"]=="demand" {
            let python=host.python().ok_or("The playback runtime is missing.")?;
            let stream=preview_stream::start(&python,&host.shared.join("studio_stream.py"),result["streamConfig"].take())?;
            result["url"]=stream["url"].clone();result["streamID"]=stream["streamID"].clone();
        }
        Ok(result)
    }).await.map_err(|e|e.to_string())?
}
#[tauri::command]
async fn studio_stop_stream(id:String)->Result<(),String>{tauri::async_runtime::spawn_blocking(move||preview_stream::stop(&id)).await.map_err(|e|e.to_string())?;Ok(())}
#[tauri::command]
async fn studio_thumbnail(params:Value,host:State<'_,Arc<Host>>)->Result<Value,String> {
    let host=host.inner().clone();tauri::async_runtime::spawn_blocking(move||{
        // Media transcoding must not hold the state lock for its whole duration.
        // A separate adapter instance only reads state for this operation.
        let shadow=Host{root:host.root.clone(),shared:host.shared.clone(),windows:host.windows.clone(),backend:host.backend.clone(),helper:host.helper.clone(),recovery_checked:AtomicBool::new(true),rpc_lock:Mutex::new(()),task_lock:Mutex::new(()),active:Mutex::new(None),media:host.media.clone(),_instance:host._instance.try_clone().map_err(|e|e.to_string())?};
        shadow.rpc("media-thumbnail",params)
    }).await.map_err(|e|e.to_string())?
}
#[tauri::command]
async fn studio_subtitles(params:Value,host:State<'_,Arc<Host>>)->Result<Value,String> {
    let host=host.inner().clone();tauri::async_runtime::spawn_blocking(move||{
        // Media transcoding must not hold the state lock for its whole duration.
        // A separate adapter instance only reads state for this operation.
        let shadow=Host{root:host.root.clone(),shared:host.shared.clone(),windows:host.windows.clone(),backend:host.backend.clone(),helper:host.helper.clone(),recovery_checked:AtomicBool::new(true),rpc_lock:Mutex::new(()),task_lock:Mutex::new(()),active:Mutex::new(None),media:host.media.clone(),_instance:host._instance.try_clone().map_err(|e|e.to_string())?};
        shadow.rpc("media-subtitles",params)
    }).await.map_err(|e|e.to_string())?
}
#[tauri::command]
async fn studio_bootstrap(app:tauri::AppHandle,host:State<'_,Arc<Host>>)->Result<Value,String> {
    let spec=if cfg!(windows){json!({"program":"powershell.exe","args":["-NoProfile","-ExecutionPolicy","Bypass","-File",host.backend.parent().unwrap().join("bootstrap-windows.ps1")],"action":"runtime"})}
        else{json!({"program":host.helper,"args":["--studio-bootstrap"],"action":"runtime"})};
    launch(host.inner().clone(),app,spec)
}
#[tauri::command]
async fn studio_cleanup(mode:String,token:Option<String>,operation:Option<String>,app:tauri::AppHandle,host:State<'_,Arc<Host>>)->Result<Value,String> {
    let host=host.inner().clone();
    tauri::async_runtime::spawn_blocking(move||{
        let _gate=host.task_lock.lock().map_err(|e|e.to_string())?;
        if host.active.lock().unwrap().is_some(){return Err("Pause and finish the active task before removing packages.".into());}
        if host.older_app_open(){return Err("Close the previous AniCanto app before removing downloaded packages.".into());}
        let operation=operation.unwrap_or_default();
        if operation.len()>80 || !operation.bytes().all(|c|c.is_ascii_alphanumeric()||c==b'-'){return Err("Invalid cleanup operation.".into());}
        let request=json!({"root":host.root,"mode":mode,"token":token});
        let mut notify=|mut status:Value|{status["operationID"]=json!(operation);let _=app.emit("studio-cleanup-progress",status);};
        notify(json!({"phase":"checking"}));
        #[cfg(windows)] if mode=="all" && token.is_some(){
            let launcher=std::env::var("CANTOSYNC_LAUNCHER_PID").ok().and_then(|s|s.parse::<u32>().ok()).ok_or("Open the portable AniCanto.exe to remove runtimes safely on exit.")?;
            let approved=anicanto_core::cleanup::reviewed(&request)?;
            std::fs::write(host.root.join("download-cleanup-request.json"),json!({"mode":mode,"token":token,"launcherPID":launcher,"approved":approved}).to_string()).map_err(|e|e.to_string())?;
            notify(json!({"phase":"deferred"}));
            return Ok(json!({"deferred":true}));
        }
        if token.is_some(){anicanto_core::cleanup::execute_with_progress(&request,&mut notify)}else{anicanto_core::cleanup::plan(&request)}
    }).await.map_err(|e|e.to_string())?
}
// Exported movies may live in the user's chosen folder, outside app storage.
// Permit those exact registered files, not arbitrary paths or parent folders.
fn reveal_target(root:&PathBuf,raw:&str)->Result<PathBuf,String>{
    let path=PathBuf::from(raw).canonicalize().map_err(|e|e.to_string())?;
    let base=root.canonicalize().map_err(|e|e.to_string())?;
    if path.starts_with(&base){return Ok(path);}
    let state:Value=std::fs::read(root.join("studio/desktop-state.json")).ok()
        .and_then(|v|serde_json::from_slice(&v).ok()).unwrap_or(Value::Null);
    let registered=state["queue"].as_array().is_some_and(|rows|rows.iter().any(|row|
        ["output","previewOutput"].iter().any(|key|row[*key].as_str().is_some_and(|value|
            PathBuf::from(value).canonicalize().is_ok_and(|target|target==path&&target.is_file())))));
    if registered {Ok(path)} else {Err("Only app-owned files or a saved movie from this library can be revealed here.".into())}
}
#[tauri::command]
async fn studio_reveal(path:String,host:State<'_,Arc<Host>>)->Result<(),String>{
    let path=reveal_target(&host.root,&path)?;
    #[cfg(target_os="macos")] let mut cmd={let mut c=Command::new("/usr/bin/open");if path.is_file(){c.arg("-R");}c};
    #[cfg(windows)] let mut cmd={let mut c=Command::new("explorer.exe");if path.is_file(){c.arg("/select,");}c};
    #[cfg(not(any(target_os="macos",windows)))] let mut cmd=Command::new("xdg-open");
    cmd.arg(path).spawn().map_err(|e|e.to_string())?;Ok(())
}
// Only the fixed project address is opened. This is not an arbitrary URL or
// shell-command interface, and it does not send application/project data.
#[tauri::command]
async fn studio_open_project()->Result<(),String>{
    const URL:&str="https://github.com/samuelkcc/AniCanto";
    #[cfg(target_os="macos")] let mut cmd=Command::new("/usr/bin/open");
    #[cfg(windows)] let mut cmd={let mut c=Command::new("rundll32.exe");c.arg("url.dll,FileProtocolHandler");c};
    #[cfg(not(any(target_os="macos",windows)))] let mut cmd=Command::new("xdg-open");
    cmd.arg(URL).spawn().map_err(|e|e.to_string())?;Ok(())
}
fn main(){
    let host=match Host::discover(){Ok(h)=>Arc::new(h),Err(error)=>{rfd::MessageDialog::new().set_title("AniCanto").set_description(&error).show();return}};
    // Headless verification exercises the exact same allowlist and dispatch as
    // the desktop command, rather than bypassing it through the Python adapter.
    if std::env::args().any(|arg|arg=="--verify-desktop-operation") {
        let mut input=String::new();
        let result=std::io::stdin().read_line(&mut input).map_err(|e|e.to_string()).and_then(|_|serde_json::from_str::<Value>(&input).map_err(|e|e.to_string())).and_then(|request|{
            let op=request["op"].as_str().ok_or("Missing desktop operation")?;
            host.desktop_rpc(op,request.get("params").cloned().unwrap_or(json!({})))
        });
        match result{Ok(value)=>println!("{}",json!({"ok":true,"result":value})),Err(error)=>{println!("{}",json!({"ok":false,"error":error}));std::process::exit(1)}}return;
    }
    if std::env::args().any(|arg|arg=="--verify-studio") {
        let result=host.rpc("state",json!({})).and_then(|state|host.rpc("models",json!({})).map(|models|json!({"ok":true,"state":state,"installedModels":models,"sharedResources":host.shared,"adapter":host.backend,"interfaceManifest":serde_json::from_str::<Value>(include_str!("../../web/assets/interface-manifest.json")).unwrap()})));
        match result{Ok(value)=>println!("{value}"),Err(error)=>{eprintln!("{error}");std::process::exit(1)}}return;
    }
    tauri::Builder::default().manage(host).manage(TaskLifecycle::default()).manage(QueueControl::default()).manage(StartupWindow(Arc::new(AtomicBool::new(false))))
        .setup(|app|{
            let preference=appearance::saved(&app.state::<Arc<Host>>().root);
            let window=tauri::WebviewWindowBuilder::from_config(app.handle(),&app.config().app.windows[0])?
                .visible(false).theme(appearance::theme(&preference))
                .background_color(appearance::background(preference=="dark"))
                .initialization_script(appearance::script(&preference)).build()?;
            // A script error must never leave the app invisible indefinitely.
            let shown=app.state::<StartupWindow>().0.clone();
            std::thread::spawn(move||{
                std::thread::sleep(std::time::Duration::from_secs(5));
                if !shown.swap(true,Ordering::AcqRel){
                    let dark=window.theme().is_ok_and(|t|t==tauri::Theme::Dark);
                    let _=window.set_background_color(Some(appearance::background(dark)));
                    let _=window.show();
                }
            });
            Ok(())
        })
        .on_page_load(|webview,payload|{
            #[cfg(windows)] if payload.event()==tauri::webview::PageLoadEvent::Finished {
                if let Some(path)=std::env::var_os("CANTOSYNC_LAUNCH_READY_PATH") {
                    let path=PathBuf::from(path);let host=webview.state::<Arc<Host>>();
                    // Only an app-owned, launcher-specific ready signal.
                    if path.parent()==Some(host.root.join("logs").as_path()) && path.file_name().is_some_and(|n|n.to_string_lossy().starts_with("launch-ready-")) {
                        let _=std::fs::write(path,b"{\"ready\":true}");
                    }
                }
            }
            #[cfg(not(windows))] let _=(webview,payload);
        })
        .invoke_handler(tauri::generate_handler![studio_ack_finished,studio_appearance,studio_rpc,studio_status,studio_pick,studio_start,studio_pause,studio_media,studio_stop_stream,studio_thumbnail,studio_subtitles,studio_bootstrap,studio_cleanup,studio_reveal,studio_open_project,studio_export_logs,studio_export_speech])
        .on_window_event(|window,event|{if let tauri::WindowEvent::CloseRequested{api,..}=event{
            let host=window.state::<Arc<Host>>();if host.task_lock.try_lock().is_err(){api.prevent_close();let _=window.emit("studio-cleanup-close-requested",());return;}if host.active.lock().unwrap().is_some(){api.prevent_close();let _=window.emit("studio-close-requested",());}
            else {preview_stream::stop_all();#[cfg(unix)] for pid in host.media.lock().unwrap().iter(){unsafe{libc::kill(-(*pid as i32),libc::SIGTERM);}}}
        }})
        .run(tauri::generate_context!()).expect("AniCanto desktop could not start");
}


#[cfg(test)]
mod cleanup_progress_tests {
    use super::*;
    #[test]
    #[cfg(unix)]
    fn live_owned_worker_blocks_source_checks_and_model_removal() {
        let root=std::env::temp_dir().join(format!("anicanto-owned-{}",std::process::id()));
        std::fs::create_dir_all(&root).unwrap();
        let child=Command::new("/bin/sleep").arg("10").spawn().unwrap();
        let instance=OpenOptions::new().create(true).truncate(false).read(true).write(true).open(root.join("instance.lock")).unwrap();
        let host=Host{root:root.clone(),shared:root.clone(),windows:root.clone(),backend:root.clone(),helper:root.clone(),recovery_checked:AtomicBool::new(true),rpc_lock:Mutex::new(()),task_lock:Mutex::new(()),active:Mutex::new(Some(Active{child,id:"owned".into(),row:Some("row".into()),paused:false,setup:false,action:"batch".into(),model_id:None,started:Instant::now()})),media:Arc::new(Mutex::new(HashSet::new())),_instance:instance};
        assert_eq!(host.desktop_rpc("source-language",json!({"id":"next"})).unwrap_err(),"Pause processing before checking another source language.");
        assert_eq!(host.desktop_rpc("reset-video",json!({"id":"next"})).unwrap_err(),"Pause processing before resetting a video.");
        assert_eq!(host.desktop_rpc("remove-model",json!({"id":"unused"})).unwrap_err(),"Pause processing before removing a model.");
        let mut task=host.active.lock().unwrap().take().unwrap();task.child.kill().unwrap();let _=task.child.wait();
        drop(host);std::fs::remove_dir_all(root).unwrap();
    }
    #[test]
    fn progress_is_readable_while_cleanup_owns_the_rpc_lock() {
        let nonce=std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos();
        let root=std::env::temp_dir().join(format!("anicanto-progress-{}-{nonce}",std::process::id()));
        std::fs::create_dir_all(&root).unwrap();
        let receipt=root.join("project-cache-progress.json");
        std::fs::write(&receipt,json!({"operationID":"test-operation","phase":"deleting","processed":2,"total":4}).to_string()).unwrap();
        let instance=OpenOptions::new().create(true).truncate(false).read(true).write(true).open(root.join("instance.lock")).unwrap();
        let host=Arc::new(Host{root:root.clone(),shared:root.clone(),windows:root.clone(),backend:root.clone(),helper:root.clone(),recovery_checked:AtomicBool::new(false),rpc_lock:Mutex::new(()),task_lock:Mutex::new(()),active:Mutex::new(None),media:Arc::new(Mutex::new(HashSet::new())),_instance:instance});
        let held=host.rpc_lock.lock().unwrap();let reader=host.clone();let (tx,rx)=std::sync::mpsc::channel();
        let worker=std::thread::spawn(move||{let _=tx.send(reader.desktop_rpc("project-cache-status",json!({"operationID":"test-operation"})));});
        let result=rx.recv_timeout(std::time::Duration::from_secs(2));
        drop(held);worker.join().unwrap();
        let value=result.expect("Status must bypass the cleanup RPC lock").unwrap();
        assert_eq!(value["processed"],2);assert_eq!(value["total"],4);
        assert_eq!(host.desktop_rpc("project-cache-status",json!({"operationID":"old-operation"})).unwrap(),Value::Null);
        assert!(host.desktop_rpc("project-cache-status",json!({"operationID":"../escape"})).is_err());
        std::fs::write(&receipt,"{interrupted write").unwrap();
        assert_eq!(host.desktop_rpc("project-cache-status",json!({"operationID":"test-operation"})).unwrap(),Value::Null);
        drop(host);std::fs::remove_dir_all(root).unwrap();
    }
    #[test]
    fn reveal_accepts_exact_export_and_preview_but_not_unregistered_files_or_parent(){
        let nonce=std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos();
        let folder=std::env::temp_dir().join(format!("anicanto-reveal-{}-{nonce}",std::process::id()));
        let root=folder.join("owned");std::fs::create_dir_all(root.join("studio")).unwrap();
        let outside=folder.join("Google Drive");std::fs::create_dir_all(&outside).unwrap();
        let output=outside.join("episode.mp4");let preview=outside.join("episode-Preview.mp4");let unrelated=outside.join("other.txt");
        for path in [&output,&preview,&unrelated]{std::fs::write(path,b"fixture").unwrap();}
        std::fs::write(root.join("studio/desktop-state.json"),json!({"queue":[{"output":output,"previewOutput":preview}]}).to_string()).unwrap();
        for path in [&output,&preview,&root]{assert!(reveal_target(&root,path.to_str().unwrap()).is_ok());}
        for path in [&unrelated,&outside]{assert!(reveal_target(&root,path.to_str().unwrap()).is_err());}
        std::fs::remove_dir_all(folder).unwrap();
    }

}
