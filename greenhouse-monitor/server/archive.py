from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import Settings
from .db import begin_archive_run, finish_archive_run, purge_readings, write_csv_export


@dataclass
class ArchiveResult:
    status: str
    row_count: int
    output_file: str | None
    message: str


def _archive_filename(settings: Settings, now_utc: datetime) -> str:
    local_now = now_utc.astimezone(ZoneInfo(settings.timezone))
    return f"{settings.archive_filename_prefix}-{local_now:%Y-%m-%d_%H-%M-%S}.csv"


def run_weekly_archive(settings: Settings) -> ArchiveResult:
    settings.ensure_directories()
    started_at_utc = datetime.now(timezone.utc).replace(microsecond=0)
    archive_run_id = begin_archive_run(settings.db_path, started_at_utc.isoformat())

    filename = _archive_filename(settings, started_at_utc)
    temp_output = settings.archive_temp_dir / filename

    try:
        row_count = write_csv_export(settings.db_path, temp_output)
        if settings.archive_share_dir is None:
            raise RuntimeError("GREENHOUSE_ARCHIVE_SHARE_DIR is not configured.")
        if not settings.archive_share_dir.exists():
            raise RuntimeError(f"Archive share is not available: {settings.archive_share_dir}")
        if not settings.archive_share_dir.is_dir():
            raise RuntimeError(f"Archive share path is not a directory: {settings.archive_share_dir}")

        remote_output = settings.archive_share_dir / filename
        shutil.copy2(temp_output, remote_output)

        if not remote_output.exists():
            raise RuntimeError(f"Archive copy missing at {remote_output}.")
        if remote_output.stat().st_size != temp_output.stat().st_size:
            raise RuntimeError("Archive copy size mismatch.")

        purge_readings(settings.db_path)

        if not settings.keep_local_archive_copy and temp_output.exists():
            temp_output.unlink()

        result = ArchiveResult(
            status="success",
            row_count=row_count,
            output_file=str(remote_output),
            message=f"Archived {row_count} reading(s) to {remote_output}.",
        )
        finish_archive_run(
            settings.db_path,
            archive_run_id,
            status=result.status,
            output_file=result.output_file,
            row_count=result.row_count,
            message=result.message,
        )
        return result
    except Exception as exc:
        result = ArchiveResult(
            status="failed",
            row_count=0,
            output_file=None,
            message=str(exc),
        )
        finish_archive_run(
            settings.db_path,
            archive_run_id,
            status=result.status,
            output_file=result.output_file,
            row_count=result.row_count,
            message=result.message,
        )
        return result
