from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from server.archive import run_weekly_archive
from server.config import load_settings
from server.db import (
    fetch_device_statuses,
    fetch_reading_count,
    initialize_database,
    insert_reading,
)


class ArchiveTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        base_path = Path(self.temp_dir.name)
        os.environ["GREENHOUSE_DB_PATH"] = str(base_path / "archive.db")
        os.environ["GREENHOUSE_DEVICE_DATA_DIR"] = str(base_path / "device-readings")
        os.environ["GREENHOUSE_EXPORT_DIR"] = str(base_path / "exports")
        os.environ["GREENHOUSE_ARCHIVE_TEMP_DIR"] = str(base_path / "pending")
        os.environ["GREENHOUSE_ARCHIVE_SHARE_DIR"] = str(base_path / "share")
        self.settings = load_settings()
        self.settings.ensure_directories()
        initialize_database(self.settings.db_path)
        Path(os.environ["GREENHOUSE_ARCHIVE_SHARE_DIR"]).mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        for key in (
            "GREENHOUSE_DB_PATH",
            "GREENHOUSE_DEVICE_DATA_DIR",
            "GREENHOUSE_EXPORT_DIR",
            "GREENHOUSE_ARCHIVE_TEMP_DIR",
            "GREENHOUSE_ARCHIVE_SHARE_DIR",
        ):
            os.environ.pop(key, None)

    def _seed(self) -> None:
        insert_reading(
            self.settings.db_path,
            {
                "device_id": "greenhouse",
                "mode": "summer",
                "sequence": 1,
                "wifi_rssi_dbm": -61,
                "temperature_c": 25.0,
                "humidity_pct": 61.0,
                "light_lux": 500.0,
            },
        )

    def test_archive_success_copies_and_purges(self) -> None:
        self._seed()
        result = run_weekly_archive(self.settings)
        self.assertEqual(result.status, "success")
        self.assertEqual(fetch_reading_count(self.settings.db_path), 0)
        self.assertGreaterEqual(len(fetch_device_statuses(self.settings.db_path)), 1)
        share_dir = Path(os.environ["GREENHOUSE_ARCHIVE_SHARE_DIR"])
        files = list(share_dir.glob("*.csv"))
        self.assertEqual(len(files), 1)

    def test_archive_failure_keeps_rows(self) -> None:
        self._seed()
        broken_target = Path(self.temp_dir.name) / "not-a-directory"
        broken_target.write_text("block", encoding="utf-8")
        os.environ["GREENHOUSE_ARCHIVE_SHARE_DIR"] = str(broken_target)
        failing_settings = load_settings()
        failing_settings.ensure_directories()
        initialize_database(failing_settings.db_path)

        result = run_weekly_archive(failing_settings)
        self.assertEqual(result.status, "failed")
        self.assertEqual(fetch_reading_count(failing_settings.db_path), 1)


if __name__ == "__main__":
    unittest.main()
