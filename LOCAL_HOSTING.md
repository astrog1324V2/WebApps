# Local Hosting Setup (Ubuntu)

This guide runs all apps on your Ubuntu desktop for local/LAN testing:

- Homepage hub: `http://<ubuntu-ip>:8080`
- Yahtzee: `http://<ubuntu-ip>:5102`
- Daily Math: `http://<ubuntu-ip>:5103`
- Nutrition Label: `http://<ubuntu-ip>:5104`
- Greenhouse Monitor: `http://<ubuntu-ip>:5105`

## Quick start (one command)

After you complete venv setup once, you can launch everything with:

```bash
cd ~/hosting_apps
bash ./star_local.sh start
```

Useful commands:

```bash
bash ./star_local.sh status
bash ./star_local.sh stop
bash ./star_local.sh restart
```

Optional env vars before start:

```bash
export OPENAI_API_KEY="sk-..."
export YAHTZEE_PORT=5102
export MATH_PORT=5103
export NUTRITION_PORT=5104
export GREENHOUSE_PORT=5105
export HUB_PORT=8080
```

## 1) Install prerequisites

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

## 2) Clone/open project

```bash
cd ~
git clone <your-repo-url> hosting_apps
cd hosting_apps
```

If the repo already exists, just `cd` into it.

## 3) Prepare each app environment

### Yahtzee (`yahtzee-game`)

```bash
cd ~/hosting_apps/yahtzee-game
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
deactivate
```

### Daily Math (`Daily_math_games_v2`)

```bash
cd ~/hosting_apps/Daily_math_games_v2
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
deactivate
```

### Nutrition Label (`nutrition-label-to-excel`)

```bash
cd ~/hosting_apps/nutrition-label-to-excel
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
deactivate
```

### Greenhouse Monitor (`greenhouse-monitor`)

```bash
cd ~/hosting_apps/greenhouse-monitor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
deactivate
```

## 4) Start all apps (5 terminals)

Run each block in its own terminal tab/window.

### Terminal A: Yahtzee on port 5102

```bash
cd ~/hosting_apps/yahtzee-game
source .venv/bin/activate
PORT=5102 python app.py
```

### Terminal B: Daily Math on port 5103

```bash
cd ~/hosting_apps/Daily_math_games_v2
source .venv/bin/activate
export OPENAI_API_KEY="sk-..."
uvicorn app.main:app --host 0.0.0.0 --port 5103
```

Notes:
- `OPENAI_API_KEY` is only required for generating new daily sets (`POST /generate`).
- Browsing existing static pages still works without a key.

### Terminal C: Nutrition Label on port 5104

```bash
cd ~/hosting_apps/nutrition-label-to-excel
source .venv/bin/activate
export OPENAI_API_KEY="sk-..."
python -m uvicorn nutrition_label_to_excel.app:app --app-dir src --host 0.0.0.0 --port 5104
```

Notes:
- `OPENAI_API_KEY` is required to analyze label photos.
- The UI itself loads without the key, but scans will fail until it is set.

### Terminal D: Homepage hub on port 8080

```bash
cd ~/hosting_apps
python3 -m http.server 8080 --bind 0.0.0.0 --directory home-page
```

### Terminal E: Greenhouse Monitor on port 5105

```bash
cd ~/hosting_apps/greenhouse-monitor
source .venv/bin/activate
export GREENHOUSE_HOST=0.0.0.0
export GREENHOUSE_PORT=5105
export GREENHOUSE_DATA_DIR=~/hosting_apps/data/greenhouse
export GREENHOUSE_DB_PATH=~/hosting_apps/data/greenhouse/greenhouse.db
export GREENHOUSE_DEVICE_DATA_DIR=~/hosting_apps/data/greenhouse/device-readings
export GREENHOUSE_EXPORT_DIR=~/hosting_apps/data/greenhouse/exports
python scripts/run_dev_server.py
```

## 5) Open the homepage

On Ubuntu host:

```text
http://localhost:8080
```

From another device on your network:

```text
http://<ubuntu-ip>:8080
```

Find your Ubuntu LAN IP:

```bash
hostname -I
```

## 6) Add future apps to the homepage

Edit `infra/app_registry.json`, then regenerate the homepage data:

```bash
cd ~/hosting_apps
python3 tools/sync_app_registry.py
```

Then refresh the homepage.

## 7) Troubleshooting

- Port already in use:
  - Change the port, or stop the existing process:
  - `ss -ltnp | grep :5105` (swap port as needed)
- Cannot access from other devices:
  - Confirm server is bound to `0.0.0.0`.
  - Allow firewall ports:
  - `sudo ufw allow 8080`
  - `sudo ufw allow 5102:5105/tcp`
- Homepage loads but app links fail:
  - Confirm each app terminal is still running.
  - Open the app URL directly first (for example `http://<ubuntu-ip>:5105`).
