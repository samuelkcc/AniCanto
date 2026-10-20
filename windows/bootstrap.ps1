param([ValidateSet('auto','nvidia','amd','intel','cpu')][string]$Backend = 'auto')
$ErrorActionPreference = 'Stop'
$PackageRoot = $PSScriptRoot
$Version = (Get-Content -LiteralPath (Join-Path $PackageRoot 'VERSION.json') -Raw | ConvertFrom-Json).version
$DataRoot = if ($env:CANTOSYNC_WINDOWS_DATA) { $env:CANTOSYNC_WINDOWS_DATA } else { Join-Path $env:LOCALAPPDATA 'CantoSync-Windows' }
$env:PYTHONNOUSERSITE = '1'
$Shared = Join-Path $PackageRoot 'shared'
$Bootstrap = Join-Path $Shared 'python-bootstrap.ps1'
$Python = Join-Path $DataRoot 'runtimes\ui\Scripts\python.exe'
New-Item -ItemType Directory -Force -Path (Join-Path $DataRoot 'logs') | Out-Null
$Log = Join-Path $DataRoot ('logs\setup-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
Start-Transcript -Path $Log | Out-Null
$Form = $null
$SetupJob = $null
$script:SetupCancelled = $false
$script:SetupComplete = $false
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
$Form = New-Object System.Windows.Forms.Form
$Form.Text = 'AniCanto - first launch'
$Form.ClientSize = New-Object System.Drawing.Size(560,230)
$Form.StartPosition = 'CenterScreen'
$Form.FormBorderStyle = 'FixedDialog'
$Form.MaximizeBox = $false
$Form.BackColor = [System.Drawing.Color]::White
$Title = New-Object System.Windows.Forms.Label
$Title.Text = 'Preparing your dubbing studio'
$Title.Font = New-Object System.Drawing.Font('Segoe UI',16,[System.Drawing.FontStyle]::Bold)
$Title.SetBounds(26,24,510,35)
$Status = New-Object System.Windows.Forms.Label
$Status.SetBounds(26,72,510,40)
$Status.Text = 'Checking the application and existing components...'
$Bar = New-Object System.Windows.Forms.ProgressBar
$Bar.SetBounds(26,122,508,14)
$Bar.Style = 'Marquee'
$Bar.MarqueeAnimationSpeed = 30
$Detail = New-Object System.Windows.Forms.Label
$Detail.SetBounds(26,153,510,48)
$Detail.Text = 'This runs once. Existing downloads are reused. Closing this window pauses setup.'
$Form.Controls.AddRange(@($Title,$Status,$Bar,$Detail))
$Form.Add_FormClosing({ if (!$script:SetupComplete) { $script:SetupCancelled = $true } })
$Form.Show()
[System.Windows.Forms.Application]::DoEvents()
function Invoke-SetupTool([string]$Tool,[string[]]$ToolArguments,[string]$Message) {
    $Status.Text = $Message
    $Started = Get-Date
    $script:SetupJob = Start-Job -ScriptBlock {
        param($Command,$Arguments)
        & $Command @Arguments 2>&1 | ForEach-Object { $_.ToString() }
        if ($LASTEXITCODE -ne 0) { throw ('Setup command failed with exit code ' + $LASTEXITCODE) }
    } -ArgumentList $Tool,$ToolArguments
    try {
        while ($script:SetupJob.State -in @('NotStarted','Running')) {
            [System.Windows.Forms.Application]::DoEvents()
            if ($script:SetupCancelled) { Stop-Job $script:SetupJob; throw 'Setup paused. Downloaded files are kept for the next launch.' }
            $Lines = @(Receive-Job $script:SetupJob)
            foreach ($Line in $Lines) { Write-Host $Line }
            $Seconds = [int]((Get-Date)-$Started).TotalSeconds
            $Detail.Text = ('Elapsed ' + $Seconds + ' sec - ' + $(if ($Lines.Count) { [string]$Lines[-1] } else { 'Working. First installation can take several minutes.' }))
            Start-Sleep -Milliseconds 100
        }
        Receive-Job $script:SetupJob | ForEach-Object { Write-Host $_ }
        if ($script:SetupJob.State -ne 'Completed') { throw $script:SetupJob.ChildJobs[0].JobStateInfo.Reason }
    } finally { Remove-Job $script:SetupJob -Force; $script:SetupJob = $null }
}
try {
    if (![Environment]::Is64BitOperatingSystem) { throw 'Windows x64 is required.' }
    if ((Get-CimInstance Win32_OperatingSystem).BuildNumber -lt 22000) { throw 'Use Windows 11 for this test package.' }
    if (!(Test-Path $Bootstrap)) { throw 'The private Python bootstrap is missing. Copy AniCanto.exe again.' }
    if (!(Test-Path $Python)) {
        Invoke-SetupTool 'powershell.exe' @('-NoProfile','-ExecutionPolicy','Bypass','-File',$Bootstrap,'-DataRoot',$DataRoot,'-Resources',$Shared,'-Environment','runtimes\ui') 'Step 1 of 3 - preparing private Python'
    }
    $Ready = Join-Path $DataRoot 'ui-ready.txt'
    $RequirementsHash = (Get-FileHash -LiteralPath (Join-Path $PackageRoot 'requirements-ui.txt') -Algorithm SHA256).Hash.ToLower()
    $NeedsInstall = !(Test-Path $Ready) -or (Get-Content $Ready -Raw).Trim() -ne $RequirementsHash
    if (!$NeedsInstall) {
        try { Invoke-SetupTool $Python @('-c','import PySide6.QtWidgets, av, numpy, soundfile, imageio_ffmpeg, httpx') 'Checking existing interface components' }
        catch { if ($script:SetupCancelled) { throw }; $NeedsInstall = $true; Remove-Item -LiteralPath $Ready -ErrorAction SilentlyContinue }
    }
    if ($NeedsInstall) {
        Invoke-SetupTool $Python @((Join-Path $Shared 'runtime_installer.py'),$DataRoot,'pip',$Python,'install','-r',(Join-Path $PackageRoot 'requirements-ui.txt')) 'Step 2 of 3 - installing missing interface components'
        Invoke-SetupTool $Python @('-c','import PySide6.QtWidgets, av, numpy, soundfile, imageio_ffmpeg, httpx') 'Step 3 of 3 - verifying the interface'
        Set-Content -Path $Ready -Value $RequirementsHash
    }
    $env:PYTHONUTF8 = '1'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:CANTOSYNC_SETUP_BACKEND = $Backend
    $script:SetupComplete = $true
    $Bar.Style = 'Continuous'
    $Bar.Value = 100
    $Status.Text = 'Ready - opening AniCanto'
    [System.Windows.Forms.Application]::DoEvents()
    $Form.Close()
    & $Python (Join-Path $PackageRoot 'desktop.py')
    if ($LASTEXITCODE -ne 0) { throw 'The desktop closed with an error. See the setup log.' }
} catch {
    [System.Windows.Forms.MessageBox]::Show(($_.Exception.Message + "`n`nLog: " + $Log),'AniCanto setup') | Out-Null
    throw
} finally {
    if ($script:SetupJob) { Stop-Job $script:SetupJob; Remove-Job $script:SetupJob -Force }
    if ($Form) { $Form.Dispose() }
    Stop-Transcript | Out-Null
}
