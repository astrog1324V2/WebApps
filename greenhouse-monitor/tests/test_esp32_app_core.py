from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


APP_CORE_PATH = (
    Path(__file__).resolve().parents[1] / "esp32" / "lib" / "app_core.py"
)


class AppCoreConfigTestCase(unittest.TestCase):
    def _load_module(self, config_values: dict[str, object]):
        fake_config = types.ModuleType("app_config")
        for name, value in config_values.items():
            setattr(fake_config, name, value)

        fake_display_ui = types.ModuleType("display_ui")
        fake_display_ui.StatusDisplay = object

        fake_sensors = types.ModuleType("sensors")
        fake_sensors.SensorSuite = object

        fake_uploader = types.ModuleType("uploader")
        fake_uploader.Uploader = object

        fake_wifi_manager = types.ModuleType("wifi_manager")
        fake_wifi_manager.WiFiManager = object

        fake_ntptime = types.ModuleType("ntptime")
        fake_ntptime.settime = lambda: True

        module_name = "test_app_core_%s" % len(self._cleanups)
        spec = importlib.util.spec_from_file_location(module_name, APP_CORE_PATH)
        module = importlib.util.module_from_spec(spec)

        originals = {
            "app_config": sys.modules.get("app_config"),
            "display_ui": sys.modules.get("display_ui"),
            "sensors": sys.modules.get("sensors"),
            "uploader": sys.modules.get("uploader"),
            "wifi_manager": sys.modules.get("wifi_manager"),
            "ntptime": sys.modules.get("ntptime"),
            module_name: sys.modules.get(module_name),
        }

        sys.modules["app_config"] = fake_config
        sys.modules["display_ui"] = fake_display_ui
        sys.modules["sensors"] = fake_sensors
        sys.modules["uploader"] = fake_uploader
        sys.modules["wifi_manager"] = fake_wifi_manager
        sys.modules["ntptime"] = fake_ntptime
        sys.modules[module_name] = module

        def cleanup():
            for name, original in originals.items():
                if original is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = original

        self.addCleanup(cleanup)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return module

    def test_component_mode_uses_temp_server_url(self) -> None:
        module = self._load_module(
            {
                "RUN_MODE": "component_test",
                "UPLOAD_ENABLED": True,
                "TEMP_WINDOWS_SERVER_URL": "http://10.0.0.15:5105/api/v1/readings",
                "SERVER_URL": "http://192.168.1.50:5105/api/v1/readings",
                "WIFI_SSID": "lab-wifi",
                "WIFI_PASSWORD": "secret",
            }
        )

        self.assertEqual(
            module._server_url(),
            "http://10.0.0.15:5105/api/v1/readings",
        )
        self.assertIsNone(module._upload_preflight_error())

    def test_component_mode_falls_back_to_server_url_when_temp_is_blank(self) -> None:
        module = self._load_module(
            {
                "RUN_MODE": "component_test",
                "UPLOAD_ENABLED": True,
                "TEMP_WINDOWS_SERVER_URL": None,
                "SERVER_URL": "http://192.168.1.50:5105/api/v1/readings",
                "WIFI_SSID": "lab-wifi",
                "WIFI_PASSWORD": "secret",
            }
        )

        self.assertEqual(
            module._server_url(),
            "http://192.168.1.50:5105/api/v1/readings",
        )
        self.assertIsNone(module._upload_preflight_error())

    def test_component_mode_requires_http_upload_url(self) -> None:
        module = self._load_module(
            {
                "RUN_MODE": "component_test",
                "UPLOAD_ENABLED": True,
                "TEMP_WINDOWS_SERVER_URL": "https://10.0.0.15:5105/api/v1/readings",
                "SERVER_URL": "http://192.168.1.50:5105/api/v1/readings",
                "WIFI_SSID": "lab-wifi",
                "WIFI_PASSWORD": "secret",
            }
        )

        self.assertEqual(module._upload_preflight_error(), "URL INVALID")

    def test_upload_url_must_not_use_localhost(self) -> None:
        module = self._load_module(
            {
                "RUN_MODE": "summer",
                "UPLOAD_ENABLED": True,
                "SERVER_URL": "http://localhost:5105/api/v1/readings",
                "WIFI_SSID": "lab-wifi",
                "WIFI_PASSWORD": "secret",
            }
        )

        self.assertEqual(module._upload_preflight_error(), "USE PC LAN IP")

    def test_component_mode_requires_real_wifi_config(self) -> None:
        module = self._load_module(
            {
                "RUN_MODE": "component_test",
                "UPLOAD_ENABLED": True,
                "TEMP_WINDOWS_SERVER_URL": "http://10.0.0.15:5105/api/v1/readings",
                "SERVER_URL": "http://192.168.1.50:5105/api/v1/readings",
                "WIFI_SSID": "YOUR_WIFI_SSID",
                "WIFI_PASSWORD": "YOUR_WIFI_PASSWORD",
            }
        )

        self.assertEqual(module._upload_preflight_error(), "WIFI CONFIG")

    def test_queue_payload_trims_oldest_entries(self) -> None:
        module = self._load_module(
            {
                "RUN_MODE": "summer",
                "UPLOAD_ENABLED": True,
                "SERVER_URL": "http://192.168.1.50:5105/api/v1/readings",
                "WIFI_SSID": "lab-wifi",
                "WIFI_PASSWORD": "secret",
                "MAX_PENDING_UPLOADS": 2,
            }
        )

        pending = []
        module._queue_payload(pending, {"sequence": 1})
        module._queue_payload(pending, {"sequence": 2})
        module._queue_payload(pending, {"sequence": 3})

        self.assertEqual(pending, [{"sequence": 2}, {"sequence": 3}])

    def test_flush_pending_uploads_stops_after_first_failure(self) -> None:
        module = self._load_module(
            {
                "RUN_MODE": "summer",
                "UPLOAD_ENABLED": True,
                "SERVER_URL": "http://192.168.1.50:5105/api/v1/readings",
                "WIFI_SSID": "lab-wifi",
                "WIFI_PASSWORD": "secret",
            }
        )

        class FakeUploader:
            def __init__(self):
                self.calls = 0

            def send(self, payload):
                self.calls += 1
                if self.calls == 1:
                    return True, 201, 120, "ok"
                return False, 503, 180, "down"

        pending = [{"sequence": 1}, {"sequence": 2}, {"sequence": 3}]
        uploader = FakeUploader()

        delivered, status_code, latency_ms, response_text = module._flush_pending_uploads(
            uploader, pending
        )

        self.assertEqual(delivered, 1)
        self.assertEqual(status_code, 503)
        self.assertEqual(latency_ms, 180)
        self.assertEqual(response_text, "down")
        self.assertEqual(pending, [{"sequence": 2}, {"sequence": 3}])


if __name__ == "__main__":
    unittest.main()
