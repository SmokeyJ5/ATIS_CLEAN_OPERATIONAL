from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


DEFAULT_CAPITAL = 20000.0
DEFAULT_RISK_PCT = 1.0


def position_size(row: dict, capital: float = DEFAULT_CAPITAL, risk_pct: float = DEFAULT_RISK_PCT) -> dict:
    price = float(row.get("price", 0) or 0)
    entry = float(row.get("entry", price) or price)
    stop = float(row.get("stop", 0) or 0)
    target1 = float(row.get("target1", 0) or 0)
    target2 = float(row.get("target2", 0) or 0)

    risk_budget = capital * (risk_pct / 100)
    risk_per_share = max(entry - stop, 0.01)
    shares = int(risk_budget // risk_per_share)
    cost = shares * entry
    max_loss = shares * risk_per_share
    profit_t1 = shares * max(target1 - entry, 0)
    profit_t2 = shares * max(target2 - entry, 0)

    return {
        "ticker": row.get("ticker", ""),
        "capital": round(capital, 2),
        "risk_pct": risk_pct,
        "risk_budget": round(risk_budget, 2),
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "target1": round(target1, 2),
        "target2": round(target2, 2),
        "risk_per_share": round(risk_per_share, 2),
        "shares": max(shares, 0),
        "estimated_cost": round(cost, 2),
        "max_loss": round(max_loss, 2),
        "profit_target1": round(profit_t1, 2),
        "profit_target2": round(profit_t2, 2),
        "reward_risk_t1": round((profit_t1 / max_loss), 2) if max_loss else 0,
        "reward_risk_t2": round((profit_t2 / max_loss), 2) if max_loss else 0,
    }


def asset_class(row: dict) -> str:
    ticker = row.get("ticker", "")
    metals = {"SLV", "GLD", "GDX", "GDXJ", "SILJ", "HL", "AG", "CDE"}
    etfs = {"SPY", "QQQ", "SLV", "GLD", "GDX", "GDXJ", "SILJ"}
    crypto = {"MARA", "COIN"}
    if ticker in metals:
        return "Metals / Miners"
    if ticker in etfs:
        return "ETF"
    if ticker in crypto:
        return "Crypto-linked"
    return "Equity"


def exposure_summary(rows: List[dict]) -> dict:
    buckets = {}
    for row in rows:
        bucket = asset_class(row)
        buckets[bucket] = buckets.get(bucket, 0) + 1
    total = sum(buckets.values()) or 1
    return {
        "counts": buckets,
        "percentages": {k: round(v / total * 100, 1) for k, v in buckets.items()},
        "total_symbols": total,
    }


def risk_report(row: dict, capital: float = DEFAULT_CAPITAL, risk_pct: float = DEFAULT_RISK_PCT) -> str:
    p = position_size(row, capital, risk_pct)
    return f"""PORTFOLIO RISK MANAGER — {row.get('ticker')}

Capital Assumption:
${p['capital']:,}

Risk Per Trade:
{p['risk_pct']}% = ${p['risk_budget']:,}

Suggested Position Size:
{p['shares']} shares

Estimated Cost:
${p['estimated_cost']:,}

Trade Plan:
Entry: ${p['entry']}
Stop: ${p['stop']}
Target 1: ${p['target1']}
Target 2: ${p['target2']}

Risk:
Risk/share: ${p['risk_per_share']}
Max loss at stop: ${p['max_loss']:,}

Reward:
Profit at Target 1: ${p['profit_target1']:,}
Profit at Target 2: ${p['profit_target2']:,}

Reward/Risk:
Target 1: {p['reward_risk_t1']}
Target 2: {p['reward_risk_t2']}

Guidance:
This is a position sizing model for planning and paper trading. It does not place trades.
"""


def exposure_report(rows: List[dict]) -> str:
    summary = exposure_summary(rows)
    lines = [
        "PORTFOLIO EXPOSURE SUMMARY",
        "",
        f"Tracked symbols: {summary['total_symbols']}",
        "",
        "Exposure buckets:",
    ]
    for bucket, count in summary["counts"].items():
        lines.append(f"- {bucket}: {count} symbols ({summary['percentages'][bucket]}%)")
    return "\n".join(lines)
