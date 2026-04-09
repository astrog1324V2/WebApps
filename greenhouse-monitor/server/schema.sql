PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    mode TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    wifi_rssi_dbm INTEGER NOT NULL,
    temperature_c REAL,
    humidity_pct REAL,
    light_lux REAL,
    sent_at_utc TEXT,
    latency_ms INTEGER,
    uptime_s INTEGER,
    received_at_utc TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_readings_device_time
    ON readings (device_id, received_at_utc DESC);

CREATE TABLE IF NOT EXISTS device_status (
    device_id TEXT PRIMARY KEY,
    mode TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    wifi_rssi_dbm INTEGER NOT NULL,
    temperature_c REAL,
    humidity_pct REAL,
    light_lux REAL,
    sent_at_utc TEXT,
    latency_ms INTEGER,
    uptime_s INTEGER,
    received_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS archive_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at_utc TEXT NOT NULL,
    completed_at_utc TEXT,
    output_file TEXT,
    status TEXT NOT NULL,
    row_count INTEGER NOT NULL DEFAULT 0,
    message TEXT
);
