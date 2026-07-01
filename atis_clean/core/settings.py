from __future__ import annotations

import json
from pathlib import Path

from atis_clean.core.paths import config_root


DEFAULT_SETTINGS = {
    "data_mode": "Fallback",
    "default_symbol": "TSLA",
    "default_workspace": "Day Trading",
    "theme": "Dark Professional",
    "startup_tab": "Dashboard",
    "paper_account_starting_cash": 100000,
}


def settings_path() -> Path:
    return config_root() / "settings.json"


def load_settings() -> dict:
    path = settings_path()
    if not path.exists():
        save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        merged = dict(DEFAULT_SETTINGS)
        merged.update(data)
        return merged
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> Path:
    payload = dict(DEFAULT_SETTINGS)
    payload.update(settings or {})
    path = settings_path()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def settings_report() -> str:
    settings = load_settings()
    lines = ["ATIS USER SETTINGS", ""]
    for key, value in settings.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)
