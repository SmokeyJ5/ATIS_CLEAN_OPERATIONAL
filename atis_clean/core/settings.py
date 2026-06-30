from __future__ import annotations

import json

from atis_clean.core.paths import config_root
from pathlib import Path


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
    except Exception:
        return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> Path:
    payload = dict(DEFAULT_SETTINGS)
    payload.update(settings or {})
    path = settings_path()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def settings_report() -> str:
    s = load_settings()
    lines = ["ATIS USER SETTINGS", ""]
    for k, v in s.items():
        lines.append(f"{k}: {v}")
    return "\n".join(lines)
