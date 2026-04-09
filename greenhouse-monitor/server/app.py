from __future__ import annotations

import json
import queue
import threading
from datetime import datetime, timezone
from io import BytesIO
from typing import Any
from zoneinfo import ZoneInfo

from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from .archive import run_weekly_archive
from .config import Settings, load_settings
from .db import (
    count_device_log_rows,
    delete_device_data_and_log,
    device_log_path,
    fetch_device_statuses,
    fetch_latest_archive_run,
    fetch_reading_count,
    fetch_recent_history,
    initialize_database,
    insert_reading,
    write_csv_export,
)


REQUIRED_FIELDS = {
    "device_id": str,
    "mode": str,
    "sequence": int,
    "wifi_rssi_dbm": int,
}
OPTIONAL_NUMERIC_FIELDS = {
    "temperature_c": float,
    "humidity_pct": float,
    "light_lux": float,
    "latency_ms": int,
    "uptime_s": int,
}
OPTIONAL_TEXT_FIELDS = {"sent_at_utc": str}
VALID_MODES = {"summer", "range_test", "component_test", "display_only"}


class DashboardEventStream:
    def __init__(self) -> None:
        self._subscribers: set[queue.Queue[str]] = set()
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue[str]:
        subscriber: queue.Queue[str] = queue.Queue(maxsize=8)
        with self._lock:
            self._subscribers.add(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: queue.Queue[str]) -> None:
        with self._lock:
            self._subscribers.discard(subscriber)

    def publish(self, payload: dict[str, Any]) -> None:
        serialized = self._serialize(payload)
        with self._lock:
            subscribers = list(self._subscribers)

        for subscriber in subscribers:
            if subscriber.full():
                try:
                    subscriber.get_nowait()
                except queue.Empty:
                    pass
            try:
                subscriber.put_nowait(serialized)
            except queue.Full:
                continue

    def stream(self, initial_payload: dict[str, Any]):
        subscriber = self.subscribe()
        initial_message = self._serialize(initial_payload)

        def generate():
            try:
                yield "retry: 5000\n"
                yield initial_message
                while True:
                    try:
                        yield subscriber.get(timeout=15)
                    except queue.Empty:
                        yield ": keepalive\n\n"
            finally:
                self.unsubscribe(subscriber)

        return generate()

    @staticmethod
    def _serialize(payload: dict[str, Any]) -> str:
        return "event: dashboard\ndata: %s\n\n" % json.dumps(payload, separators=(",", ":"))


def create_app(settings: Settings | None = None) -> Flask:
    app = Flask(__name__)
    app.config["SETTINGS"] = settings or load_settings()
    dashboard_events = DashboardEventStream()

    current_settings: Settings = app.config["SETTINGS"]
    current_settings.ensure_directories()
    initialize_database(current_settings.db_path)

    @app.get("/health")
    def health() -> Response:
        return jsonify(
            {
                "status": "ok",
                "db_path": str(current_settings.db_path),
                "timestamp_utc": _utc_now_iso(),
            }
        )

    @app.get("/api/v1/latest")
    def latest() -> Response:
        return jsonify(_build_dashboard_payload(current_settings))

    @app.get("/api/v1/stream")
    def stream() -> Response:
        return Response(
            dashboard_events.stream(_build_dashboard_payload(current_settings)),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.post("/api/v1/readings")
    def readings() -> Response:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Request body must be a JSON object."}), 400

        try:
            cleaned_payload = _validate_payload(payload)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        record = insert_reading(
            current_settings.db_path,
            cleaned_payload,
            device_data_dir=current_settings.device_readings_dir,
        )
        dashboard_events.publish(_build_dashboard_payload(current_settings))
        return jsonify({"status": "ok", "reading": record}), 201

    @app.get("/export.csv")
    def export_csv() -> Response:
        temp_path = current_settings.export_dir / "export-current.csv"
        write_csv_export(current_settings.db_path, temp_path)
        buffer = BytesIO(temp_path.read_bytes())
        return send_file(
            buffer,
            mimetype="text/csv",
            as_attachment=True,
            download_name="greenhouse-export.csv",
        )

    @app.get("/devices/<device_id>/history.csv")
    def export_device_csv(device_id: str) -> Response:
        csv_path = device_log_path(current_settings.device_readings_dir, device_id)
        if not csv_path.exists():
            abort(404, description=f"No stored readings for device '{device_id}'.")
        return send_file(
            csv_path,
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"{device_id}-history.csv",
        )

    @app.post("/admin/archive")
    def archive_now() -> Response:
        result = run_weekly_archive(current_settings)
        status_code = 200 if result.status == "success" else 500
        return jsonify(
            {
                "status": result.status,
                "row_count": result.row_count,
                "output_file": result.output_file,
                "message": result.message,
            }
        ), status_code

    @app.post("/admin/devices/<device_id>/delete")
    def delete_device(device_id: str) -> Response:
        if not delete_device_data_and_log(
            current_settings.db_path,
            device_id,
            current_settings.device_readings_dir,
        ):
            return jsonify({"error": f"Unknown device: {device_id}"}), 404
        return redirect(url_for("index"), code=303)

    @app.get("/")
    def index() -> str:
        dashboard = _build_dashboard_payload(current_settings)
        return render_template(
            "index.html",
            generated_at_local=dashboard["generated_at_local"],
            devices=dashboard["devices"],
            deltas=dashboard["deltas"],
            history=dashboard["history"],
            reading_count=dashboard["reading_count"],
            latest_archive=dashboard["latest_archive"],
            device_data_dir=dashboard["device_data_dir"],
        )

    return app


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}

    for field_name, field_type in REQUIRED_FIELDS.items():
        if field_name not in payload:
            raise ValueError(f"Missing required field: {field_name}")
        cleaned[field_name] = _coerce_value(field_name, payload[field_name], field_type)

    if not cleaned["device_id"].strip():
        raise ValueError("device_id cannot be empty.")
    cleaned["device_id"] = cleaned["device_id"].strip()

    if cleaned["mode"] not in VALID_MODES:
        raise ValueError(
            "mode must be 'summer', 'range_test', 'component_test', or 'display_only'."
        )

    for field_name, field_type in OPTIONAL_NUMERIC_FIELDS.items():
        value = payload.get(field_name)
        cleaned[field_name] = (
            None if value is None else _coerce_value(field_name, value, field_type)
        )

    for field_name, field_type in OPTIONAL_TEXT_FIELDS.items():
        value = payload.get(field_name)
        cleaned[field_name] = (
            None if value is None else _coerce_value(field_name, value, field_type)
        )

    return cleaned


def _coerce_value(field_name: str, value: Any, field_type: type) -> Any:
    if field_type is str:
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a string.")
        return value

    if field_type is int:
        if isinstance(value, bool):
            raise ValueError(f"{field_name} must be an integer.")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} must be an integer.") from exc

    if field_type is float:
        if isinstance(value, bool):
            raise ValueError(f"{field_name} must be numeric.")
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} must be numeric.") from exc

    raise ValueError(f"Unsupported field type for {field_name}.")


def _build_status_payload(settings: Settings) -> dict[str, dict[str, Any]]:
    rows = fetch_device_statuses(settings.db_path)
    devices: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = dict(row)
        received_at_utc = item["received_at_utc"]
        age_seconds = _age_seconds(received_at_utc)
        item["received_at_local"] = _format_local(received_at_utc, settings.timezone)
        item["sent_at_local"] = (
            _format_local(item["sent_at_utc"], settings.timezone) if item["sent_at_utc"] else None
        )
        item["age_seconds"] = age_seconds
        item["is_stale"] = age_seconds > settings.stale_minutes * 60
        device_csv_path = device_log_path(settings.device_readings_dir, item["device_id"])
        item["device_csv_name"] = device_csv_path.name
        item["device_csv_path"] = str(device_csv_path)
        item["stored_reading_count"] = count_device_log_rows(
            settings.device_readings_dir, item["device_id"]
        )
        devices[item["device_id"]] = item
    return devices


def _build_dashboard_payload(settings: Settings) -> dict[str, Any]:
    devices = _build_status_payload(settings)
    history = fetch_recent_history(settings.db_path, settings.ui_history_limit)
    latest_archive = fetch_latest_archive_run(settings.db_path)

    for rows in history.values():
        for row in rows:
            row["received_at_local"] = _format_local(row["received_at_utc"], settings.timezone)
            row["sent_at_local"] = _format_local(row["sent_at_utc"], settings.timezone)

    if latest_archive:
        latest_archive["started_at_local"] = _format_local(
            latest_archive["started_at_utc"], settings.timezone
        )
        latest_archive["completed_at_local"] = _format_local(
            latest_archive["completed_at_utc"], settings.timezone
        )

    return {
        "generated_at_utc": _utc_now_iso(),
        "generated_at_local": _format_local(_utc_now_iso(), settings.timezone),
        "devices": devices,
        "deltas": _build_deltas(devices),
        "history": history,
        "reading_count": fetch_reading_count(settings.db_path),
        "latest_archive": latest_archive,
        "device_data_dir": str(settings.device_readings_dir),
    }


def _build_deltas(devices: dict[str, dict[str, Any]]) -> dict[str, float | None]:
    greenhouse = devices.get("greenhouse")
    outdoor = devices.get("outdoor")
    if not greenhouse or not outdoor:
        return {"temperature_c": None, "humidity_pct": None, "light_lux": None}

    return {
        "temperature_c": _delta(greenhouse.get("temperature_c"), outdoor.get("temperature_c")),
        "humidity_pct": _delta(greenhouse.get("humidity_pct"), outdoor.get("humidity_pct")),
        "light_lux": _delta(greenhouse.get("light_lux"), outdoor.get("light_lux")),
    }


def _delta(left: Any, right: Any) -> float | None:
    if left is None or right is None:
        return None
    return round(float(left) - float(right), 2)


def _format_local(timestamp_utc: str | None, timezone_name: str) -> str | None:
    if not timestamp_utc:
        return None
    parsed = datetime.fromisoformat(timestamp_utc)
    local_time = parsed.astimezone(ZoneInfo(timezone_name))
    return local_time.strftime("%Y-%m-%d %H:%M:%S %Z")


def _age_seconds(timestamp_utc: str | None) -> int:
    if not timestamp_utc:
        return 0
    parsed = datetime.fromisoformat(timestamp_utc)
    return int((datetime.now(timezone.utc) - parsed).total_seconds())


def main() -> None:
    settings = load_settings()
    app = create_app(settings)

    try:
        from waitress import serve
    except ImportError:
        app.run(host=settings.host, port=settings.port, debug=False)
        return

    serve(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
