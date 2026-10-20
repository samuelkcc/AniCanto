$ErrorActionPreference = 'Stop'
$DataRoot = if ($env:CANTOSYNC_WINDOWS_DATA) { $env:CANTOSYNC_WINDOWS_DATA } else { Join-Path $env:LOCALAPPDATA 'CantoSync-Windows' }
$Python = Join-Path $DataRoot 'runtimes\ui\Scripts\python.exe'
$Installer=Join-Path $PSScriptRoot 'shared\runtime_installer.py'
if (!(Test-Path $Python)) { throw 'Run Start-AniCanto.cmd first to install the desktop runtime.' }
& $Python $Installer $DataRoot pip $Python install 'pyinstaller==6.14.2'
if ($LASTEXITCODE -ne 0) { throw 'Could not install the Windows packager.' }
Push-Location $PSScriptRoot
try {
    & $Python -m PyInstaller --noconfirm --onedir --console --name AniCanto-Windows --paths shared `
        --add-data 'shared;shared' --add-data 'tools;tools' --add-data 'models.json;.' `
        --add-data 'artwork;artwork' `
        --hidden-import studio `
        --add-data 'jobs.py;.' --add-data 'install.py;.' --add-data 'native_tts.py;.' `
        --add-data 'downloads.py;.' --add-data 'gpu.py;.' --add-data 'requirements-cosy.lock;.' `
        --add-data 'requirements-gpt.lock;.' --add-data 'requirements-qwen.lock;.' `
        --hidden-import imageio_ffmpeg --collect-all imageio_ffmpeg app.py
    if ($LASTEXITCODE -ne 0) { throw 'Windows EXE build failed.' }
    Write-Host 'Built dist\AniCanto-Windows\AniCanto-Windows.exe. Keep the whole directory together.'
} finally { Pop-Location }
