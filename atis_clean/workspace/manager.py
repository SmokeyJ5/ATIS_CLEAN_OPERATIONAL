from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
from typing import Dict, List


DEFAULT_WORKSPACES = {
    "Day Trading": {
        "selected_symbol": "TSLA",
        "multi_chart_layout": "4 Charts",
        "linked_charts": True,
        "data_mode": "Fallback",
        "scanner_preset": "Day Trade",
        "chart_timeframe": "5m",
        "notes": "Momentum scanner, AI decision, alerts, and charts.",
    },
    "Swing Trading": {
        "selected_symbol": "NVDA",
        "multi_chart_layout": "4 Charts",
        "linked_charts": True,
        "data_mode": "Fallback",
        "scanner_preset": "Swing",
        "chart_timeframe": "Daily",
        "notes": "Trend, portfolio risk, journal, and market intelligence.",
    },
    "Metals Dashboard": {
        "selected_symbol": "SLV",
        "multi_chart_layout": "6 Charts",
        "linked_charts": False,
        "data_mode": "Fallback",
        "scanner_preset": "Metals",
        "chart_timeframe": "1h",
        "notes": "Silver, gold, miners, dollar, yields, and market intelligence.",
    },
    "Market Overview": {
        "selected_symbol": "SPY",
        "multi_chart_layout": "6 Charts",
        "linked_charts": False,
        "data_mode": "Fallback",
        "scanner_preset": "ETF",
        "chart_timeframe": "Daily",
        "notes": "Broad market, ETFs, VIX context, and economic calendar.",
    },
}


def workspace_root() -> Path:
    path = Path.cwd() / "config" / "workspaces"
    path.mkdir(parents=True, exist_ok=True)
    return path


def workspace_file(name: str) -> Path:
    safe = "".join(ch for ch in name if ch.isalnum() or ch in (" ", "_", "-")).strip().replace(" ", "_")
    return workspace_root() / f"{safe}.json"


def ensure_default_workspaces() -> None:
    for name, data in DEFAULT_WORKSPACES.items():
        path = workspace_file(name)
        if not path.exists():
            save_workspace(name, data)


def save_workspace(name: str, data: dict) -> Path:
    payload = dict(data)
    payload["workspace_name"] = name
    payload["saved_at"] = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    path = workspace_file(name)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path


def load_workspace(name: str) -> dict:
    ensure_default_workspaces()
    path = workspace_file(name)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def list_workspaces() -> List[str]:
    ensure_default_workspaces()
    names = []
    for path in workspace_root().glob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            names.append(data.get("workspace_name") or path.stem.replace("_", " "))
        except Exception:
            names.append(path.stem.replace("_", " "))
    return sorted(set(names))


def delete_workspace(name: str) -> bool:
    path = workspace_file(name)
    if path.exists():
        path.unlink()
        return True
    return False


def workspace_report() -> str:
    ensure_default_workspaces()
    names = list_workspaces()
    lines = [
        "WORKSPACE MANAGER",
        "",
        f"Saved workspaces: {len(names)}",
        "",
    ]
    for name in names:
        data = load_workspace(name)
        lines.append(f"{name}")
        lines.append(f"- Symbol: {data.get('selected_symbol', 'N/A')}")
        lines.append(f"- Layout: {data.get('multi_chart_layout', 'N/A')}")
        lines.append(f"- Scanner: {data.get('scanner_preset', 'N/A')}")
        lines.append(f"- Notes: {data.get('notes', '')}")
        lines.append("")
    return "\n".join(lines)
