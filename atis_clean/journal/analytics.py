from __future__ import annotations

from datetime import datetime
from pathlib import Path
import csv
from typing import Dict, List

HEADERS = ["date", "ticker", "strategy", "action", "entry", "exit", "shares", "stop", "target", "pnl", "r_multiple", "result", "notes"]

def journal_path() -> Path:
    data_dir = Path.cwd() / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir / "trade_journal.csv"

def ensure_journal_file() -> Path:
    path = journal_path()
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=HEADERS).writeheader()
    return path

def planned_trade_from_row(row: dict, strategy: str = "Paper Trade") -> dict:
    entry = float(row.get("entry", row.get("price", 0)) or 0)
    stop = float(row.get("stop", 0) or 0)
    target = float(row.get("target1", 0) or 0)
    shares = 100
    risk_per_share = max(entry - stop, 0.01)
    reward = max(target - entry, 0)
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "ticker": row.get("ticker", ""),
        "strategy": strategy,
        "action": row.get("ai_decision", {}).get("ai_action", row.get("action", "WATCH")),
        "entry": entry,
        "exit": "",
        "shares": shares,
        "stop": stop,
        "target": target,
        "pnl": round(reward * shares, 2),
        "r_multiple": round(reward / risk_per_share, 2),
        "result": "Planned",
        "notes": f"Planned from ATIS score {row.get('score')}/100",
    }

def append_trade(trade: dict) -> Path:
    path = ensure_journal_file()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writerow({h: trade.get(h, "") for h in HEADERS})
    return path

def load_trades() -> List[dict]:
    path = ensure_journal_file()
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def sample_trades() -> List[dict]:
    return [
        {"date":"2026-06-01","ticker":"TSLA","strategy":"Day Trade","action":"BUY WATCH","entry":"240","exit":"248","shares":"50","stop":"235","target":"250","pnl":"400","r_multiple":"1.6","result":"Win","notes":"Clean VWAP hold"},
        {"date":"2026-06-03","ticker":"NVDA","strategy":"Momentum","action":"WATCH","entry":"126","exit":"124","shares":"80","stop":"123","target":"132","pnl":"-160","r_multiple":"-0.67","result":"Loss","notes":"Entered before confirmation"},
        {"date":"2026-06-07","ticker":"SLV","strategy":"Metals","action":"BUY WATCH","entry":"29.5","exit":"30.4","shares":"300","stop":"29.1","target":"31","pnl":"270","r_multiple":"2.25","result":"Win","notes":"Metals strength"},
        {"date":"2026-06-10","ticker":"HL","strategy":"Metals","action":"WATCH","entry":"6.7","exit":"7.05","shares":"500","stop":"6.5","target":"7.2","pnl":"175","r_multiple":"1.75","result":"Win","notes":"Miner follow-through"},
    ]

def trades_for_analytics() -> List[dict]:
    trades = load_trades()
    completed = [t for t in trades if str(t.get("result", "")).lower() in {"win", "loss"}]
    return completed if completed else sample_trades()

def _num(value, default=0.0):
    try:
        if value in ("", None):
            return default
        return float(value)
    except Exception:
        return default

def performance_metrics(trades: List[dict] | None = None) -> dict:
    trades = trades if trades is not None else trades_for_analytics()
    completed = [t for t in trades if str(t.get("result", "")).lower() in {"win", "loss"}]
    wins = [t for t in completed if str(t.get("result", "")).lower() == "win"]
    losses = [t for t in completed if str(t.get("result", "")).lower() == "loss"]
    total_pnl = sum(_num(t.get("pnl")) for t in completed)
    gross_win = sum(max(_num(t.get("pnl")), 0) for t in completed)
    gross_loss = abs(sum(min(_num(t.get("pnl")), 0) for t in completed))
    return {
        "total_trades": len(completed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round((len(wins) / len(completed) * 100) if completed else 0, 1),
        "total_pnl": round(total_pnl, 2),
        "avg_win": round(gross_win / len(wins), 2) if wins else 0,
        "avg_loss": round(gross_loss / len(losses), 2) if losses else 0,
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss else round(gross_win, 2),
        "expectancy": round(total_pnl / len(completed), 2) if completed else 0,
        "avg_r": round(sum(_num(t.get("r_multiple")) for t in completed) / len(completed), 2) if completed else 0,
        "largest_win": round(max([_num(t.get("pnl")) for t in completed] or [0]), 2),
        "largest_loss": round(min([_num(t.get("pnl")) for t in completed] or [0]), 2),
    }

def strategy_breakdown(trades: List[dict] | None = None) -> Dict[str, dict]:
    trades = trades if trades is not None else trades_for_analytics()
    out = {}
    for t in trades:
        strategy = t.get("strategy") or "Uncategorized"
        out.setdefault(strategy, {"count": 0, "pnl": 0.0})
        out[strategy]["count"] += 1
        out[strategy]["pnl"] += _num(t.get("pnl"))
    for v in out.values():
        v["pnl"] = round(v["pnl"], 2)
    return out

def analytics_report() -> str:
    metrics = performance_metrics()
    breakdown = strategy_breakdown()
    lines = [
        "TRADE JOURNAL ANALYTICS",
        "",
        f"Completed trades: {metrics['total_trades']}",
        f"Wins / Losses: {metrics['wins']} / {metrics['losses']}",
        f"Win rate: {metrics['win_rate']}%",
        f"Total P/L: ${metrics['total_pnl']:,}",
        f"Average winner: ${metrics['avg_win']:,}",
        f"Average loser: ${metrics['avg_loss']:,}",
        f"Profit factor: {metrics['profit_factor']}",
        f"Expectancy/trade: ${metrics['expectancy']:,}",
        f"Average R: {metrics['avg_r']}",
        f"Largest win: ${metrics['largest_win']:,}",
        f"Largest loss: ${metrics['largest_loss']:,}",
        "",
        "Strategy breakdown:",
    ]
    for strategy, data in breakdown.items():
        lines.append(f"- {strategy}: {data['count']} trades | P/L ${data['pnl']:,}")
    return "\n".join(lines)

def journal_review(row: dict) -> str:
    trade = planned_trade_from_row(row)
    return f"""AI JOURNAL REVIEW — {row.get('ticker')}

Planned Setup:
Action: {trade['action']}
Entry: ${trade['entry']}
Stop: ${trade['stop']}
Target: ${trade['target']}
Default shares: {trade['shares']}
Planned R multiple: {trade['r_multiple']}

Review Checklist:
- Did price hold VWAP?
- Did volume confirm?
- Was entry near the planned zone?
- Was stop respected?
- Was the trade aligned with ATIS score and AI confidence?

Improvement Prompt:
After the trade, record exit, P/L, result, and notes so ATIS can evaluate performance over time.
"""
