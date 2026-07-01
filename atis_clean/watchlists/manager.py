from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from atis_clean.core.paths import atomic_write_text, config_root


DEFAULT_WATCHLISTS = {
    "Day Trading": ["TSLA", "NVDA", "AAPL", "MSFT", "AMD", "QQQ", "SPY"],
    "Silver Miners": ["SLV", "SILJ", "HL", "AG", "CDE", "PAAS"],
    "Gold Miners": ["GLD", "GDX", "GDXJ", "NEM", "AEM"],
    "Copper Uranium": ["FCX", "SCCO", "COPX", "URNM"],
    "Favorites": ["TSLA", "NVDA", "SLV", "HL"],
}


def watchlist_dir() -> Path:
    path = config_root() / "watchlists"
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_name(name: str) -> str:
    return "".join(ch for ch in name if ch.isalnum() or ch in (" ", "_", "-")).strip().replace(" ", "_")


def watchlist_path(name: str) -> Path:
    return watchlist_dir() / f"{safe_name(name)}.json"


def ensure_default_watchlists() -> None:
    for name, symbols in DEFAULT_WATCHLISTS.items():
        path = watchlist_path(name)
        if not path.exists():
            save_watchlist(name, symbols)


def save_watchlist(name: str, symbols: List[str]) -> Path:
    symbols = [s.strip().upper() for s in symbols if s and s.strip()]
    payload = {"name": name, "symbols": sorted(set(symbols))}
    path = watchlist_path(name)
    atomic_write_text(path, json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_watchlist(name: str) -> List[str]:
    ensure_default_watchlists()
    path = watchlist_path(name)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [s.strip().upper() for s in data.get("symbols", []) if s.strip()]
    except Exception:
        return []


def list_watchlists() -> List[str]:
    ensure_default_watchlists()
    names = []
    for path in watchlist_dir().glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            names.append(data.get("name") or path.stem.replace("_", " "))
        except Exception:
            names.append(path.stem.replace("_", " "))
    return sorted(set(names))


def add_symbol(name: str, symbol: str) -> List[str]:
    symbols = load_watchlist(name)
    symbol = symbol.strip().upper()
    if symbol and symbol not in symbols:
        symbols.append(symbol)
    save_watchlist(name, symbols)
    return sorted(set(symbols))


def remove_symbol(name: str, symbol: str) -> List[str]:
    symbol = symbol.strip().upper()
    symbols = [s for s in load_watchlist(name) if s != symbol]
    save_watchlist(name, symbols)
    return symbols


def watchlist_report() -> str:
    lines = ["ATIS WATCHLIST MANAGER", ""]
    for name in list_watchlists():
        symbols = load_watchlist(name)
        lines.append(f"{name}: {len(symbols)} symbols")
        lines.append(", ".join(symbols))
        lines.append("")
    return "\n".join(lines)
