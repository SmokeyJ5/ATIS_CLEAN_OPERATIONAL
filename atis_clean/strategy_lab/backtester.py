from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict


STRATEGIES = {
    "EMA/VWAP Momentum": {
        "description": "Buy when price is above VWAP and short EMA trend is positive.",
    },
    "Breakout Volume": {
        "description": "Buy breakouts when candles push above recent highs with volume confirmation.",
    },
    "Mean Reversion": {
        "description": "Buy dips near lower range and target return toward VWAP.",
    },
    "Metals Swing": {
        "description": "Trend-following style tuned for metals/miners using wider stops.",
    },
}


def strategy_names():
    return list(STRATEGIES.keys())


def _num(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def backtest(row: dict, strategy: str = "EMA/VWAP Momentum", starting_capital: float = 10000.0, risk_pct: float = 1.0) -> dict:
    candles = row.get("candles", []) or []
    if len(candles) < 10:
        return empty_result(row, strategy, starting_capital)

    trades = []
    equity = starting_capital
    equity_curve = [equity]

    for i in range(6, len(candles) - 3, 5):
        window = candles[max(0, i - 5):i]
        c = candles[i]
        next_c = candles[min(i + 3, len(candles) - 1)]

        close = _num(c.get("close"))
        high_recent = max(_num(x.get("high")) for x in window)
        low_recent = min(_num(x.get("low")) for x in window)
        vwap = _num(row.get("vwap"), close)

        signal = False
        stop = low_recent
        target = close + (close - stop) * 1.8

        if strategy == "EMA/VWAP Momentum":
            signal = close > vwap and close >= high_recent * 0.995
        elif strategy == "Breakout Volume":
            signal = close >= high_recent * 0.998
            target = close + (close - stop) * 2.0
        elif strategy == "Mean Reversion":
            signal = close <= low_recent * 1.01
            stop = close * 0.985
            target = vwap if vwap > close else close * 1.025
        elif strategy == "Metals Swing":
            signal = close > vwap * 0.99
            stop = close * 0.94
            target = close * 1.08

        if not signal:
            continue

        risk_budget = equity * (risk_pct / 100)
        risk_per_share = max(close - stop, 0.01)
        qty = max(int(risk_budget // risk_per_share), 1)

        future_high = max(_num(x.get("high")) for x in candles[i + 1:min(i + 6, len(candles))])
        future_low = min(_num(x.get("low")) for x in candles[i + 1:min(i + 6, len(candles))])

        if future_low <= stop:
            exit_price = stop
            result = "Loss"
        elif future_high >= target:
            exit_price = target
            result = "Win"
        else:
            exit_price = _num(next_c.get("close"), close)
            result = "Win" if exit_price > close else "Loss"

        pnl = round((exit_price - close) * qty, 2)
        r_multiple = round(pnl / max(qty * risk_per_share, 0.01), 2)
        equity += pnl
        equity_curve.append(round(equity, 2))

        trades.append({
            "entry_index": i,
            "entry": round(close, 2),
            "exit": round(exit_price, 2),
            "qty": qty,
            "stop": round(stop, 2),
            "target": round(target, 2),
            "pnl": pnl,
            "r": r_multiple,
            "result": result,
        })

    return build_result(row, strategy, starting_capital, equity, trades, equity_curve)


def empty_result(row: dict, strategy: str, starting_capital: float) -> dict:
    return {
        "ticker": row.get("ticker", ""),
        "strategy": strategy,
        "starting_capital": starting_capital,
        "ending_equity": starting_capital,
        "net_pnl": 0,
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": 0,
        "profit_factor": 0,
        "max_drawdown": 0,
        "avg_trade": 0,
        "avg_r": 0,
        "trades": [],
        "equity_curve": [starting_capital],
        "report": "Not enough candles to backtest.",
    }


def build_result(row: dict, strategy: str, starting_capital: float, ending_equity: float, trades: List[dict], equity_curve: List[float]) -> dict:
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]

    gross_win = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    net = ending_equity - starting_capital

    peak = starting_capital
    max_dd = 0
    for value in equity_curve:
        peak = max(peak, value)
        drawdown = peak - value
        max_dd = max(max_dd, drawdown)

    total = len(trades)
    result = {
        "ticker": row.get("ticker", ""),
        "strategy": strategy,
        "starting_capital": round(starting_capital, 2),
        "ending_equity": round(ending_equity, 2),
        "net_pnl": round(net, 2),
        "total_trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / total * 100, 1) if total else 0,
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss else round(gross_win, 2),
        "max_drawdown": round(max_dd, 2),
        "avg_trade": round(net / total, 2) if total else 0,
        "avg_r": round(sum(t["r"] for t in trades) / total, 2) if total else 0,
        "trades": trades,
        "equity_curve": equity_curve,
    }
    result["report"] = backtest_report(result)
    return result


def backtest_report(result: dict) -> str:
    return f"""STRATEGY LAB BACKTEST — {result['ticker']}

Strategy:
{result['strategy']}

Starting Capital:
${result['starting_capital']:,}

Ending Equity:
${result['ending_equity']:,}

Net P/L:
${result['net_pnl']:,}

Trades:
{result['total_trades']}

Wins / Losses:
{result['wins']} / {result['losses']}

Win Rate:
{result['win_rate']}%

Profit Factor:
{result['profit_factor']}

Average Trade:
${result['avg_trade']:,}

Average R:
{result['avg_r']}

Max Drawdown:
${result['max_drawdown']:,}

AI Review:
This is a simulated backtest using ATIS candle data. Treat it as research support, not proof of future performance. Look for repeatability, reasonable drawdown, and consistency across multiple symbols.
"""
