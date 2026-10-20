param([Parameter(Mandatory=$true)][string]$DataRoot,[Parameter(Mandatory=$true)][string]$Resources,[string]$Environment='')
$ErrorActionPreference='Stop'
if (![Environment]::Is64BitOperatingSystem) { throw 'Windows x64 is required.' }
$Manifest=Get-Content -LiteralPath (Join-Path $Resources 'python-installer.json') -Raw | ConvertFrom-Json
$Spec=$Manifest.platforms.'windows-x64'
if ($Spec.directory -notmatch '^cpython-3\.12\.\d+-x86_64-pc-windows-msvc$') { throw 'Invalid Python bootstrap manifest.' }
$PythonRoot=Join-Path $DataRoot 'python'
$Downloads=Join-Path $DataRoot 'downloads'
New-Item -ItemType Directory -Force -Path $PythonRoot,$Downloads | Out-Null
$Base=Join-Path $PythonRoot $Spec.directory
$BasePython=Join-Path $Base 'python.exe'
$Lock=$null
for ($i=0;$i -lt 120;$i++) {
    try { $Lock=[System.IO.File]::Open((Join-Path $PythonRoot '.bootstrap.lock'),'OpenOrCreate','ReadWrite','None'); break }
    catch [System.IO.IOException] { Start-Sleep -Seconds 1 }
}
if (!$Lock) { throw 'Another private Python setup is still running.' }
$Stage=$null
function Test-Python([string]$Executable) {
    if (!(Test-Path -LiteralPath $Executable)) { return $false }
    & $Executable -I -c "import ssl,json,venv,sys,platform;assert sys.version_info[:2]==(3,12) and platform.machine().lower() in ('amd64','x86_64')" 2>&1 | Out-Host
    return ($LASTEXITCODE -eq 0)
}
function Test-Archive([string]$Path) {
    return ((Test-Path -LiteralPath $Path) -and (Get-Item -LiteralPath $Path).Length -eq $Spec.size -and (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLower() -eq $Spec.sha256)
}
try {
    foreach ($Key in @('PYTHONHOME','PYTHONPATH','__PYVENV_LAUNCHER__')) { [Environment]::SetEnvironmentVariable($Key,$null,'Process') }
    $Marker=Join-Path $Base '.anicanto-python-verified'
    $Ready=(Test-Path -LiteralPath $Marker) -and ((Get-Content -LiteralPath $Marker -Raw).Trim() -eq $Spec.sha256) -and (Test-Python $BasePython)
    if (!$Ready) {
        Write-Output (@{stage='Runtime';message='Downloading / verifying private Python. Existing downloads are reused.'} | ConvertTo-Json -Compress)
        $Archive=Join-Path $Downloads ($Spec.directory+'.tar.gz')
        if (!(Test-Archive $Archive)) {
            $Partial=$Archive+'.partial'
            if (!(Test-Archive $Partial)) {
                if ((Test-Path -LiteralPath $Partial) -and (Get-Item -LiteralPath $Partial).Length -ge $Spec.size) { Remove-Item -LiteralPath $Partial }
                & "$env:SystemRoot\System32\curl.exe" --fail --location --retry 3 --connect-timeout 30 --max-time 1800 --continue-at - --output $Partial $Spec.url
                if ($LASTEXITCODE -ne 0) { throw 'Python download was interrupted. Reopen to resume.' }
            }
            if (!(Test-Archive $Partial)) { Remove-Item -LiteralPath $Partial -ErrorAction SilentlyContinue; throw 'Private Python checksum mismatch; rejected.' }
            Move-Item -LiteralPath $Partial -Destination $Archive -Force
        }
        $Stage=Join-Path $PythonRoot ('.staging-'+[guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $Stage | Out-Null
        & "$env:SystemRoot\System32\tar.exe" -xzf $Archive -C $Stage
        if ($LASTEXITCODE -ne 0) { throw 'Private Python archive extraction failed.' }
        if (!(Test-Python (Join-Path $Stage 'python\python.exe'))) { throw 'Private Python did not pass verification.' }
        Set-Content -LiteralPath (Join-Path $Stage 'python\.anicanto-python-verified') -Value $Spec.sha256
        if (Test-Path -LiteralPath $Base) { Move-Item -LiteralPath $Base -Destination ($Base+'.rejected-'+[guid]::NewGuid().ToString('N')) }
        Move-Item -LiteralPath (Join-Path $Stage 'python') -Destination $Base
        if (!(Test-Python $BasePython)) { throw 'Installed private Python did not pass verification.' }
    }
} finally {
    if ($Stage -and (Test-Path -LiteralPath $Stage)) { Remove-Item -LiteralPath $Stage -Recurse -Force }
    if ($Lock) { $Lock.Dispose() }
}
if ($Environment) {
    if ($Environment -notmatch '^(runtimes[\\/])?[a-z][a-z0-9-]*$') { throw 'Invalid application environment name.' }
    & $BasePython (Join-Path $Resources 'runtime_installer.py') $DataRoot env $Environment
    if ($LASTEXITCODE -ne 0) { throw 'Private environment creation failed.' }
}
