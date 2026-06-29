from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


PRESETS = {
    "Day Trade": {
        "min_score": 70,
        "min_change": 1.0,
        "min_rvol": 2.0,
        "require_above_vwap": True,
        "require_above_ema9": True,
        "require_above_ema20": False,
        "require_news": False,
        "require_new_high": False,
    },
    "High Momentum": {
        "min_score": 80,
        "min_change": 2.0,
        "min_rvol": 2.5,
        "require_above_vwap": True,
        "require_above_ema9": True,
        "require_above_ema20": True,
        "require_news": False,
        "require_new_high": True,
    },
    "Swing": {
        "min_score": 60,
        "min_change": 0.0,
        "min_rvol": 1.0,
        "require_above_vwap": False,
        "require_above_ema9": False,
        "require_above_ema20": True,
        "require_news": False,
        "require_new_high": False,
    },
    "Metals": {
        "min_score": 45,
        "min_change": -5.0,
        "min_rvol": 0.5,
        "require_above_vwap": False,
        "require_above_ema9": False,
        "require_above_ema20": False,
        "require_news": False,
        "require_new_high": False,
        "symbols": {"SLV", "GLD", "GDX", "GDXJ", "SILJ", "HL", "AG", "CDE"},
    },
    "ETF": {
        "min_score": 40,
        "min_change": -5.0,
        "min_rvol": 0.5,
        "require_above_vwap": False,
        "require_above_ema9": False,
        "require_above_ema20": False,
        "require_news": False,
        "require_new_high": False,
        "symbols": {"SLV", "GLD", "SPY", "QQQ", "GDX", "GDXJ", "SILJ"},
    },
    "All": {
        "min_score": 0,
        "min_change": -100.0,
        "min_rvol": 0.0,
        "require_above_vwap": False,
        "require_above_ema9": False,
        "require_above_ema20": False,
        "require_news": False,
        "require_new_high": False,
    },
}


def preset_names() -> List[str]:
    return list(PRESETS.keys())


def bucket(row: dict) -> str:
    score = row.get("score", 0)
    if score >= 85:
        return "High Conviction"
    if score >= 70:
        return "Momentum"
    if score >= 55:
        return "Watch"
    return "Avoid"


def _passes_bool(row: dict, key: str, enabled: bool) -> bool:
    if not enabled:
        return True
    return bool(row.get(key, False))


def scan_rows(rows: Iterable[dict], preset: str = "Day Trade", custom: dict | None = None) -> List[dict]:
    rules = dict(PRESETS.get(preset, PRESETS["Day Trade"]))
    if custom:
        rules.update({k: v for k, v in custom.items() if v is not None})

    out = []
    symbols = rules.get("symbols")

    for row in rows:
        if symbols and row.get("ticker") not in symbols:
            continue
        if row.get("score", 0) < float(rules.get("min_score", 0)):
            continue
        if row.get("change_pct", 0) < float(rules.get("min_change", -100)):
            continue
        if row.get("relative_volume", 0) < float(rules.get("min_rvol", 0)):
            continue
        if not _passes_bool(row, "above_vwap", bool(rules.get("require_above_vwap", False))):
            continue
        if not _passes_bool(row, "above_9ema", bool(rules.get("require_above_ema9", False))):
            continue
        if not _passes_bool(row, "above_20ema", bool(rules.get("require_above_ema20", False))):
            continue
        if not _passes_bool(row, "news", bool(rules.get("require_news", False))):
            continue
        if not _passes_bool(row, "new_intraday_high", bool(rules.get("require_new_high", False))):
            continue

        item = dict(row)
        item["scanner_bucket"] = bucket(row)
        item["scanner_preset"] = preset
        out.append(item)

    out.sort(key=lambda r: (r.get("score", 0), r.get("relative_volume", 0), r.get("change_pct", 0)), reverse=True)
    for i, row in enumerate(out, 1):
        row["scanner_rank"] = i
    return out


def scanner_report(rows: List[dict], preset: str) -> str:
    if not rows:
        return f"""SCANNER ENGINE — {preset}

No symbols currently match this preset.

Try:
- Lower the score filter
- Use the All preset
- Switch to Fallback mode
- Search a ticker directly from the top Symbol box
"""

    top = rows[0]
    lines = [
        f"SCANNER ENGINE — {preset}",
        "",
        f"Matches: {len(rows)}",
        f"Top setup: {top['ticker']} — {top.get('action')} | Score {top.get('score')}/100",
        "",
        "Top Results:",
    ]
    for row in rows[:10]:
        lines.append(
            f"#{row['scanner_rank']} {row['ticker']} | Score {row.get('score')} | "
            f"Change {row.get('change_pct')}% | RVOL {row.get('relative_volume')}x | {row.get('action')}"
        )
    return "\n".join(lines)
