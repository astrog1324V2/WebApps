from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    data_dir: Path
    db_path: Path
    device_readings_dir: Path
    export_dir: Path
    archive_share_dir: Path | None
    timezone: str
    stale_minutes: int
    ui_history_limit: int
    archive_filename_prefix: str
    archive_temp_dir: Path
    keep_local_archive_copy: bool

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.device_readings_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.archive_temp_dir.mkdir(parents=True, exist_ok=True)


def _optional_path(value: str | None) -> Path | None:
    if not value:
        return None
    return Path(value).expanduser()


def load_settings() -> Settings:
    data_dir = Path(os.getenv("GREENHOUSE_DATA_DIR", PROJECT_ROOT / "data")).expanduser()
    db_path = Path(os.getenv("GREENHOUSE_DB_PATH", data_dir / "greenhouse.db")).expanduser()
    device_readings_dir = Path(
        os.getenv("GREENHOUSE_DEVICE_DATA_DIR", data_dir / "device-readings")
    ).expanduser()
    export_dir = Path(os.getenv("GREENHOUSE_EXPORT_DIR", data_dir / "exports")).expanduser()
    archive_temp_dir = Path(
        os.getenv("GREENHOUSE_ARCHIVE_TEMP_DIR", export_dir / "pending")
    ).expanduser()

    return Settings(
        host=os.getenv("GREENHOUSE_HOST", "0.0.0.0"),
        port=int(os.getenv("GREENHOUSE_PORT", "8000")),
        data_dir=data_dir,
        db_path=db_path,
        device_readings_dir=device_readings_dir,
        export_dir=export_dir,
        archive_share_dir=_optional_path(os.getenv("GREENHOUSE_ARCHIVE_SHARE_DIR")),
        timezone=os.getenv("GREENHOUSE_TIMEZONE", "America/Toronto"),
        stale_minutes=int(os.getenv("GREENHOUSE_STALE_MINUTES", "3")),
        ui_history_limit=int(os.getenv("GREENHOUSE_UI_HISTORY_LIMIT", "10")),
        archive_filename_prefix=os.getenv("GREENHOUSE_ARCHIVE_PREFIX", "greenhouse-weekly"),
        archive_temp_dir=archive_temp_dir,
        keep_local_archive_copy=os.getenv("GREENHOUSE_KEEP_LOCAL_ARCHIVE_COPY", "0") == "1",
    )
