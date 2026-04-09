# ESP32 MicroPython Firmware

This is the firmware package for the merged `WebApps/greenhouse-monitor` setup.

## Important network rule

The ESP32 boards should send readings to the Windows host over your local network.

Use:

```text
http://<your-windows-pc-lan-ip>:5105/api/v1/readings
```

Do not point the boards at:

- `localhost`
- `127.0.0.1`
- the Cloudflare hostname
- an `https://` URL

Cloudflare Tunnel is only for browser access to the dashboards from outside your home. The sensors should keep talking directly to the PC on your LAN.

## Default wiring

- DHT22 data pin: `GPIO4`
- I2C SDA: `GPIO21`
- I2C SCL: `GPIO22`
- BH1750 I2C address: `0x23`
- SH1106 OLED I2C address: `0x3C`

The BH1750 and SH1106 share the same I2C bus on the greenhouse board.

## Files to copy to each board

- `boot.py`
- `main.py`
- one `app_config.py` file for the target board
- every file from `lib/`

## Board configs

- `boards/greenhouse/app_config.py`
- `boards/outdoor/app_config.py`
- `boards/test_dht22/app_config.py`
- `boards/portable_demo/app_config.py`

For the normal greenhouse deployment:

1. Copy the right board file to the ESP32 as `app_config.py`
2. Set `WIFI_SSID`
3. Set `WIFI_PASSWORD`
4. Set `WINDOWS_SERVER_LAN_IP` to the LAN IP of the PC running Docker Desktop

The upload URL is now built automatically from that IP using port `5105`.

## Run modes

- `summer`: upload every 60 seconds to `SERVER_URL`
- `range_test`: upload every 10 seconds to `SERVER_URL`
- `component_test`: upload every 10 seconds to `TEMP_WINDOWS_SERVER_URL` when set, otherwise `SERVER_URL`
- `display_only`: refresh the OLED locally without WiFi or HTTP uploads

Switch modes by editing `RUN_MODE` in `app_config.py`.

`test_dht22` is the DHT22-only test profile. It disables the BH1750 and OLED so you can run `range_test` with just the DHT22 connected.

`portable_demo` is the self-contained OLED demo profile. It reads sensors and updates the display without WiFi or uploads.

## Recovery behavior

- `boot.py` runs automatically at power-on
- `main.py` restarts the board after unexpected failures
- `MAX_PENDING_UPLOADS` controls how many unsent readings stay in RAM while WiFi or the server is unavailable

That lets the nodes recover after a power outage and flush a short backlog if the Windows PC takes longer to boot than the ESP32 boards.
