param(
    [switch]$Help
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Show-Usage {
    Write-Host "Usage:"
    Write-Host "  .\setup_local.ps1"
    Write-Host ""
    Write-Host "This sets up Python virtual environments for:"
    Write-Host "  - yahtzee-game"
    Write-Host "  - Daily_math_games_v2"
    Write-Host "  - nutrition-label-to-excel"
}

if ($Help) {
    Show-Usage
    exit 0
}

$RootDir = Split-Path -Parent $PSCommandPath

function Require-File {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Hint
    )
    if (-not (Test-Path -Path $Path -PathType Leaf)) {
        Write-Host "Missing: $Path"
        Write-Host "Hint: $Hint"
        exit 1
    }
}

function Setup-AppVenv {
    param(
        [Parameter(Mandatory = $true)][string]$AppName,
        [Parameter(Mandatory = $true)][string]$AppPath
    )

    $requirements = Join-Path $AppPath "requirements.txt"
    $venvDir = Join-Path $AppPath ".venv"
    $venvPython = Join-Path $venvDir "Scripts\python.exe"

    Write-Host ""
    Write-Host "[$AppName] setup starting..."
    Require-File -Path $requirements -Hint "Expected requirements.txt in $AppPath"

    if (-not (Test-Path -Path $venvPython -PathType Leaf)) {
        Write-Host "[$AppName] creating virtual environment..."
        & python -m venv $venvDir
    }
    else {
        Write-Host "[$AppName] virtual environment already exists."
    }

    Write-Host "[$AppName] upgrading pip..."
    & $venvPython -m pip install --upgrade pip

    Write-Host "[$AppName] installing requirements..."
    Push-Location $AppPath
    try {
        & $venvPython -m pip install -r $requirements
    }
    finally {
        Pop-Location
    }

    Write-Host "[$AppName] setup complete."
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python was not found in PATH."
    Write-Host "Install Python 3.10+ and reopen PowerShell."
    exit 1
}

$yahtzeePath = Join-Path $RootDir "yahtzee-game"
$mathPath = Join-Path $RootDir "Daily_math_games_v2"
$nutritionPath = Join-Path $RootDir "nutrition-label-to-excel"

Setup-AppVenv -AppName "yahtzee-game" -AppPath $yahtzeePath
Setup-AppVenv -AppName "Daily_math_games_v2" -AppPath $mathPath
Setup-AppVenv -AppName "nutrition-label-to-excel" -AppPath $nutritionPath

Write-Host ""
Write-Host "All setup complete."
Write-Host "Start services with: .\start_local.ps1 start"
