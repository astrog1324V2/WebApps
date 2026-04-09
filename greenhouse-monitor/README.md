# Greenhouse Monitor

Embedded greenhouse dashboard for the shared `WebApps` stack.

## What it does

- Receives JSON readings from the greenhouse and outdoor ESP32 nodes
- Shows current conditions, stale/fresh device status, and recent history
- Stores a shared SQLite dashboard database plus append-only per-device CSV files
- Persists data under `WebApps/data/greenhouse`
- Includes the ESP32 MicroPython firmware package under `greenhouse-monitor/esp32`

## Host paths

- Combined dashboard database: `data/greenhouse/greenhouse.db`
- Inside station history file: `data/greenhouse/device-readings/greenhouse.csv`
- Outside station history file: `data/greenhouse/device-readings/outdoor.csv`

## Docker run command

This app is started by the root `compose.yaml`:

```powershell
docker compose up --build greenhouse
```

Then open `http://localhost:5105`.

## ESP32 upload URL

Point each ESP32 at:

```text
http://<your-pc-lan-ip>:5105/api/v1/readings
```

The ESP32s should keep posting to the LAN IP of the Windows host. Cloudflare Tunnel is for browser access to the dashboards, not for the sensors.

Use the board configs in `greenhouse-monitor/esp32/boards/` and edit `WINDOWS_SERVER_LAN_IP` before flashing the boards.

## Tests

```powershell
python -m unittest discover -s tests -v
```
