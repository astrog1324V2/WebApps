from __future__ import annotations

import csv
import os
import tempfile
import unittest
from pathlib import Path

from server.app import create_app
from server.config import load_settings


class AppTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        base_path = Path(self.temp_dir.name)
        os.environ["GREENHOUSE_DB_PATH"] = str(base_path / "test.db")
        os.environ["GREENHOUSE_DEVICE_DATA_DIR"] = str(base_path / "device-readings")
        os.environ["GREENHOUSE_EXPORT_DIR"] = str(base_path / "exports")
        os.environ["GREENHOUSE_ARCHIVE_TEMP_DIR"] = str(base_path / "pending")
        os.environ["GREENHOUSE_ARCHIVE_SHARE_DIR"] = str(base_path / "share")
        os.environ["GREENHOUSE_TIMEZONE"] = "America/Toronto"
        self.app = create_app(load_settings())
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        for key in (
            "GREENHOUSE_DB_PATH",
            "GREENHOUSE_DEVICE_DATA_DIR",
            "GREENHOUSE_EXPORT_DIR",
            "GREENHOUSE_ARCHIVE_TEMP_DIR",
            "GREENHOUSE_ARCHIVE_SHARE_DIR",
            "GREENHOUSE_TIMEZONE",
        ):
            os.environ.pop(key, None)

    def test_post_reading_and_fetch_latest(self) -> None:
        payload = {
            "device_id": "greenhouse",
            "mode": "summer",
            "sequence": 10,
            "wifi_rssi_dbm": -62,
            "temperature_c": 24.5,
            "humidity_pct": 66.1,
            "light_lux": 348.0,
        }
        response = self.client.post("/api/v1/readings", json=payload)
        self.assertEqual(response.status_code, 201)

        latest_response = self.client.get("/api/v1/latest")
        self.assertEqual(latest_response.status_code, 200)
        latest = latest_response.get_json()
        self.assertIn("greenhouse", latest["devices"])
        self.assertEqual(latest["devices"]["greenhouse"]["sequence"], 10)
        self.assertEqual(latest["devices"]["greenhouse"]["stored_reading_count"], 1)
        self.assertIn("history", latest)
        self.assertIn("greenhouse", latest["history"])

    def test_stream_emits_dashboard_event(self) -> None:
        self.client.post(
            "/api/v1/readings",
            json={
                "device_id": "greenhouse",
                "mode": "summer",
                "sequence": 1,
                "wifi_rssi_dbm": -61,
                "temperature_c": 24.0,
                "humidity_pct": 60.0,
                "light_lux": 300.0,
            },
        )

        response = self.client.get("/api/v1/stream", buffered=False)
        first_chunk = next(response.response).decode("utf-8")
        second_chunk = next(response.response).decode("utf-8")
        response.close()

        self.assertIn("retry: 5000", first_chunk)
        self.assertIn("event: dashboard", second_chunk)
        self.assertIn('"reading_count":1', second_chunk)

    def test_export_csv_contains_rows(self) -> None:
        for device_id in ("greenhouse", "outdoor"):
            self.client.post(
                "/api/v1/readings",
                json={
                    "device_id": device_id,
                    "mode": "summer",
                    "sequence": 1,
                    "wifi_rssi_dbm": -70,
                    "temperature_c": 20.0,
                    "humidity_pct": 50.0,
                    "light_lux": 120.0,
                },
            )

        response = self.client.get("/export.csv")
        self.assertEqual(response.status_code, 200)
        rows = list(csv.DictReader(response.data.decode("utf-8").splitlines()))
        self.assertEqual(len(rows), 2)

    def test_device_specific_csv_is_written_and_downloadable(self) -> None:
        self.client.post(
            "/api/v1/readings",
            json={
                "device_id": "outdoor",
                "mode": "summer",
                "sequence": 4,
                "wifi_rssi_dbm": -69,
                "temperature_c": 14.0,
                "humidity_pct": 82.0,
                "light_lux": 910.0,
            },
        )

        latest = self.client.get("/api/v1/latest").get_json()
        self.assertEqual(latest["devices"]["outdoor"]["device_csv_name"], "outdoor.csv")

        response = self.client.get("/devices/outdoor/history.csv")
        self.assertEqual(response.status_code, 200)
        rows = list(csv.DictReader(response.data.decode("utf-8").splitlines()))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["device_id"], "outdoor")
        response.close()

    def test_component_test_mode_is_accepted(self) -> None:
        response = self.client.post(
            "/api/v1/readings",
            json={
                "device_id": "greenhouse",
                "mode": "component_test",
                "sequence": 2,
                "wifi_rssi_dbm": -58,
                "temperature_c": 23.0,
                "humidity_pct": 52.0,
                "light_lux": 210.0,
            },
        )
        self.assertEqual(response.status_code, 201)

    def test_display_only_mode_is_accepted(self) -> None:
        response = self.client.post(
            "/api/v1/readings",
            json={
                "device_id": "portable_demo",
                "mode": "display_only",
                "sequence": 3,
                "wifi_rssi_dbm": -127,
                "temperature_c": 21.5,
                "humidity_pct": 47.0,
                "light_lux": 180.0,
            },
        )
        self.assertEqual(response.status_code, 201)

    def test_index_page_renders(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Current conditions", response.data.decode("utf-8"))

    def test_delete_device_removes_status_and_history(self) -> None:
        for sequence in (1, 2):
            self.client.post(
                "/api/v1/readings",
                json={
                    "device_id": "retired_node",
                    "mode": "summer",
                    "sequence": sequence,
                    "wifi_rssi_dbm": -71,
                    "temperature_c": 19.5,
                    "humidity_pct": 48.0,
                    "light_lux": 90.0,
                },
            )

        response = self.client.post("/admin/devices/retired_node/delete")
        self.assertEqual(response.status_code, 303)

        latest = self.client.get("/api/v1/latest").get_json()
        self.assertNotIn("retired_node", latest["devices"])
        self.assertEqual(latest["reading_count"], 0)
        self.assertEqual(
            self.client.get("/devices/retired_node/history.csv").status_code,
            404,
        )

        index_response = self.client.get("/")
        self.assertNotIn("Retired Node", index_response.data.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
