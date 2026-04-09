from __future__ import annotations

import csv
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


READING_COLUMNS = (
    "device_id",
    "mode",
    "sequence",
    "wifi_rssi_dbm",
    "temperature_c",
    "humidity_pct",
    "light_lux",
    "sent_at_utc",
    "latency_ms",
    "uptime_s",
    "received_at_utc",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_connection(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path, timeout=30.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection


def initialize_database(db_path: Path) -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    schema = schema_path.read_text(encoding="utf-8")
    with closing(get_connection(db_path)) as connection:
        connection.executescript(schema)
        connection.commit()


def device_log_path(device_data_dir: Path, device_id: str) -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "-", device_id.strip()).strip("-") or "device"
    return device_data_dir / f"{safe_name}.csv"


def _append_device_log(device_data_dir: Path, record: dict[str, Any]) -> Path:
    device_data_dir.mkdir(parents=True, exist_ok=True)
    output_path = device_log_path(device_data_dir, record["device_id"])
    write_header = not output_path.exists()

    with output_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(READING_COLUMNS))
        if write_header:
            writer.writeheader()
        writer.writerow({column: record[column] for column in READING_COLUMNS})

    return output_path


def count_device_log_rows(device_data_dir: Path, device_id: str) -> int:
    output_path = device_log_path(device_data_dir, device_id)
    if not output_path.exists():
        return 0

    with output_path.open("r", newline="", encoding="utf-8") as handle:
        row_count = sum(1 for _ in handle) - 1
    return max(row_count, 0)


def delete_device_log(device_data_dir: Path, device_id: str) -> None:
    output_path = device_log_path(device_data_dir, device_id)
    if output_path.exists():
        output_path.unlink()


def insert_reading(
    db_path: Path,
    payload: dict[str, Any],
    *,
    device_data_dir: Path | None = None,
) -> dict[str, Any]:
    received_at_utc = utc_now_iso()
    record = {
        "device_id": payload["device_id"],
        "mode": payload["mode"],
        "sequence": payload["sequence"],
        "wifi_rssi_dbm": payload["wifi_rssi_dbm"],
        "temperature_c": payload.get("temperature_c"),
        "humidity_pct": payload.get("humidity_pct"),
        "light_lux": payload.get("light_lux"),
        "sent_at_utc": payload.get("sent_at_utc"),
        "latency_ms": payload.get("latency_ms"),
        "uptime_s": payload.get("uptime_s"),
        "received_at_utc": received_at_utc,
    }
    values = [record[column] for column in READING_COLUMNS]

    with closing(get_connection(db_path)) as connection:
        connection.execute(
            """
            INSERT INTO readings (
                device_id, mode, sequence, wifi_rssi_dbm, temperature_c,
                humidity_pct, light_lux, sent_at_utc, latency_ms, uptime_s, received_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        connection.execute(
            """
            INSERT INTO device_status (
                device_id, mode, sequence, wifi_rssi_dbm, temperature_c,
                humidity_pct, light_lux, sent_at_utc, latency_ms, uptime_s, received_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                mode = excluded.mode,
                sequence = excluded.sequence,
                wifi_rssi_dbm = excluded.wifi_rssi_dbm,
                temperature_c = excluded.temperature_c,
                humidity_pct = excluded.humidity_pct,
                light_lux = excluded.light_lux,
                sent_at_utc = excluded.sent_at_utc,
                latency_ms = excluded.latency_ms,
                uptime_s = excluded.uptime_s,
                received_at_utc = excluded.received_at_utc
            """,
            values,
        )
        connection.commit()

    if device_data_dir is not None:
        _append_device_log(device_data_dir, record)

    return record


def fetch_device_statuses(db_path: Path) -> list[dict[str, Any]]:
    with closing(get_connection(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT device_id, mode, sequence, wifi_rssi_dbm, temperature_c,
                   humidity_pct, light_lux, sent_at_utc, latency_ms, uptime_s, received_at_utc
            FROM device_status
            ORDER BY device_id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def fetch_recent_history(db_path: Path, limit_per_device: int) -> dict[str, list[dict[str, Any]]]:
    devices = [row["device_id"] for row in fetch_device_statuses(db_path)]
    history: dict[str, list[dict[str, Any]]] = {}
    with closing(get_connection(db_path)) as connection:
        for device_id in devices:
            rows = connection.execute(
                """
                SELECT device_id, mode, sequence, wifi_rssi_dbm, temperature_c,
                       humidity_pct, light_lux, sent_at_utc, latency_ms, uptime_s, received_at_utc
                FROM readings
                WHERE device_id = ?
                ORDER BY received_at_utc DESC
                LIMIT ?
                """,
                (device_id, limit_per_device),
            ).fetchall()
            history[device_id] = [dict(row) for row in rows]
    return history


def fetch_reading_count(db_path: Path) -> int:
    with closing(get_connection(db_path)) as connection:
        row = connection.execute("SELECT COUNT(*) AS count FROM readings").fetchone()
    return int(row["count"])


def delete_device_data(db_path: Path, device_id: str) -> bool:
    with closing(get_connection(db_path)) as connection:
        status_deleted = connection.execute(
            "DELETE FROM device_status WHERE device_id = ?",
            (device_id,),
        ).rowcount
        readings_deleted = connection.execute(
            "DELETE FROM readings WHERE device_id = ?",
            (device_id,),
        ).rowcount
        connection.commit()
    return bool(status_deleted or readings_deleted)


def delete_device_data_and_log(db_path: Path, device_id: str, device_data_dir: Path) -> bool:
    deleted = delete_device_data(db_path, device_id)
    delete_device_log(device_data_dir, device_id)
    return deleted


def fetch_latest_archive_run(db_path: Path) -> dict[str, Any] | None:
    with closing(get_connection(db_path)) as connection:
        row = connection.execute(
            """
            SELECT id, started_at_utc, completed_at_utc, output_file, status, row_count, message
            FROM archive_runs
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    return dict(row) if row else None


def write_csv_export(db_path: Path, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(get_connection(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT device_id, mode, sequence, wifi_rssi_dbm, temperature_c,
                   humidity_pct, light_lux, sent_at_utc, latency_ms, uptime_s, received_at_utc
            FROM readings
            ORDER BY received_at_utc ASC
            """
        ).fetchall()

    fieldnames = list(READING_COLUMNS)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
    return len(rows)


def begin_archive_run(db_path: Path, started_at_utc: str) -> int:
    with closing(get_connection(db_path)) as connection:
        cursor = connection.execute(
            """
            INSERT INTO archive_runs (started_at_utc, status)
            VALUES (?, ?)
            """,
            (started_at_utc, "running"),
        )
        archive_id = cursor.lastrowid
        connection.commit()
    return int(archive_id)


def finish_archive_run(
    db_path: Path,
    archive_run_id: int,
    *,
    status: str,
    output_file: str | None,
    row_count: int,
    message: str | None,
) -> None:
    with closing(get_connection(db_path)) as connection:
        connection.execute(
            """
            UPDATE archive_runs
            SET completed_at_utc = ?, output_file = ?, status = ?, row_count = ?, message = ?
            WHERE id = ?
            """,
            (utc_now_iso(), output_file, status, row_count, message, archive_run_id),
        )
        connection.commit()


def purge_readings(db_path: Path) -> None:
    with closing(get_connection(db_path)) as connection:
        connection.execute("DELETE FROM readings")
        connection.commit()
        connection.execute("VACUUM")
