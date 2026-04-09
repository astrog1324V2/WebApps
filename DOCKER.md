# Docker Setup

This repo runs the homepage plus every app, including the greenhouse dashboard, from one root `compose.yaml`.

## What you get

- Homepage hub on `http://localhost:8080`
- Yahtzee on `http://localhost:5102`
- Daily Math on `http://localhost:5103`
- Nutrition Label To Excel on `http://localhost:5104`
- Greenhouse Monitor on `http://localhost:5105`

## Requirements

- Windows 11
- Docker Desktop installed and running

## First-time setup

1. Open PowerShell in `F:\Codex_Projects\WebApps`
2. Copy the example env file:

```powershell
Copy-Item .env.example .env
```

3. Edit `.env` if needed:
- Set `OPENAI_API_KEY` if you use Daily Math generation or nutrition label scanning
- Leave the greenhouse values alone unless you want a different timezone or stale timeout
- Set `GREENHOUSE_ARCHIVE_SHARE_DIR` only if you want the archive endpoint to copy weekly CSVs somewhere else

4. Regenerate the derived files from the shared app registry:

```powershell
python .\tools\sync_app_registry.py
```

## Start the full stack

Foreground:

```powershell
docker compose up --build
```

Detached:

```powershell
docker compose up --build -d
```

Stop without deleting persisted data:

```powershell
docker compose down
```

See container status:

```powershell
docker compose ps
```

See greenhouse logs:

```powershell
docker compose logs -f greenhouse
```

## Greenhouse data layout

The greenhouse service persists everything under `WebApps/data/greenhouse`.

- Dashboard database: `data/greenhouse/greenhouse.db`
- Inside station file: `data/greenhouse/device-readings/greenhouse.csv`
- Outside station file: `data/greenhouse/device-readings/outdoor.csv`
- Combined exports: `data/greenhouse/exports`

The dashboard uses the SQLite database for fast current/history queries and also writes each station to its own append-only CSV file so the sensor history is easy to inspect or back up directly.

## ESP32 upload URL

Each ESP32 should post to the Windows PC over your LAN, not through Cloudflare.

Set the upload URL in each ESP32 config to:

```text
http://<your-windows-pc-lan-ip>:5105/api/v1/readings
```

Examples:

```text
http://192.168.1.50:5105/api/v1/readings
http://10.0.0.42:5105/api/v1/readings
```

Browser access from outside your home will go through Cloudflare Tunnel, but the ESP32 devices should keep talking directly to the PC on the local network.

The firmware files now live in `greenhouse-monitor/esp32`. Edit the matching board file in `greenhouse-monitor/esp32/boards/`, set `WINDOWS_SERVER_LAN_IP`, then copy it to the board as `app_config.py`.

## Common commands

Rebuild only the greenhouse service:

```powershell
docker compose up --build greenhouse
```

Restart just the greenhouse container:

```powershell
docker compose restart greenhouse
```

Open a shell in the greenhouse container:

```powershell
docker compose exec greenhouse sh
```

## Add another app later

The single source of truth is `infra/app_registry.json`.

1. Add the app entry there
2. Run:

```powershell
python .\tools\sync_app_registry.py
```

That regenerates:

- `compose.yaml`
- `home-page/apps.json`

If the new app needs persistent storage, add a `volumes` entry in the app's `run` block and create the matching folder under `data/`.

## Notes

- The homepage understands both local ports and Cloudflare-style subdomains derived from `infra/app_registry.json`.
- Docker is the preferred path now; the local PowerShell/bash launchers remain available for non-Docker testing.
