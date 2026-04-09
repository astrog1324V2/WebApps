$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $repoRoot "data\logs"
$logPath = Join-Path $logDir "windows-server.log"
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

if (Test-Path $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonCommand = Get-Command python -ErrorAction Stop
    $pythonExe = $pythonCommand.Source
}

Push-Location $repoRoot
try {
    & $pythonExe "scripts\run_dev_server.py" *>> $logPath
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
