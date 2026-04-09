from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "infra" / "app_registry.json"
APPS_JSON_PATH = ROOT / "home-page" / "apps.json"
COMPOSE_PATH = ROOT / "compose.yaml"
DOCKERFILE_PATH = "docker/python-service.Dockerfile"


def load_registry() -> dict:
    with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        registry = json.load(handle)

    if not registry.get("apps"):
        raise ValueError("Registry must define at least one app.")

    slugs = set()
    service_names = set()
    ports = set()
    for app in registry["apps"]:
        slug = app["slug"]
        service_name = app["service_name"]
        port = int(app["port"])
        source_path = ROOT / app["source_path"]

        if slug in slugs:
            raise ValueError(f"Duplicate app slug: {slug}")
        if service_name in service_names:
            raise ValueError(f"Duplicate service name: {service_name}")
        if port in ports:
            raise ValueError(f"Duplicate port: {port}")
        if not source_path.exists():
            raise ValueError(f"Missing app path: {app['source_path']}")

        slugs.add(slug)
        service_names.add(service_name)
        ports.add(port)

    return registry


def quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def render_compose(registry: dict) -> str:
    lines = [
        "# Generated from infra/app_registry.json by tools/sync_app_registry.py",
        "services:",
        "  home-page:",
        "    image: nginx:1.27-alpine",
        "    ports:",
        '      - "8080:80"',
        "    volumes:",
        '      - "./home-page:/usr/share/nginx/html:ro"',
        "    restart: unless-stopped",
    ]

    for app in registry["apps"]:
        install = app["build"]["install"]
        run = app["run"]
        port = int(app["port"])

        lines.extend(
            [
                f"  {app['service_name']}:",
                "    build:",
                "      context: .",
                f"      dockerfile: {DOCKERFILE_PATH}",
                "      args:",
                f"        APP_DIR: {app['source_path']}",
                f"        INSTALL_METHOD: {install['type']}",
                f"        INSTALL_TARGET: {install['target']}",
                f"    working_dir: /workspace/{app['source_path']}",
                f"    command: {quote(run['command'])}",
                "    environment:",
            ]
        )

        for key, value in run.get("environment", {}).items():
            lines.append(f"      {key}: {quote(str(value))}")

        lines.extend(
            [
                "    ports:",
                f'      - "{port}:{port}"',
            ]
        )

        volumes = run.get("volumes", [])
        if volumes:
            lines.append("    volumes:")
            for volume in volumes:
                mount = f"{volume['source']}:{volume['target']}"
                lines.append(f"      - {quote(mount)}")

        lines.append("    restart: unless-stopped")

    lines.append("")
    return "\n".join(lines)


def render_homepage_data(registry: dict) -> str:
    visible_apps = [app for app in registry["apps"] if app.get("show_on_homepage", True)]
    payload = {
        "hub": registry["hub"],
        "apps": [
            {
                "name": app["display_name"],
                "slug": app["slug"],
                "tag": app["tag"],
                "description": app["description"],
                "port": int(app["port"]),
                "buttonVariant": app.get("button_variant", "primary"),
                "publicSubdomain": app.get("public_subdomain"),
            }
            for app in visible_apps
        ],
    }
    return json.dumps(payload, indent=2) + "\n"


def main() -> None:
    registry = load_registry()
    COMPOSE_PATH.write_text(render_compose(registry), encoding="utf-8")
    APPS_JSON_PATH.write_text(render_homepage_data(registry), encoding="utf-8")


if __name__ == "__main__":
    main()
