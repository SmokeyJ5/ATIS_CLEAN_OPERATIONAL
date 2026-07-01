from __future__ import annotations

from datetime import datetime
import csv
from pathlib import Path
from typing import List

from atis_clean.core.paths import data_root


ALERT_HEADERS = ["time", "ticker", "alert", "level", "status", "message"]


def alert_log_path() -> Path:
    data_dir = data_root()
    data_dir.mkdir(exist_ok=True)
    return data_dir / "alerts_log.csv"


def ensure_alert_log() -> Path:
    path = alert_log_path()
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=ALERT_HEADERS).writeheader()
    return path


def log_alert(alert: dict) -> Path:
    path = ensure_alert_log()
    row = {h: alert.get(h, "") for h in ALERT_HEADERS}
    with path.open("a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=ALERT_HEADERS).writerow(row)
    return path


def load_alerts() -> List[dict]:
    path = ensure_alert_log()
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _coerce_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def evaluate_alerts(row: dict) -> List[dict]:
    ticker = row.get("ticker", "")
    price = _coerce_float(row.get("price", 0), 0)
    vwap = _coerce_float(row.get("vwap", 0), 0)
    ema9 = _coerce_float(row.get("ema9", 0), 0)
    ema20 = _coerce_float(row.get("ema20", 0), 0)
    rvol = _coerce_float(row.get("relative_volume", 0), 0)
    change = _coerce_float(row.get("change_pct", 0), 0)
    ai = row.get("ai_decision", {}) if isinstance(row.get("ai_decision", {}), dict) else {}
    ai_score = int(_coerce_float(ai.get("ai_score", row.get("score", 0)), 0))

    now = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    alerts = []

    def add(name, level, status, message):
        alerts.append({
            "time": now,
            "ticker": ticker,
            "alert": name,
            "level": level,
            "status": status,
            "message": message,
        })

    if price and vwap:
        if price > vwap:
            add("VWAP Reclaim", round(vwap, 2), "ACTIVE", f"{ticker} is above VWAP.")
        else:
            add("VWAP Loss", round(vwap, 2), "WARNING", f"{ticker} is below VWAP.")

    if ema9 and ema20:
        if price > ema9 > ema20:
            add("EMA Alignment", f"9>{20}", "ACTIVE", "Price is above 9 EMA and 9 EMA is above 20 EMA.")
        elif price < ema20:
            add("EMA Weakness", round(ema20, 2), "WARNING", "Price is below 20 EMA.")
        else:
            add("EMA Watch", round(ema9, 2), "WATCH", "EMA structure is mixed.")

    if rvol >= 3:
        add("Volume Spike", f"{rvol}x", "ACTIVE", "Relative volume is above 3x.")
    elif rvol >= 2:
        add("Volume Watch", f"{rvol}x", "WATCH", "Relative volume is above 2x.")
    else:
        add("Low Volume", f"{rvol}x", "QUIET", "Relative volume is below alert threshold.")

    if change >= 4:
        add("Momentum Surge", f"{change}%", "ACTIVE", "Strong positive momentum.")
    elif change <= -3:
        add("Downside Pressure", f"{change}%", "WARNING", "Negative momentum is elevated.")

    if ai_score >= 85:
        add("AI High Conviction", f"{ai_score}/100", "ACTIVE", "AI score is above 85.")
    elif ai_score >= 70:
        add("AI Watch", f"{ai_score}/100", "WATCH", "AI score is in watch range.")
    else:
        add("AI Low Score", f"{ai_score}/100", "QUIET", "AI score is below high-conviction threshold.")

    if row.get("new_intraday_high"):
        add("New Intraday High", row.get("day_high", ""), "ACTIVE", "Symbol is making/testing intraday high.")

    if row.get("news"):
        add("Catalyst Flag", "News", "ACTIVE", "News/catalyst flag is active.")

    return alerts


def alerts_report(row: dict) -> str:
    alerts = evaluate_alerts(row)
    active = [a for a in alerts if a["status"] == "ACTIVE"]
    warnings = [a for a in alerts if a["status"] == "WARNING"]
    watch = [a for a in alerts if a["status"] == "WATCH"]

    lines = [
        f"ALERT ENGINE — {row.get('ticker')}",
        "",
        f"Active alerts: {len(active)}",
        f"Warnings: {len(warnings)}",
        f"Watch alerts: {len(watch)}",
        "",
        "Current alerts:",
    ]

    for a in alerts:
        lines.append(f"- {a['status']} | {a['alert']} @ {a['level']} — {a['message']}")

    lines.append("")
    lines.append("Automation note:")
    lines.append("This phase evaluates alerts safely when a symbol is loaded or refreshed. It does not run a high-frequency background loop.")

    return "\n".join(lines)
