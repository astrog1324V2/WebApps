# Cloudflare Tunnel Setup (Windows 11)

This guide exposes the Docker-hosted apps on your Windows PC without opening router ports.

It matches the current stack exactly:

- `home.yourdomain.com` -> homepage hub on `http://localhost:8080`
- `yahtzee.yourdomain.com` -> `http://localhost:5102`
- `math.yourdomain.com` -> `http://localhost:5103`
- `nutrition.yourdomain.com` -> `http://localhost:5104`
- `greenhouse.yourdomain.com` -> `http://localhost:5105`

The homepage has been updated so that when you open it through `home.yourdomain.com`, its buttons can automatically switch to the matching public subdomains above.

## Before you start

1. Your domain must already be managed by Cloudflare
2. Docker Desktop should be running on the PC
3. The webapps stack should be up:

```powershell
cd F:\Codex_Projects\WebApps
docker compose up --build -d
```

## 1) Install `cloudflared`

In PowerShell:

```powershell
winget install --id Cloudflare.cloudflared
cloudflared --version
```

## 2) Log in and create the tunnel

```powershell
cloudflared tunnel login
cloudflared tunnel create webapps-tunnel
```

Save the tunnel ID shown by the second command.

## 3) Create the tunnel config

Create:

```text
C:\Users\<YOUR_WINDOWS_USER>\.cloudflared\config.yml
```

Use this template and replace the placeholders:

```yaml
tunnel: <YOUR_TUNNEL_ID>
credentials-file: "C:\\Users\\<YOUR_WINDOWS_USER>\\.cloudflared\\<YOUR_TUNNEL_ID>.json"

ingress:
  - hostname: home.yourdomain.com
    service: http://localhost:8080
  - hostname: yahtzee.yourdomain.com
    service: http://localhost:5102
  - hostname: math.yourdomain.com
    service: http://localhost:5103
  - hostname: nutrition.yourdomain.com
    service: http://localhost:5104
  - hostname: greenhouse.yourdomain.com
    service: http://localhost:5105
  - service: http_status:404
```

## 4) Create DNS routes

```powershell
cloudflared tunnel route dns webapps-tunnel home.yourdomain.com
cloudflared tunnel route dns webapps-tunnel yahtzee.yourdomain.com
cloudflared tunnel route dns webapps-tunnel math.yourdomain.com
cloudflared tunnel route dns webapps-tunnel nutrition.yourdomain.com
cloudflared tunnel route dns webapps-tunnel greenhouse.yourdomain.com
```

## 5) Run the tunnel

Manual run:

```powershell
cloudflared tunnel run webapps-tunnel
```

Then test:

- `https://home.yourdomain.com`
- `https://yahtzee.yourdomain.com`
- `https://math.yourdomain.com`
- `https://nutrition.yourdomain.com`
- `https://greenhouse.yourdomain.com`

## 6) Auto-start the tunnel on boot

Run PowerShell as Administrator:

```powershell
cloudflared service install
```

That installs `cloudflared` as a Windows service. It will reconnect the tunnel after reboot.

## 7) What still needs to start after a reboot

If Docker Desktop is set to start with Windows and restart containers automatically, the apps will come back on their own.

Recommended Docker Desktop settings:

1. Enable "Start Docker Desktop when you sign in"
2. Leave each compose service on `restart: unless-stopped` as it already is

After a reboot, verify:

```powershell
cd F:\Codex_Projects\WebApps
docker compose ps
```

If needed:

```powershell
docker compose up -d
```

## Important note for the ESP32s

Do not change the ESP32 upload target to the Cloudflare URL.

Keep each ESP32 pointed at the PC's LAN address:

```text
http://<your-windows-pc-lan-ip>:5105/api/v1/readings
```

Cloudflare Tunnel is for browsers reaching your dashboards from outside your home. The ESP32s should keep sending readings directly to the Windows host over your local network.

The board configs you should edit are in `greenhouse-monitor/esp32/boards/`. Set `WINDOWS_SERVER_LAN_IP` there before flashing the ESP32s.

## Troubleshooting

- `502 Bad Gateway`
- The target container is not running. Check:

```powershell
docker compose ps
docker compose logs greenhouse
```

- Homepage opens but app links still show `:510x`
- Make sure you opened the hub through `home.yourdomain.com`, not `localhost:8080`
- The homepage only switches to public subdomains when the current hostname is already public

- Greenhouse page loads but no new sensor data appears
- Confirm the ESP32 `SERVER_URL` is the LAN IP and port `5105`
- Confirm Windows Firewall allows inbound TCP `5105` on your local network

- Cloudflare DNS route says the hostname already exists
- Remove the old DNS entry in Cloudflare, then rerun the `cloudflared tunnel route dns` command
