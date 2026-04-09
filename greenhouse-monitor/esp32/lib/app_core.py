import time

try:
    import ntptime
except ImportError:
    ntptime = None

import app_config as config

from display_ui import StatusDisplay
from sensors import SensorSuite
from uploader import Uploader
from wifi_manager import WiFiManager


def _utc_timestamp():
    now = time.gmtime()
    return "%04d-%02d-%02dT%02d:%02d:%02d+00:00" % (
        now[0],
        now[1],
        now[2],
        now[3],
        now[4],
        now[5],
    )


def _interval_seconds():
    if config.RUN_MODE == "range_test":
        return config.RANGE_TEST_INTERVAL_SECONDS
    if config.RUN_MODE == "component_test":
        return getattr(
            config,
            "COMPONENT_TEST_INTERVAL_SECONDS",
            config.RANGE_TEST_INTERVAL_SECONDS,
        )
    if config.RUN_MODE == "display_only":
        return getattr(config, "DISPLAY_REFRESH_SECONDS", 2)
    if not _uploads_enabled():
        return getattr(config, "DISPLAY_REFRESH_SECONDS", config.UPLOAD_INTERVAL_SECONDS)
    return config.UPLOAD_INTERVAL_SECONDS


def _uploads_enabled():
    return getattr(config, "UPLOAD_ENABLED", True)


def _pending_upload_limit():
    return max(1, int(getattr(config, "MAX_PENDING_UPLOADS", 8)))


def _queue_payload(pending_uploads, payload):
    pending_uploads.append(payload)
    overflow = len(pending_uploads) - _pending_upload_limit()
    if overflow > 0:
        del pending_uploads[:overflow]


def _flush_pending_uploads(uploader, pending_uploads):
    delivered = 0
    last_status_code = 0
    last_latency_ms = None
    response_text = ""

    while pending_uploads:
        success, status_code, latency_ms, response_text = uploader.send(pending_uploads[0])
        last_status_code = status_code
        last_latency_ms = latency_ms
        if not success:
            return delivered, last_status_code, last_latency_ms, response_text
        pending_uploads.pop(0)
        delivered += 1

    return delivered, last_status_code, last_latency_ms, response_text


def _blank(value):
    return not value or not str(value).strip()


def _targets_localhost(url):
    candidate = str(url).lower()
    return (
        "://localhost" in candidate
        or "://127.0.0.1" in candidate
        or "://0.0.0.0" in candidate
    )


def _server_url():
    if config.RUN_MODE == "component_test":
        temp_server_url = getattr(config, "TEMP_WINDOWS_SERVER_URL", None)
        if temp_server_url and str(temp_server_url).strip():
            return temp_server_url
    return config.SERVER_URL


def _upload_preflight_error():
    if not _uploads_enabled():
        return None

    server_url = _server_url()
    if _blank(server_url):
        return "URL MISSING"
    if not str(server_url).startswith("http://"):
        return "URL INVALID"
    if _targets_localhost(server_url):
        return "USE PC LAN IP"

    ssid = getattr(config, "WIFI_SSID", "")
    if _blank(ssid) or ssid == "YOUR_WIFI_SSID":
        return "WIFI CONFIG"

    password = getattr(config, "WIFI_PASSWORD", "")
    if password == "YOUR_WIFI_PASSWORD":
        return "WIFI CONFIG"

    return None


def _sync_clock():
    if ntptime is None:
        return False
    try:
        ntptime.settime()
        return True
    except Exception:
        return False


def run_device():
    upload_error = _upload_preflight_error()
    uploads_enabled = _uploads_enabled() and upload_error is None
    wifi = None
    uploader = None
    clock_sync_pending = True
    if uploads_enabled:
        wifi = WiFiManager(
            config.WIFI_SSID,
            config.WIFI_PASSWORD,
            timeout_s=config.WIFI_TIMEOUT_SECONDS,
        )
        uploader = Uploader(_server_url(), timeout_s=config.HTTP_TIMEOUT_SECONDS)
    elif upload_error:
        print("Uploads disabled: %s" % upload_error)
    sensors = SensorSuite(config)
    print("I2C scan=%s" % sensors.format_i2c_addresses())
    display = None
    if config.OLED_ENABLED:
        if config.OLED_ADDR in sensors.i2c_addresses:
            try:
                display = StatusDisplay(sensors.i2c, config)
            except Exception:
                sensors.init_errors.append("OLED OFFLINE")
        else:
            sensors.init_errors.append("OLED OFFLINE")

    interval_seconds = _interval_seconds()
    boot_ms = time.ticks_ms()
    sequence = 0
    last_latency_ms = None
    pending_uploads = []

    if display:
        display.render({"temperature_c": None, "humidity_pct": None, "light_lux": None}, "BOOT")

    while True:
        cycle_started_ms = time.ticks_ms()
        readings = sensors.read_all()
        footer = upload_error or "DISPLAY ONLY"
        if readings["errors"]:
            footer = readings["errors"][0][:21]
        if display:
            display.render(readings, footer)
        wifi_ok = False
        rssi = None
        sent_at_utc = None
        sequence += 1

        if wifi is not None:
            wifi_ok = wifi.ensure_connected()
            rssi = wifi.rssi()
            if wifi_ok:
                sent_at_utc = _utc_timestamp()
                if clock_sync_pending:
                    _sync_clock()
                    clock_sync_pending = False

        payload = {
            "device_id": config.DEVICE_ID,
            "mode": config.RUN_MODE,
            "sequence": sequence,
            "wifi_rssi_dbm": rssi if rssi is not None else -127,
            "temperature_c": readings["temperature_c"],
            "humidity_pct": readings["humidity_pct"],
            "light_lux": readings["light_lux"],
            "sent_at_utc": sent_at_utc,
            "latency_ms": last_latency_ms,
            "uptime_s": time.ticks_diff(time.ticks_ms(), boot_ms) // 1000,
        }

        if uploader:
            _queue_payload(pending_uploads, payload)

        if uploader and wifi_ok:
            try:
                delivered, status_code, latency_ms, _response_text = _flush_pending_uploads(
                    uploader, pending_uploads
                )
                if latency_ms is not None:
                    last_latency_ms = latency_ms

                if delivered > 0 and latency_ms is not None:
                    if delivered == 1:
                        footer = "POST OK %dms" % latency_ms
                    else:
                        footer = "SYNC %d OK" % delivered
                elif delivered > 0:
                    footer = "POST OK"
                else:
                    footer = "HTTP %d" % status_code
            except Exception as exc:
                footer = "UPLOAD ERROR"
                print("Upload failed:", exc)
        elif uploader:
            footer = "WIFI DOWN Q%d" % len(pending_uploads)

        if readings["errors"]:
            footer = readings["errors"][0][:21]

        print(
            "mode=%s seq=%d wifi=%s temp=%s hum=%s light=%s pending=%d status=%s"
            % (
                config.RUN_MODE,
                sequence,
                payload["wifi_rssi_dbm"],
                readings["temperature_c"],
                readings["humidity_pct"],
                readings["light_lux"],
                len(pending_uploads),
                footer,
            )
        )

        if display:
            display.render(readings, footer)

        elapsed_ms = time.ticks_diff(time.ticks_ms(), cycle_started_ms)
        remaining_ms = max(0, interval_seconds * 1000 - elapsed_ms)
        while remaining_ms > 0:
            sleep_ms = 250 if remaining_ms > 250 else remaining_ms
            time.sleep_ms(sleep_ms)
            remaining_ms -= sleep_ms
