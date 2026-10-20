$ErrorActionPreference = 'Stop'
$PackageRoot=$env:CANTOSYNC_WINDOWS_PACKAGE
$DataRoot=$env:CANTOSYNC_WINDOWS_DATA
if (!$PackageRoot -or !$DataRoot) { throw 'Missing app-owned package or storage path.' }
$Shared=Join-Path $PackageRoot 'shared'
& (Join-Path $Shared 'python-bootstrap.ps1') -DataRoot $DataRoot -Resources $Shared -Environment 'runtimes\ui'
if ($LASTEXITCODE -ne 0) { throw 'Private Python installation was interrupted. Reopen to resume.' }
$Python=Join-Path $DataRoot 'runtimes\ui\Scripts\python.exe'
& $Python -I -c "import json,pathlib,ssl,subprocess;print(json.dumps(dict(stage='Runtime ready',message='Desktop runtime verified.',progress=1)))"
if ($LASTEXITCODE -ne 0) { throw 'Private Python did not pass verification.' }
