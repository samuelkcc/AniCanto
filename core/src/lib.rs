//! Deterministic cross-platform policy. No UI, inference, network or shell execution.
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
pub mod cleanup;

pub const CATALOG: &str = include_str!("../../Resources/production-contract.json");
pub fn digest(bytes: &[u8]) -> String { format!("{:x}", Sha256::digest(bytes)) }
pub fn catalog() -> Value { serde_json::from_str(CATALOG).expect("build-time catalog") }

pub fn verify_package(folder:&std::path::Path,manifest:&str)->Result<(),String> {
    verify_package_with_progress(folder,manifest,|_,_|Ok(()))
}

/// Preserve full integrity checks while reporting work and allowing cancellation.
pub fn verify_package_with_progress<F>(folder:&std::path::Path,manifest:&str,mut progress:F)->Result<(),String>
where F:FnMut(usize,usize)->Result<(),String> {
    use std::path::Component;
    if std::fs::symlink_metadata(folder).map_err(|e|e.to_string())?.file_type().is_symlink() {return Err("package-root-symlink".into());}
    let entries:Value=serde_json::from_str(manifest).map_err(|e|e.to_string())?;
    let entries=entries.as_object().ok_or("invalid-package-manifest")?;
    if entries.is_empty() {return Err("empty-package-manifest".into());}
    progress(0,entries.len())?;
    for (index,(name,record)) in entries.iter().enumerate() {
        let relative=std::path::Path::new(name);
        if name.contains('\\') || name.contains(':') || relative.components().any(|c|!matches!(c,Component::Normal(_))) {
            return Err("invalid-package-path".into());
        }
        let mut path=folder.to_path_buf();
        for component in relative.components() {
            path.push(component);
            if std::fs::symlink_metadata(&path).map_err(|e|e.to_string())?.file_type().is_symlink() {return Err("package-symlink".into());}
        }
        let bytes=std::fs::read(&path).map_err(|e|e.to_string())?;
        if record["size"].as_u64()!=Some(bytes.len() as u64) || record["sha256"]!=digest(&bytes) {
            return Err(format!("package-file-changed:{name}"));
        }
        progress(index+1,entries.len())?;
    }
    Ok(())
}

fn strings(value: Option<&Value>, default: &[&str]) -> Result<Vec<String>, String> {
    let mut result = Vec::new();
    match value {
        None => result.extend(default.iter().map(|s| s.to_string())),
        Some(Value::Array(rows)) => for row in rows {
            let s = row.as_str().ok_or("expected-string-list")?.to_string();
            if !result.contains(&s) { result.push(s); }
        },
        _ => return Err("expected-list".into()),
    }
    Ok(result)
}

/// Projects retain all existing inference settings; this is the portable production projection.
/// UI mode is deliberately absent from the identity: switching views cannot change a job.
pub fn plan(cfg: &Value) -> Result<Value, String> {
    if !cfg.is_object() { return Err("expected-settings-object".into()); }
    let c = catalog();
    let default = cfg["ttsBackend"].as_str().unwrap_or("drama3");
    let mut engines = strings(cfg.get("selectedEngines"), &[default])?;
    let retired=c["retiredEngines"].as_object().unwrap();
    if engines.iter().any(|id|retired.contains_key(id)) {
        let old=engines.clone();engines.retain(|id|!retired.contains_key(id));
        if engines.is_empty() {engines.push(if old.iter().any(|s|s=="gpt-sovits-v3") {"gpt-sovits"} else {"cosyvoice3"}.into());}
    }
    let languages = strings(cfg.get("dubLanguages"), &["yue"])?;
    if engines.is_empty() || languages.is_empty() { return Err("empty-voice-selection".into()); }
    if cfg["interfaceMode"] == "simple" && engines.len() != 1 { return Err("basic-mode-requires-one-engine".into()); }
    let known = c["engines"].as_array().unwrap();
    for engine in &engines {
        if !known.iter().any(|e| e["id"] == *engine) { return Err(format!("unknown-engine:{engine}")); }
    }
    for lang in &languages {
        if !["yue", "zh", "en"].contains(&lang.as_str()) { return Err(format!("unknown-language:{lang}")); }
        if !known.iter().any(|e| engines.iter().any(|id| e["id"] == *id) && e["languages"].as_array().unwrap().contains(&json!(lang))) {
            return Err(format!("unsupported-language:{lang}"));
        }
    }
    // Catalog order is stable; default audio is independent of presentation order.
    let ordered: Vec<String> = known.iter().filter_map(|e| {
        let id=e["id"].as_str().unwrap(); engines.iter().any(|v| v==id).then(|| id.to_string())
    }).collect();
    let primary = cfg["defaultAudioEngine"].as_str().unwrap_or(default);
    let primary = if engines.iter().any(|v| v==primary) {primary} else {&engines[0]};
    let ordered_languages: Vec<&str> = ["yue", "zh", "en"].into_iter().filter(|l| languages.iter().any(|v| v==l)).collect();
    let mut tracks = Vec::new();
    for language in &ordered_languages { for engine in known {
        let id=engine["id"].as_str().unwrap();
        if ordered.iter().any(|v| v==id) && engine["languages"].as_array().unwrap().contains(&json!(language)) {
            tracks.push(json!({"id":format!("{language}:{id}"),"engine":id,"language":language}));
        }
    }}
    let mut subs = strings(cfg.get("subtitleModes"), match cfg["subtitleOutput"].as_str().unwrap_or("yue") {
        "none" => &[], "english" => &["english"], "both"|"dual"|"separate" => &["yue","english"],
        "all"|"complete" => &["original","yue","english"], "original-yue"=> &["original","yue"],
        "original-english"=> &["original","english"], "original" => &["original"], _ => &["yue"],
    })?;
    if cfg["subtitleSelection"].as_str()==Some("automatic") {
        subs=ordered_languages.iter().map(|l| if *l=="en" {"english".to_string()} else {l.to_string()}).collect();
        if ordered_languages.contains(&"yue") && ordered_languages.contains(&"en") {subs.push("dual".to_string());}
        subs.push("original".to_string());
    }
    if subs.iter().any(|v| !["original","yue","zh","english","dual"].contains(&v.as_str())) {return Err("unknown-subtitle-mode".into());}
    let subtitles: Vec<&str> = ["yue","zh","english","dual","original"].into_iter().filter(|v| subs.iter().any(|s| s==v)).collect();
    let mut streams=Vec::new();
    if subtitles.contains(&"original") {
        if let Some(value)=cfg.get("originalSubtitleStreams") {
            for n in value.as_array().ok_or("invalid-subtitle-streams")? {
                streams.push(n.as_u64().ok_or("invalid-subtitle-stream-index")?);
            }
        }
    }
    streams.sort_unstable(); streams.dedup();
    let original=cfg["includeOriginal"].as_bool().unwrap_or(true);
    let mut result=json!({"schemaVersion":1,"policyRevision":c["policyRevision"],
        "engines":ordered,"primaryEngine":primary,"languages":ordered_languages,
        "tracks":tracks,"dubbedTrackCount":tracks.len(),"includeOriginal":original,
        "maximumAudioTrackCount":tracks.len()+usize::from(original),
        "subtitles":subtitles,"originalSubtitleStreams":streams,
        "legacySubtitleLayout":cfg["subtitleOutput"].as_str().unwrap_or("yue"),
        "burnSubtitles":cfg["burnOutputCaptions"].as_bool().unwrap_or(false),
        "cantoneseLocale":"yue-HK","autoRepair":cfg["aiAutoFix"].as_bool().unwrap_or(true),
        "translateOPED":cfg["translateOPED"].as_bool().unwrap_or(false),
        "detectOPED":cfg["autoSkipOP"].as_bool().unwrap_or(true),
        "allowCrossEngineRepair":cfg["allowCrossEngineRepair"].as_bool().unwrap_or(false)});
    result["identity"]=json!(digest(serde_json::to_string(&result).unwrap().as_bytes()));
    Ok(result)
}

/// Conservative planning estimates. A real native speech probe is required.
fn drama_memory(h:&Value,preference:&str)->Value {
    let vram=h["acceleratorMemoryGB"].as_f64().unwrap_or(0.);
    let free=h["acceleratorFreeMemoryGB"].as_f64().unwrap_or(vram);
    let need=if vram>=23.5 {18.}else if vram>=15.5 {12.}else if vram>=11.5 {9.}else{6.};
    let name=h["acceleratorName"].as_str().unwrap_or("").to_uppercase();
    let driver=h["cudaDriverVersion"].as_str().and_then(|v|v.split('.').next()).and_then(|v|v.parse::<u64>().ok());
    let needs_new_driver=(name.contains("RTX 50")||name.contains("BLACKWELL"))&&driver.is_some_and(|v|v<580);
    let cuda=!needs_new_driver && preference!="cpu" && h["backend"]=="cuda" && h["nativeDramaCUDA"]==true && vram>=7.5 && (free-(vram*0.1).max(0.5)).min(vram*0.8)>=need;
    let (layers,gpu)=if vram>=23.5 {(0,18.)} else if vram>=15.5 {(16,12.)} else if vram>=11.5 {(24,9.)} else {(32,6.)};
    json!({"backend":if cuda {"cuda"}else{"cpu"},"systemGB":22.,"gpuGB":if cuda {gpu}else{0.},
        "cpuExpertLayers":if cuda {layers}else{0},"contextLength":if cuda {2048}else{4096},
        "estimated":true,"policy":"full-drama-q2-split-1","requiresSpeechProbe":true})
}

/// Evaluate only registered adapters. GPU advertising is not evidence of successful model inference.
fn windows_deployment(req:&Value)->Result<Value,String> {
    let h=&req["hardware"];
    let ram=h["memoryGB"].as_f64().filter(|x|x.is_finite() && *x>0.).ok_or("memory-undetected")?;
    let reserve=(ram*0.15).max(8.);let host_budget=(ram-reserve).max(0.);
    let backend=h["backend"].as_str().unwrap_or("cpu");
    let gpu=h["acceleratorMemoryGB"].as_f64().unwrap_or(0.);
    let free=h["acceleratorFreeMemoryGB"].as_f64().unwrap_or(gpu);
    let budget=if ["cuda","rocm"].contains(&backend) {host_budget.min((gpu*0.8).min((free-(gpu*0.1).max(0.5)).max(0.)))} else {host_budget};
    let models=req["models"].as_array().ok_or("missing-model-catalog")?;
    let preference=req["dramaBackend"].as_str().unwrap_or("auto");
    if !["auto","cuda","cpu"].contains(&preference){return Err("invalid-drama-backend".into());}
    let voice_memory=drama_memory(h,preference);
    if req["engine"]=="drama3" && preference=="cuda" && voice_memory["backend"]!="cuda" {return Err("full-drama-cuda-requires-nvidia-8gb".into());}

    let installed=strings(req.get("installedModels"),&[])?;
    let valid=|m:&&Value| m["retired"]!=true && m["licenseReviewRequired"]!=true && m["nativeFormat"].is_string() && m["bytes"].as_u64().unwrap_or(0)>0 && m["files"].as_array().is_some_and(|f|!f.is_empty());
    let explicitly_requested=|m:&Value|req["requestedModels"].as_object().is_some_and(|roles|roles.values().any(|id|id==&m["id"]));
    let fits=|m:&&Value| valid(m) && m["estimatedMemoryGB"].as_f64().is_some_and(|n|{
        let cpu=m["engine"]!="cosyvoice3";
        let advised=if cpu {host_budget} else {budget};
        let physical=if cpu || !["cuda","rocm"].contains(&backend) {ram} else {ram.min(h["acceleratorMemoryGB"].as_f64().unwrap_or(0.))};
        n>0. && (n<=advised || explicitly_requested(m) && n<=physical)
    });
    let is_installed=|m:&Value|installed.iter().any(|id|m["id"]==*id);
    let manual=|role:&str,category:&str,engine:Option<&str>|->Result<Option<&Value>,String>{
        let Some(id)=req["requestedModels"][role].as_str() else{return Ok(None)};
        models.iter().find(|m|m["id"]==id && m["category"]==category && engine.is_none_or(|e|m["engine"]==e) && fits(m)).map(Some).ok_or_else(||format!("incompatible-requested-model:{role}:{id}"))
    };
    let existing=|role:&str,category:&str,engine:Option<&str>| models.iter().filter(|m|m["category"]==category && engine.is_none_or(|e|m["engine"]==e)).filter(fits).filter(|m|is_installed(m)).min_by(|a,b|{
        let priority=|m:&Value|if req["selectedModels"][role]==m["id"] {0u8} else {1};
        priority(a).cmp(&priority(b)).then_with(||b["parameterB"].as_f64().unwrap_or(0.).total_cmp(&a["parameterB"].as_f64().unwrap_or(0.)))
    });
    // 35B is explicit/installed only. The default tier is 4B or 9B.
    let text=manual("text","text",Some("ollama"))?.or_else(||existing("text","text",Some("ollama"))).or_else(||models.iter().filter(|m|m["engine"]=="ollama" && ["qwen3.5:9b"].contains(&m["id"].as_str().unwrap_or(""))).filter(fits).max_by(|a,b|a["parameterB"].as_f64().unwrap_or(0.).total_cmp(&b["parameterB"].as_f64().unwrap_or(0.))));
    let requested=req["engine"].as_str().unwrap_or("drama3");
    if requested=="cosyvoice3" && backend!="cuda" {return Err("cosyvoice3-requires-windows-nvidia".into());}
    if !catalog()["engines"].as_array().unwrap().iter().any(|e|e["id"]==requested) {return Err("unknown-engine".into());}
    // Full Q2 always needs host RAM, even with CUDA expert offload.
    // Dedicated VRAM is a separate pool; neither capacity substitutes for the other.
    let full_drama_fits=models.iter().any(|m|m["id"]=="drama3-native-q2" && fits(&m));
    let explicit_full=req["requestedModels"]["voice"]=="drama3-native-q2";
    let slow_drama=req["allowDramaCPU"].as_bool().unwrap_or(false) || (requested=="drama3" && full_drama_fits && (ram>=30. || explicit_full));
    let small=models.iter().find(|m|(h["nativeDramaSmallCPU"]==true || h["nativeDramaSmallCUDA"]==true) && m["id"]=="drama3-small-iq3" && valid(m) && m["estimatedMemoryGB"].as_f64().is_some_and(|n|n<=host_budget));
    let small_cuda=backend=="cuda" && h["nativeDramaSmallCUDA"]==true && small.is_some_and(|m|fits(&m));
    let small_fallback=requested=="drama3" && !slow_drama && small.is_some();
    let engine=if requested=="drama3" && !slow_drama && !small_fallback {"gpt-sovits-v2"} else {requested};
    let voice=manual("voice","voice",Some(engine))?.or_else(||if small_fallback {small} else {existing(engine,"voice",Some(engine)).or_else(||models.iter().filter(|m|m["category"]=="voice" && m["engine"]==engine).filter(|m|if engine=="drama3" && slow_drama {valid(m) && m["estimatedMemoryGB"].as_f64().is_some_and(|n|n<=host_budget)} else {fits(m)}).min_by_key(|m|m["bytes"].as_u64().unwrap_or(u64::MAX)))});
    let choose=|role:&str,category:&str,engine:Option<&str>|existing(role,category,engine).or_else(||models.iter().filter(|m|m["category"]==category && engine.is_none_or(|e|m["engine"]==e)).filter(fits).max_by(|a,b|a["parameterB"].as_f64().unwrap_or(0.).total_cmp(&b["parameterB"].as_f64().unwrap_or(0.))));
    let speech=manual("speech","speech",Some("whisper"))?.or_else(||choose("speech","speech",Some("whisper")));let asr=manual("asr","asr",Some("qwen3-asr"))?.or_else(||choose("asr","asr",Some("qwen3-asr")));
    let reference=if !req["requestedModels"]["referenceSpeech"].is_string() && (req["singleModelPerCategory"]==true || req["requestedModels"]["speech"].is_string()){speech}else{manual("referenceSpeech","speech",Some("whisper"))?.or_else(||existing("referenceSpeech","speech",Some("whisper"))).or_else(||models.iter().filter(|m|m["id"]=="whisper-small").filter(fits).next())};
    let mut blockers=Vec::new();let mut warnings=Vec::new();
    if text.is_none(){blockers.push("no-compatible-text-model");}
    if voice.is_none(){blockers.push("no-compatible-voice-model");}
    if speech.is_none() || asr.is_none() || reference.is_none(){blockers.push("no-compatible-speech-analysis-models");}
    if requested!=engine{warnings.push("native-drama-cuda-unavailable-fallback-gpt-v2-pro-plus");}
    if [text,voice,speech,asr].into_iter().flatten().any(|m|{
        let advised=if m["id"]=="drama3-native-q2" {host_budget} else {budget};
        m["estimatedMemoryGB"].as_f64().unwrap_or(0.)>advised
    }) {warnings.push("model-memory-pressure-swap-or-load-failure-possible");}
    if small_fallback {warnings.push(if small_cuda {"native-drama-small-cuda-planned"} else {"native-drama-small-cpu-fallback"});}
    else if engine=="drama3"{warnings.push(if voice_memory["backend"]=="cuda" {"native-drama-full-cuda-needs-probe"}else{"native-drama-cpu-explicit-slow-path"});}
    let visual=text.filter(|m|m["estimatedMemoryGB"].as_f64().unwrap_or(0.)+3.<=budget);
    if visual.is_none(){warnings.push("visual-analysis-unavailable-use-audio-roles");}
    let summarize=|m:&Value|json!({"id":m["id"],"title":m["title"],"repo":m["repo"],"revision":m["revision"],"bytes":m["bytes"],"estimatedMemoryGB":m["estimatedMemoryGB"],"estimatedSystemMemoryGB":if m["id"]=="drama3-native-q2" {voice_memory["systemGB"].clone()}else{Value::Null},"estimatedVRAMGB":if m["id"]=="drama3-native-q2" {voice_memory["gpuGB"].clone()}else{Value::Null},"nativeFormat":m["nativeFormat"],"installed":is_installed(m)});
    let mut downloads=Vec::new();
    for m in [text,visual,voice,speech,asr,reference].into_iter().flatten(){if !downloads.iter().any(|r:&Value|r["id"]==m["id"]){downloads.push(summarize(m));}}
    for m in models.iter().filter(|m|m["category"]=="classifier").filter(fits){downloads.push(summarize(m));}
    let bytes=downloads.iter().filter(|m|m["installed"]!=true).map(|m|m["bytes"].as_u64().unwrap_or(0)).sum::<u64>();
    let roles=json!({"text":text.map(|m|&m["id"]),"visual":visual.map(|m|&m["id"]),"voice":voice.map(|m|&m["id"]),"speech":speech.map(|m|&m["id"]),"asr":asr.map(|m|&m["id"]),"referenceSpeech":reference.map(|m|&m["id"])});
    Ok(json!({"schemaVersion":1,"hardware":h,"requestedEngine":requested,"engine":engine,"voiceBackend":if small_fallback && small_cuda {"cuda"} else if engine=="drama3" {voice_memory["backend"].as_str().unwrap_or("cpu")} else {backend},"dramaBackend":preference,"voiceMemory":if engine=="drama3"&&!small_fallback {voice_memory.clone()}else{Value::Null},"warnings":warnings,"blockers":blockers,"roles":roles,"downloads":downloads,"text":text.map(summarize),"voice":voice.map(summarize),"memoryBudgetGB":budget,"systemMemoryBudgetGB":host_budget,"acceleratorMemoryBudgetGB":if ["cuda","rocm"].contains(&backend){budget}else{0.},"systemReserveGB":reserve,"modelDownloadBytes":bytes,"runtimeDownloadBytes":null,"canDeployModels":blockers.is_empty(),"fullWorkflowReady":false,"roleAnalysisMode":if visual.is_some(){"audiovisual"}else{"audio"},"stagesRunSerially":true,"requiresRuntimeAndAuxiliaryModels":true,"additionalComponents":["native-worker","native-asr","native-separator","speakers","ffmpeg","ollama"]}))
}

fn deployment_inner(req: &Value) -> Result<Value,String> {
    if req["hardware"]["platform"]=="windows" && req["hardware"]["architecture"]=="x86_64" && req["hardware"]["nativeWorkflowVersion"]==1 {return windows_deployment(req);}
    let h=&req["hardware"];
    let ram=h["memoryGB"].as_f64().filter(|n| n.is_finite() && *n>0.).ok_or("memory-undetected")?;
    let platform=h["platform"].as_str().ok_or("platform-undetected")?;
    let arch=h["architecture"].as_str().ok_or("architecture-undetected")?;
    let backend=h["backend"].as_str().unwrap_or("cpu");
    let reserve=(ram*0.15).max(8.);
    let mut budget=(ram-reserve).max(0.);
    if backend=="metal" { budget=budget.min(h["acceleratorBudgetGB"].as_f64().unwrap_or(0.)); }
    if ["cuda","rocm","xpu"].contains(&backend) {budget=budget.min(h["acceleratorMemoryGB"].as_f64().unwrap_or(0.)*0.8);}
    let models=req["models"].as_array().ok_or("missing-model-catalog")?;
    // A 32 GB Mac can attempt full Drama 3 when explicitly shown a memory-pressure
    // warning. Its 28 GB estimate exceeds the usual 24 GB model budget, so this
    // is an exception for this voice model only, not a smaller memory estimate.
    let mac_drama_32=platform=="macos" && arch=="aarch64" && backend=="metal" && ram>=32.;
    let explicitly_requested=|m:&Value|req["requestedModels"].as_object().is_some_and(|roles|roles.values().any(|id|id==&m["id"]));
    let fits=|m:&&Value| m["retired"]!=true && m["licenseReviewRequired"]!=true && m["estimatedMemoryGB"].as_f64().is_some_and(|n| n>0. && (n<=if m["id"]=="drama3-small-iq3" {(ram-reserve).max(0.)} else {budget} || (mac_drama_32 && m["id"]=="drama3-35b-4bit" || explicitly_requested(m)) && n<=ram))
        && m["bytes"].as_u64().unwrap_or(0)>0
        && m["files"].as_array().is_some_and(|files| !files.is_empty())
        && m["revision"].as_str().is_some_and(|r| r.len()==40 && r.bytes().all(|c| c.is_ascii_hexdigit()));
    let apple=platform=="macos" && arch=="aarch64" && backend=="metal";
    let mut candidates:Vec<&Value>=models.iter().filter(|m| apple && m["category"]=="text" && m["engine"]=="mlx-text"
        && ["mlx:qwen3.5-9b:4bit","mlx:qwen3.5-35b-a3b:4bit"].contains(&m["id"].as_str().unwrap_or(""))).filter(fits).collect();
    candidates.sort_by(|a,b| b["parameterB"].as_f64().unwrap_or(0.).total_cmp(&a["parameterB"].as_f64().unwrap_or(0.)));
    // Installation inventory is supplied by the host after checking local files.
    // Preserve a usable installed selection; hardware advice is for missing roles.
    let installed=strings(req.get("installedModels"), &[])?;
    let is_installed=|m:&Value| installed.iter().any(|id|m["id"]==*id);
    let manual=|role:&str,category:&str,engine:Option<&str>|->Result<Option<&Value>,String>{
        let Some(id)=req["requestedModels"][role].as_str() else{return Ok(None)};
        models.iter().find(|m|apple && m["id"]==id && m["category"]==category && engine.is_none_or(|e|m["engine"]==e) && fits(m)).map(Some).ok_or_else(||format!("incompatible-requested-model:{role}:{id}"))
    };
    let existing=|role:&str,category:&str,engine:Option<&str>| models.iter().filter(|m|apple && m["category"]==category
        && engine.is_none_or(|e|m["engine"]==e)).filter(fits).filter(|m|is_installed(m))
        .min_by(|a,b| {
            let priority=|m:&Value|if req["selectedModels"][role]==m["id"] {0u8} else {1};
            priority(a).cmp(&priority(b))
                .then_with(||b["parameterB"].as_f64().unwrap_or(0.).total_cmp(&a["parameterB"].as_f64().unwrap_or(0.)))
                .then_with(||b["bytes"].as_u64().unwrap_or(0).cmp(&a["bytes"].as_u64().unwrap_or(0)))
        });
    let text=manual("text","text",Some("mlx-text"))?.or_else(||existing("text","text",Some("mlx-text"))).or_else(||candidates.first().copied());
    // Match the visual worker's additional frame/vision-encoder allowance.
    let visual_fits=|m:&&Value|m["estimatedMemoryGB"].as_f64().unwrap_or(f64::INFINITY)+4.<=budget.min(ram*0.8);
    let visual=if req["singleModelPerCategory"]==true || req["requestedModels"]["text"].is_string(){text.filter(|m|visual_fits(m))}else{existing("visual","text",Some("mlx-text")).filter(|m|req["selectedModels"]["visual"]==m["id"] && visual_fits(m))
        .or_else(||text.filter(|m|visual_fits(m)))
        .or_else(||candidates.iter().copied().find(visual_fits))};
    let engine=req["engine"].as_str().unwrap_or("drama3");
    if !catalog()["engines"].as_array().unwrap().iter().any(|e|e["id"]==engine) {return Err("unknown-engine".into());}
    let voice_for=|selected:&str| models.iter().filter(|m|apple && m["category"]=="voice" && m["engine"]==selected).filter(fits)
        .min_by_key(|m|(if selected=="drama3" && m["id"]=="drama3-small-iq3" {1} else {0},m["bytes"].as_u64().unwrap_or(u64::MAX)));
    let mut voice=manual("voice","voice",Some(engine))?.or_else(||existing(engine,"voice",Some(engine))).or_else(||voice_for(engine));
    let mut effective_engine=engine;
    let mut warnings=Vec::new();
    if engine=="drama3" && voice.is_some_and(|m|m["id"]=="drama3-small-iq3") {warnings.push("drama3-small-cpu-fallback");}
    if apple && engine=="drama3" && voice.is_none() {
        if let Some(fallback)=voice_for("gpt-sovits-v2") {
            voice=Some(fallback);effective_engine="gpt-sovits-v2";
            warnings.push("drama3-memory-budget-fallback-gpt-v2-pro-plus");
        }
    }
    let auxiliary=|category:&str| models.iter().filter(|m|apple && m["category"]==category && (m["precision"]=="4bit" || m["engine"]=="whisper"))
        .filter(fits).max_by(|a,b|a["parameterB"].as_f64().unwrap_or(0.).total_cmp(&b["parameterB"].as_f64().unwrap_or(0.)));
    let speech=manual("speech","speech",Some("whisper"))?.or_else(||existing("speech","speech",Some("whisper"))).or_else(||auxiliary("speech"));
    let asr=manual("asr","asr",None)?.or_else(||existing("asr","asr",None)).or_else(||auxiliary("asr"));
    if [text,voice,speech,asr].into_iter().flatten().any(|m|m["estimatedMemoryGB"].as_f64().unwrap_or(0.)>budget) {warnings.push("model-memory-pressure-swap-or-load-failure-possible");}
    let reference=if !req["requestedModels"]["referenceSpeech"].is_string() && (req["singleModelPerCategory"]==true || req["requestedModels"]["speech"].is_string()){speech}else{manual("referenceSpeech","speech",Some("whisper"))?.or_else(||existing("referenceSpeech","speech",Some("whisper"))).or_else(||models.iter().filter(|m|apple && m["id"]=="whisper-small").filter(fits).next())};
    let summarize=|m:&Value| json!({"id":m["id"],"title":m["title"],"repo":m["repo"],"revision":m["revision"],"bytes":m["bytes"],"estimatedMemoryGB":m["estimatedMemoryGB"],"installed":is_installed(m)});
    let mut blockers=Vec::new();
    if !apple {blockers.push("automatic-platform-adapter-not-integrated");}
    if text.is_none() {blockers.push("no-compatible-text-model");}
    if visual.is_none() {warnings.push("visual-analysis-unavailable-use-audio-roles");}
    if voice.is_none() {blockers.push("no-compatible-voice-model");}
    if speech.is_none() || asr.is_none() || reference.is_none() {blockers.push("no-compatible-speech-analysis-models");}
    let mut downloads=Vec::new();
    for model in [text,visual,voice,speech,asr,reference].into_iter().flatten() {
        if !downloads.iter().any(|m:&Value|m["id"]==model["id"]) {downloads.push(summarize(model));}
    }
    let bytes=downloads.iter().filter(|m|m["installed"]!=true).map(|m|m["bytes"].as_u64().unwrap_or(0)).sum::<u64>();
    let mut roles=json!({"text":text.map(|m|&m["id"]),"voice":voice.map(|m|&m["id"]),
        "speech":speech.map(|m|&m["id"]),"referenceSpeech":reference.map(|m|&m["id"]),"asr":asr.map(|m|&m["id"])});
    if let Some(model)=visual {roles["visual"]=model["id"].clone();}
    Ok(json!({"schemaVersion":1,"hardware":h,"engine":effective_engine,"requestedEngine":engine,"warnings":warnings,
        "roleAnalysisMode":if visual.is_some() {"audiovisual"} else {"audio"},"memoryBudgetGB":budget,
        "systemReserveGB":reserve,"text":text.map(summarize),"voice":voice.map(summarize),
        "roles":roles,"downloads":downloads,"additionalComponents":["base-runtime","text-visual-runtime","separator","speakers"],
        "modelDownloadBytes":bytes,"runtimeDownloadBytes":null,"blockers":blockers,
        "canDeployModels":blockers.is_empty(),"fullWorkflowReady":false,
        "stagesRunSerially":true,"requiresRuntimeAndAuxiliaryModels":true}))
}

/// Quality choices use the SAME real hardware and feasibility policy as installation.
/// Unavailable templates never borrow a different engine or relax the memory guard.
pub fn deployment(req:&Value)->Result<Value,String> {
    // Runtime generation is chosen independently from model-memory fit.
    let mut normalized=req.clone();
    if normalized["hardware"]["platform"]=="windows" && normalized["hardware"]["backend"]=="cuda" {
        let name=normalized["hardware"]["acceleratorName"].as_str().unwrap_or("").to_uppercase();
        let cc=normalized["hardware"]["cudaComputeCapability"].as_f64();
        let policy:Value=serde_json::from_str(include_str!("../../Resources/hardware-runtimes.json")).unwrap();
        let driver=normalized["hardware"]["cudaDriverVersion"].as_str().and_then(|v|v.split('.').next()).and_then(|v|v.parse::<u64>().ok()).unwrap_or(0);
        let preferred=normalized["hardware"]["selectedTorchIndex"].as_str();
        let mut options=policy["nvidia"].as_array().unwrap().iter().filter(|p|driver>=p["minimumDriverMajor"].as_u64().unwrap_or(0)).collect::<Vec<_>>();
        options.sort_by_key(|p|if preferred.is_some_and(|index|p["torchIndex"]==index){0}else{1});
        let profile=options.into_iter().find(|p|{
            if let Some(cc)=cc {cc>=p["minimumCC"].as_f64().unwrap()&&cc<=p["maximumCC"].as_f64().unwrap()}
            else{p["nameHints"].as_array().unwrap().iter().any(|h|name.contains(h.as_str().unwrap()))}
        });
        if let Some(p)=profile {normalized["hardware"]["gpuRuntime"]=p.clone();normalized["hardware"]["torchIndex"]=p["torchIndex"].clone();}
        else if !name.is_empty(){
            normalized["hardware"]["detectedBackend"]=json!("cuda");normalized["hardware"]["backend"]=json!("cpu");normalized["hardware"]["suggestedSetupBackend"]=json!("cpu");
            normalized["hardware"]["gpuCompatibilityReason"]=json!("This GPU architecture is not covered by the pinned CUDA runtimes. CPU processing is available.");
        }
    }
    if normalized["hardware"]["platform"]=="windows" && normalized["hardware"]["backend"]=="rocm" {
        let name=normalized["hardware"]["acceleratorName"].as_str().unwrap_or("").to_uppercase();
        let name=name.strip_suffix(" GRAPHICS").unwrap_or(&name);
        let policy:Value=serde_json::from_str(include_str!("../../Resources/hardware-runtimes.json")).unwrap();
        let supported=name.is_empty()||policy["amd"]["models"].as_object().unwrap().keys().any(|m|name==m || name.ends_with(&format!(" {m}")));
        if !supported {normalized["hardware"]["detectedBackend"]=json!("rocm");normalized["hardware"]["backend"]=json!("cpu");normalized["hardware"]["suggestedSetupBackend"]=json!("cpu");normalized["hardware"]["gpuCompatibilityReason"]=json!("This Radeon is outside the pinned Windows ROCm support list. CPU processing is available.");}
    }
    let req=&normalized;
    let mut result=deployment_inner(req)?;
    let h=&req["hardware"];let apple=h["platform"]=="macos" && h["architecture"]=="aarch64";
    let windows=h["platform"]=="windows" && h["architecture"]=="x86_64";
    let backend=h["backend"].as_str().unwrap_or("unprobed");
    let ram=h["memoryGB"].as_f64().unwrap_or(0.);
    let budget=result["memoryBudgetGB"].as_f64().unwrap_or(0.);
    let models=req["models"].as_array().ok_or("missing-model-catalog")?;
    let mut presets=Vec::new();
    for (id,title,size,voice,engine,min_ram,description) in [
        ("quality","Highest quality",if windows || ram<64. {"9b"} else {"35b"},if apple {"drama3-35b-4bit"} else {"drama3-native-q2"},"drama3",if apple && ram>=64. {64.} else {32.},if windows {"Full Drama 3 Q2 uses NVIDIA CUDA when selected and supported, with CPU/RAM offload. AMD and integrated graphics use CPU for Drama 3. Setup must verify actual loading and speech."} else if ram<64. {"Full Drama 3 + Qwen 9B can be tried on a 32 GB Apple Silicon Mac. The 28 GB voice-model estimate exceeds the 24 GB budget after reserving 8 GB for macOS; swap and severe slowdowns are possible. 64 GB is the tested best-quality recommendation."} else {"Best Cantonese results in project listening tests so far: full Drama 3 + Qwen 35B on Apple Silicon with 64 GB memory. Other hardware and model formats have not been shown to match these results."}),
        ("balanced","Balanced","9b","v2ProPlus","gpt-sovits-v2",16.,"GPT-SoVITS V2 Pro Plus + Qwen 9B. A lower-memory alternative; voice expression, pronunciation and translation detail may differ from the highest-quality setup.")
    ] {
        let text=if apple {format!("mlx:qwen3.5-{}:4bit",if size=="35b" {"35b-a3b"} else {size})} else {format!("qwen3.5:{size}")};
        let asr=if apple {match id {"quality"=>"asr-1.7b-bf16","balanced"=>"asr-1.7b-8bit",_=>"asr-0.6b-4bit"}} else {"asr-native-1.7b"};
        let speech=if id=="compact" {"whisper-small"} else {"whisper-large-v3"};
        let requested=json!({"text":text,"voice":voice,"asr":asr,"speech":speech,"referenceSpeech":speech});
        let mut proposal=req.clone();proposal["engine"]=json!(engine);proposal["requestedModels"]=requested.clone();
        proposal["singleModelPerCategory"]=json!(true);proposal["allowDramaCPU"]=json!(windows && engine=="drama3");
        let mut blockers=Vec::<String>::new();
        if !apple && !windows {blockers.push("platform-not-supported".into());}
        // Windows reports usable RAM after hardware reservations, not DIMM size.
        // Nominal tiers allow that reservation; actual pool fit below stays strict.
        if ram<min_ram && !(windows && ram>=min_ram-2.) {blockers.push("insufficient-system-memory".into());}
        let mut peak=0f64;let mut host_peak=0f64;let mut gpu_peak=0f64;
        for ident in [text.as_str(),voice,asr,speech] {
            if let Some(model)=models.iter().find(|m|m["id"]==ident && m["retired"]!=true){
                let need=model["estimatedMemoryGB"].as_f64().unwrap_or(f64::INFINITY);
                peak=peak.max(need);
                if windows && ident=="drama3-native-q2" {
                    let memory=drama_memory(h,req["dramaBackend"].as_str().unwrap_or("auto"));
                    host_peak=host_peak.max(memory["systemGB"].as_f64().unwrap_or(22.));
                    gpu_peak=gpu_peak.max(memory["gpuGB"].as_f64().unwrap_or(0.));
                } else if windows && ["cuda","rocm"].contains(&backend) && need<=budget {gpu_peak=gpu_peak.max(need);} else {host_peak=host_peak.max(need);}
                if model["licenseReviewRequired"]==true {blockers.push("model-license-review-required".into());}
            } else {blockers.push("model-package-unavailable".into());}
        }
        let host_budget=(ram-(ram*0.15).max(8.)).max(0.);
        if windows {
            if host_peak>host_budget {blockers.push("insufficient-system-memory".into());}
            if gpu_peak>budget {blockers.push(if backend=="cpu" {"insufficient-model-memory"} else {"insufficient-gpu-memory"}.into());}
        } else if peak>budget && !(apple && ram>=32. && ram<64. && voice=="drama3-35b-4bit" && peak<=ram) {blockers.push("insufficient-model-memory".into());}
        let planned=deployment_inner(&proposal);
        let mut plan=match planned {Ok(p)=>p,Err(_)=>{blockers.push("requested-model-plan-unavailable".into());json!({})}};
        if let Some(list)=plan["blockers"].as_array(){for b in list {if let Some(b)=b.as_str(){blockers.push(b.into());}}}
        if !plan.is_null() && plan["roles"]["voice"].is_string() && plan["roles"]["voice"]!=voice {blockers.push("requested-quality-not-supported".into());}
        blockers.sort();blockers.dedup();
        plan["canDeployModels"]=json!(blockers.is_empty());plan["blockers"]=json!(blockers);
        presets.push(json!({"id":id,"title":title,"description":description,"engine":engine,"requestedModels":requested,
            "modelSummary":format!("{} + Qwen {}",if id=="quality" {"Drama 3"}else{"GPT-SoVITS V2 Pro Plus"},size.to_uppercase()),"minimumSystemMemoryGB":min_ram,"estimatedPeakModelGB":peak,"availableModelBudgetGB":budget,
            "memoryPressure":apple && peak>budget,
            "minimumDedicatedVRAMGB":if windows && ["cuda","rocm"].contains(&backend){Some((gpu_peak/0.8).ceil())}else{None},
            "estimatedSystemPeakGB":host_peak,"estimatedAcceleratorPeakGB":gpu_peak,
            "available":blockers.is_empty(),"blockers":blockers,"plan":plan}));
    }
    if windows {
        for original in presets.clone() {
            if backend=="cpu" {break;}
            let mut proposal=req.clone();proposal["hardware"]["backend"]=json!("cpu");proposal["hardware"]["suggestedSetupBackend"]=json!("cpu");
            proposal["engine"]=original["engine"].clone();proposal["requestedModels"]=original["requestedModels"].clone();proposal["dramaBackend"]=json!("cpu");proposal["allowDramaCPU"]=json!(true);
            if let Ok(mut cpu)=deployment_inner(&proposal){
                let available=cpu["canDeployModels"]==true && ram>=original["minimumSystemMemoryGB"].as_f64().unwrap_or(0.)-2.;
                cpu["setupBackend"]=json!("cpu");
                let mut preset=original.clone();preset["id"]=json!(format!("{}-cpu",original["id"].as_str().unwrap()));preset["title"]=json!(format!("{} · CPU",original["title"].as_str().unwrap()));
                preset["available"]=json!(available);preset["blockers"]=cpu["blockers"].clone();preset["minimumDedicatedVRAMGB"]=Value::Null;preset["executionBackend"]=json!("cpu");preset["plan"]=cpu;
                if !available && preset["blockers"].as_array().is_some_and(|x|x.is_empty()){preset["blockers"]=json!(["insufficient-system-memory"]);}
                presets.push(preset);
            }
        }
        if backend=="cpu" {
            for p in &mut presets {p["executionBackend"]=json!("cpu");p["plan"]["setupBackend"]=json!("cpu");}
            presets.sort_by_key(|p|if p["id"]=="balanced" {0}else{1});
        }
        // GPU profile first; when it does not fit, offer the faster lower-memory
        // CPU voice alternative before the much larger full Drama CPU model.
        if !presets.iter().any(|p|p["available"]==true && !p["id"].as_str().unwrap_or("").ends_with("-cpu")) && backend!="cpu" {
            presets.sort_by_key(|p|match p["id"].as_str().unwrap_or(""){"balanced-cpu"=>0,"quality-cpu"=>1,_=>2});
        }
    }
    result["recommendedPreset"]=presets.iter().find(|p|p["available"]==true).map(|p|p["id"].clone()).unwrap_or(Value::Null);
    result["qualityPresets"]=json!(presets);
    result["hardwarePolicy"]=json!({"supportedPlatforms":["Apple Silicon","Windows x64"],"intelMacSupported":false,
        "gpuInferenceVerified":h["inferenceVerified"].as_bool().unwrap_or(false),"memoryIsEstimate":true,"stagesRunSerially":true});
    Ok(result)
}

pub fn hardware() -> Value {
    #[cfg(target_os="macos")]
    fn memory() -> Option<u64> {
        use std::ffi::c_void;
        extern "C" { fn sysctlbyname(name:*const i8, old:*mut c_void, len:*mut usize, new:*mut c_void, newlen:usize)->i32; }
        let mut size=0u64; let mut len=8usize;
        let ok=unsafe {sysctlbyname(b"hw.memsize\0".as_ptr().cast(),(&mut size as *mut u64).cast(),&mut len,std::ptr::null_mut(),0)};
        (ok==0).then_some(size)
    }
    #[cfg(target_os="windows")]
    fn memory() -> Option<u64> {
        #[repr(C)] struct Status {length:u32,load:u32,total:u64,available:u64,page_total:u64,page_available:u64,virtual_total:u64,virtual_available:u64,extended:u64}
        #[link(name="kernel32")] extern "system" {fn GlobalMemoryStatusEx(status:*mut Status)->i32;}
        let mut s=Status{length:std::mem::size_of::<Status>() as u32,load:0,total:0,available:0,page_total:0,page_available:0,virtual_total:0,virtual_available:0,extended:0};
        (unsafe{GlobalMemoryStatusEx(&mut s)}!=0).then_some(s.total)
    }
    #[cfg(not(any(target_os="windows",target_os="macos")))]
    fn memory()->Option<u64>{None}
    let result=json!({"platform":std::env::consts::OS,"architecture":std::env::consts::ARCH,
        "cpuThreads":std::thread::available_parallelism().map(|n|n.get()).ok(),"memoryGB":memory().map(|n|n as f64/1073741824.),"backend":"unprobed", "inferenceVerified":false});
    #[cfg(target_os="windows")]
    {
        let mut result=result;
        use windows::Win32::Graphics::Dxgi::{CreateDXGIFactory1,IDXGIFactory1};
        let mut adapters=Vec::new();
        if let Ok(factory)=unsafe{CreateDXGIFactory1::<IDXGIFactory1>()} {
            for index in 0..32 {
                let Ok(adapter)=(unsafe{factory.EnumAdapters1(index)}) else {break};
                let Ok(desc)=(unsafe{adapter.GetDesc1()}) else {continue};
                if ![0x10de,0x1002,0x8086].contains(&desc.VendorId){continue;}
                let end=desc.Description.iter().position(|c|*c==0).unwrap_or(desc.Description.len());
                adapters.push(json!({"name":String::from_utf16_lossy(&desc.Description[..end]),
                    "vendorId":desc.VendorId,"dedicatedMemoryGB":desc.DedicatedVideoMemory as f64/1073741824.,
                    "sharedMemoryGB":desc.SharedSystemMemory as f64/1073741824.}));
            }
        }
        result["displayAdapters"]=json!(adapters);
        result
    }
    #[cfg(not(target_os="windows"))]
    {result}
}

pub fn dispatch(req:Value)->Result<Value,String> {
    match req["operation"].as_str() {
        Some("catalog")=>Ok(json!({"catalog":catalog(),"sha256":digest(CATALOG.as_bytes())})),
        Some("plan")=>plan(&req["settings"]),
        Some("deployment")=>deployment(&req),
        Some("hardware")=>Ok(hardware()),
        Some("cleanup-plan")=>cleanup::plan(&req),
        Some("cleanup-downloads")=>cleanup::execute(&req),
        _=>Err("unknown-operation".into()),
    }
}
