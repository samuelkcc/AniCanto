"""Build an arm64 macOS app. Homebrew is used ONLY on the build machine."""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
APP = Path(os.environ.get("CANTO_BUILD_APP",str(ROOT / "dist/AniCanto.app")))
CONTENTS = APP / "Contents"
RES = CONTENTS / "Resources"
BIN = RES / "bin"
LIB = CONTENTS / "Frameworks"
BUILD = ROOT / ".build"


def run(*args):
    return subprocess.check_output([str(x) for x in args], stderr=subprocess.STDOUT).decode()


def dependencies(path):
    return [line.strip().split(" (", 1)[0] for line in run("/usr/bin/otool", "-L", path).splitlines()[1:] if line.strip().startswith("/opt/homebrew/")]


def build():
    from python_installer_assets import prepare as installer_assets
    installer_assets()
    for p in [BIN, LIB, CONTENTS / "MacOS", BUILD]:
        p.mkdir(parents=True, exist_ok=True)
    from build_core import install as install_core
    install_core(BIN/'anicanto-core')
    run('python3', ROOT/'scripts/generate_contract.py', '--check')
    shutil.copy2(ROOT/'Resources/production-contract.json',RES/'production-contract.json')
    (BIN/'uv').unlink(missing_ok=True)
    for name in ('python-installer.json','python-bootstrap.sh','python-bootstrap.ps1','runtime_installer.py'):
        shutil.copy2(ROOT/'Resources'/name,RES/name)
    copied = {}

    def copy_binary(source, target):
        if str(target) in copied:
            return
        copied[str(target)] = str(source)
        shutil.copy2(source, target)
        target.chmod(0o755)
        deps = dependencies(source)
        for dep in deps:
            libtarget = LIB / Path(dep).name
            copy_binary(Path(dep), libtarget)
            newpath = "@loader_path/" + Path(dep).name if target.parent == LIB else "@executable_path/../../Frameworks/" + Path(dep).name
            run("/usr/bin/install_name_tool", "-change", dep, newpath, target)
        if target.parent == LIB:
            run("/usr/bin/install_name_tool", "-id", "@rpath/" + target.name, target)
        run("/usr/bin/codesign", "--force", "--sign", "-", target)

    for name in ["ffmpeg", "ffprobe"]:
        copy_binary(Path(shutil.which(name)), BIN / name)
    shutil.rmtree(RES / "__pycache__", ignore_errors=True)
    shutil.copy2(ROOT / "Resources/worker.py", RES / "worker.py")
    shutil.copy2(ROOT / "Resources/audio_format.py", RES / "audio_format.py")
    shutil.copy2(ROOT / "Resources/audio_manifest.py", RES / "audio_manifest.py")
    for name in ("soft_subtitles.py", "drama3.py", "role_reanalysis.py", "ai_result_repair.py", "signal_quality.py", "visual_identity.py", "character_observations.py","portrait_validation.py", "appearance_reconcile.py", "reference_quality.py", "source_reference.py", "gsv_reference.py", "cantonese_pronunciation.py", "script_revision.py", "voice_samples.py", "independent_voices.py", "natural_voices.py", "audio_audition.py", "voice_expression.py", "gsv_versions.py", "reference_recovery.py", "prosody_experiment.py", "pcm_mix.py", "video_acceleration.py"):
        shutil.copy2(ROOT / "Resources" / name, RES / name)
    for name in ["text_request_meter.py", "text_prompt_cache.py", "workflow_policy.py", "dialogue_units.py", "engine_policy.py", "visual_speakers.py", "visual-requirements.lock", "model-options.json", "model_catalog.py", "track_control.py", "runtime_recovery.py", "overlap_policy.py", "model_recovery.py", "processing_time.py", "audio_fallback.py", "project_store.py", "engine_reference.py", "qwen_recovery.py", "qwen_reference.py", "dub_languages.py", "voice_models.py", "voice-models.json", "project_edit.py", "artwork-provenance.json", "app-icon-prompt.txt", "companion-prompt.txt", "studio-restoration-prompt.txt", "theme-art-prompts.json", "mlx_text.py", "mlx-text-model.json", "text-requirements.lock", "MODEL-NOTICES.txt", "tts_health.py", "speech_level.py", "mix_balance.py", "pronunciation.py", "caption_tracks.py", "source_evidence.py", "hybrid_script.py", "multitrack.py", "qwen_voice.py", "qwen-voice-model.json", "qwen-requirements.lock", "repair_budget.py", "cantonese_style.py", "semantic_review.py", "script_preflight.py", "caption_allocation.py", "voicecheck.py", "quality.py", "speechcheck.py", "subtitle_render.py", "acoustics.py", "delivery.py", "nonverbal.py", "opening.py", "asr_verify.py", "asr-model.json", "asr-requirements.lock", "runtime_paths.py", "duration_fit.py", "dialogue.py", "cosy.py", "cosy-models.json", "cosy-requirements.lock", "speakers.py", "dubbing.py", "dubbing_setup.py", "model_download.py", "dubbing_runner.py", "mel-roformer.yaml", "gsv-requirements.lock", "separator-requirements.lock"]:
        shutil.copy2(ROOT / "Resources" / name, RES / name)
    shutil.copytree(ROOT / "Resources/wheels", RES / "wheels", dirs_exist_ok=True)
    shutil.copy2(ROOT / "Resources/demo.srt", RES / "demo.srt")
    for path in (ROOT/'Resources').glob('pet-*.png'):shutil.copy2(path,RES/path.name)
    shutil.copy2(ROOT/'Resources/pet-art-prompts.json',RES/'pet-art-prompts.json')
    for name in ('assistant-rigs.json','assistant-characters.json','assistant-animation.json'):
        shutil.copy2(ROOT/'Resources'/name,RES/name)
    shutil.copy2(ROOT/'Resources/PUBLIC-DISTRIBUTION.json',RES/'PUBLIC-DISTRIBUTION.json')
    shutil.copytree(ROOT/'Resources/natural-voices',RES/'natural-voices',dirs_exist_ok=True)
    for lang in ("en", "zh-HK"):
        shutil.copytree(ROOT / "Resources" / (lang+".lproj"), RES / (lang+".lproj"), dirs_exist_ok=True)
    (RES / "BUNDLED-COMPONENTS.json").write_text(json.dumps(copied, indent=2))
    (RES / "THIRD-PARTY-NOTICES.txt").write_text(
        "AniCanto Beta\n\nFFmpeg: https://ffmpeg.org/ ; this build includes GPL codecs (x264/x265).\n"
        + run(shutil.which("ffmpeg"), "-L")
        + "\nPrivate CPython and pip: pinned upstream distributions; see licenses/python-installer.\n"
        + "Ollama and isolated standalone Python runtimes are bundled; dependency licenses remain in site-packages distribution metadata. Model downloads are app-managed.\n"
        + "GPT-SoVITS source and models: https://github.com/RVC-Boss/GPT-SoVITS ; https://huggingface.co/lj1995/GPT-SoVITS\n"
        + "CosyVoice 3: https://github.com/QwenAudio/CosyVoice ; MLX adapter: https://github.com/DePasqualeOrg/mlx-audio-plus ; models: https://huggingface.co/mlx-community/Fun-CosyVoice3-0.5B-2512-4bit ; https://huggingface.co/mlx-community/S3TokenizerV3\n"
        + "WeSpeaker: https://github.com/wenet-e2e/wespeaker ; https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet34-LM\n"
        + "Audio separator: https://github.com/nomadkaraoke/python-audio-separator\n"
        + "Mel-Band RoFormer model: https://huggingface.co/KimberleyJSN/melbandroformer\n"
        + "Bundled Python wheels: jieba and jieba_fast. Each wheel includes its package metadata and available license notices.\n"
        + "This is an unsigned-development prototype for local testing, not a notarized public release.\n"
    )
    with (RES / "THIRD-PARTY-NOTICES.txt").open("a") as notices:
        notices.write("\nAniCanto original code: SCKC, MIT. See Licenses/AniCanto-MIT.txt.\nQwen3-TTS optional weights: Apache-2.0; https://github.com/QwenLM/Qwen3-TTS\nMLX Audio: MIT; https://github.com/Blaizzy/mlx-audio ; qwen-runtime packages retain their license metadata.\nOriginal generated character artwork; no official anime characters. Public distribution source/license audit remains outstanding.\n")
    for name in ('local_tts.py','local-tts-requirements.lock','ai_result_repair.py','runtime_exclusions.py','use_terms.py','model_licenses.py'):
        shutil.copy2(ROOT/'Resources'/name,RES/name)
    shutil.copytree(ROOT/'Resources/tts-vendor',RES/'tts-vendor',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    # Bundle distribution licenses from every Homebrew formula whose binaries are embedded.
    licenses = RES / "Licenses"
    licenses.mkdir(exist_ok=True)
    (licenses / "AniCanto-MIT.txt").unlink(missing_ok=True)
    shutil.copy2(ROOT / "LICENSE", licenses / "AniCanto-MIT.txt")
    for source in copied.values():
        source = Path(source).resolve()
        try:
            relative = source.relative_to("/opt/homebrew/Cellar")
        except ValueError:
            continue
        formula = Path("/opt/homebrew/Cellar") / relative.parts[0] / relative.parts[1]
        target = licenses / relative.parts[0]
        target.mkdir(exist_ok=True)
        for file in formula.rglob("*"):
            if file.is_file() and (file.name.upper().startswith(("LICENSE", "COPYING", "COPYRIGHT"))):
                shutil.copy2(file, target / file.name)
    run("/usr/bin/swiftc", "-swift-version", "5", "-O", "-target", "arm64-apple-macosx14.0", "-module-cache-path", BUILD / "ModuleCache", *sorted((ROOT / "Sources").glob("*.swift")), "-o", CONTENTS / "MacOS/AniCanto")
    shutil.copy2(ROOT / "Resources/AniCanto.icns", RES / "AniCanto.icns")
    release = json.loads((ROOT / "VERSION.json").read_text())
    info = {"CFBundleExecutable":"AniCanto", "CFBundleIdentifier":"local.sam.canto.sync", "CFBundleName":"AniCanto", "CFBundleDisplayName":"AniCanto", "CFBundleIconFile":"AniCanto.icns", "CFBundlePackageType":"APPL", "CFBundleShortVersionString":release["version"], "CFBundleVersion":release["build"], "CFBundleLocalizations":["en","zh-HK"], "CFBundleDevelopmentRegion":"zh-HK", "LSMinimumSystemVersion":"14.0", "NSHighResolutionCapable":True, "NSPrincipalClass":"NSApplication", "NSAppTransportSecurity":{"NSAllowsLocalNetworking":True}}
    with (CONTENTS / "Info.plist").open("wb") as f:
        plistlib.dump(info, f)
    # Keep all workflow modules and welcome artwork in source-built releases.
    for module in (ROOT / "Resources").glob("*.py"):
        shutil.copy2(module, RES / module.name)
    shutil.copy2(ROOT/'Resources/drama3-small-server',BIN/'drama3-small-server')
    shutil.copytree(ROOT / "Resources/welcome-art", RES / "welcome-art", dirs_exist_ok=True)
    from license_inventory import generate
    if os.environ.get('CANTO_BUNDLE_RUNTIMES')=='1':
        from bundle_runtimes import bundle
        bundle(RES,ROOT,BUILD)
    else:
        from lightweight_mac import prepare
        prepare(RES,ROOT)
    from release_notices import install as install_release_notices
    extra=install_release_notices(RES)
    inventory=generate(RES)+extra
    (RES/"license-inventory.json").write_text(json.dumps(inventory,ensure_ascii=False,indent=2))
    # Neutral, locally generated demo: no external media and no model needed.
    run("/usr/bin/swift", "-module-cache-path", BUILD / "ModuleCache", ROOT / "scripts/demo-captions.swift", BUILD)
    run(BIN / "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=960x540:rate=24", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-loop", "1", "-i", BUILD / "caption-0.png", "-loop", "1", "-i", BUILD / "caption-1.png", "-loop", "1", "-i", BUILD / "caption-2.png", "-filter_complex", "[0:v][2:v]overlay=enable='between(t,0.5,3.5)'[a];[a][3:v]overlay=enable='between(t,4,7.5)'[b];[b][4:v]overlay=enable='between(t,8,11.8)'[v]", "-map", "[v]", "-map", "1:a", "-t", "12", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", RES / "demo.mp4")
    run(BIN / "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=960x540:rate=24", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-i", ROOT / "Resources/demo.srt", "-i", ROOT / "Resources/demo-alternate.srt", "-map", "0:v", "-map", "1:a", "-map", "2:s", "-map", "3:s", "-t", "12", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-c:s", "srt", "-metadata:s:s:0", "language=zho", "-metadata:s:s:0", "title=繁體 · 示範 A", "-metadata:s:s:1", "language=yue", "-metadata:s:s:1", "title=廣東話 · 示範 B", RES / "multi-subtitle.mkv")
    from resource_assets import prune
    prune(RES)
    run("/usr/bin/codesign", "--force", "--deep", "--sign", "-", APP)
    run("/usr/bin/codesign", "--verify", "--deep", "--strict", APP)
    legacy = ROOT / "dist/Sam Canto Sync.app"
    if legacy.exists():
        import time
        shutil.move(str(legacy), str(BUILD / ("previous-app-" + str(time.time_ns()) + ".app")))
    print(APP)


if __name__ == "__main__":
    build()
