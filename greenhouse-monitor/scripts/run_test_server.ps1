$ErrorActionPreference = "Stop"

if (-not $env:GREENHOUSE_HOST) {
    $env:GREENHOUSE_HOST = "0.0.0.0"
}

if (-not $env:GREENHOUSE_PORT) {
    $env:GREENHOUSE_PORT = "8000"
}

python scripts/run_dev_server.py
