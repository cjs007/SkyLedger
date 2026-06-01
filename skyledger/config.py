from __future__ import annotations

import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_PATHS = (
    "config.yaml",
    "/etc/skyledger/config.yaml",
)


@dataclass(slots=True)
class AppConfig:
    home_lat: float = 0.0
    home_lon: float = 0.0
    home_name: str = "SkyLedger"
    adsb_json_path: str = "/run/readsb/aircraft.json"
    discord_webhook_url: str = ""
    dashboard_port: int = 8000
    alert_radius_miles: float = 0.5
    guess_trigger_radius_miles: float = 1.2
    reveal_radius_miles: float = 0.5
    tracking_radius_miles: float = 3.0
    max_alert_altitude_ft: int = 10000
    countdown_seconds: int = 10
    reveal_duration_seconds: int = 25
    alert_cooldown_minutes: int = 10
    raw_position_retention_days: int = 14
    enable_discord_alerts: bool = False
    enable_enrichment: bool = False
    dashboard_title: str = "SkyLedger"
    database_path: str = "skyledger.db"
    tar1090_url: str = "http://localhost/tar1090/"
    poll_interval_seconds: float = 2.0

    def public_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["discord_webhook_url"] = "configured" if self.discord_webhook_url else ""
        return data


def load_config(path: str | None = None) -> AppConfig:
    config_path = _resolve_config_path(path)
    raw: dict[str, Any] = {}
    if config_path and config_path.exists():
        with config_path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
            if not isinstance(loaded, dict):
                raise ValueError(f"Config file must contain a YAML mapping: {config_path}")
            raw = loaded

    allowed = {field.name: field for field in fields(AppConfig)}
    unknown = set(raw) - set(allowed)
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"Unknown config field(s): {names}")

    values: dict[str, Any] = {}
    for name, field in allowed.items():
        if name in raw:
            values[name] = _coerce(raw[name], field.type)

    return AppConfig(**values)


def _resolve_config_path(path: str | None) -> Path | None:
    explicit = path or os.environ.get("SKYLEDGER_CONFIG")
    if explicit:
        return Path(explicit).expanduser()

    for candidate in DEFAULT_CONFIG_PATHS:
        resolved = Path(candidate).expanduser()
        if resolved.exists():
            return resolved
    return None


def _coerce(value: Any, annotation: Any) -> Any:
    if isinstance(annotation, str):
        annotation = {
            "float": float,
            "int": int,
            "str": str,
            "bool": bool,
        }.get(annotation, annotation)

    if annotation is bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)
    if annotation is int:
        return int(value)
    if annotation is float:
        return float(value)
    if annotation is str:
        return "" if value is None else str(value)
    return value
