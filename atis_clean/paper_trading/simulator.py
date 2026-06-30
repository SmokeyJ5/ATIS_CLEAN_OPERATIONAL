from __future__ import annotations

from datetime import datetime
from pathlib import Path
import csv
import json
from typing import Dict, List

from atis_clean.core.paths import data_root
from atis_clean.core.settings import load_settings


ORDER_HEADERS = ["time", "ticker", "side", "quantity", "price", "value", "status", "notes"]


def starting_cash() -> float:
    settings = load_settings()
    try:
        return float(settings.get("paper_account_starting_cash", 100000.0))
    except Exception:
        return 100000.0


def data_dir() -> Path:
    path = data_root()
    path.mkdir(exist_ok=True)
    return path


def account_path() -> Path:
    return data_dir() / "paper_account.json"


def orders_path() -> Path:
    return data_dir() / "paper_orders.csv"


def ensure_account() -> dict:
    path = account_path()
    if not path.exists():
        account = {"cash": starting_cash(), "realized_pnl": 0.0, "positions": {}}
        save_account(account)
        return account
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        account = {"cash": starting_cash(), "realized_pnl": 0.0, "positions": {}}
        save_account(account)
        return account


def save_account(account: dict) -> None:
    account_path().write_text(json.dumps(account, indent=2), encoding="utf-8")


def ensure_orders_log() -> Path:
    path = orders_path()
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=ORDER_HEADERS).writeheader()
    return path


def log_order(order: dict) -> None:
    path = ensure_orders_log()
    with path.open("a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=ORDER_HEADERS).writerow({h: order.get(h, "") for h in ORDER_HEADERS})


def load_orders() -> List[dict]:
    path = ensure_orders_log()
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def reset_account() -> dict:
    account = {"cash": starting_cash(), "realized_pnl": 0.0, "positions": {}}
    save_account(account)
    ensure_orders_log()
    return account


def buy(ticker: str, quantity: int, price: float, notes: str = "") -> dict:
    ticker = ticker.upper()
    quantity = int(quantity)
    price = float(price)
    account = ensure_account()
    value = round(quantity * price, 2)

    if quantity <= 0:
        return {"status": "REJECTED", "message": "Quantity must be positive."}
    if value > float(account.get("cash", 0)):
        return {"status": "REJECTED", "message": "Not enough paper cash."}

    pos = account["positions"].get(ticker, {"quantity": 0, "avg_cost": 0.0})
    old_qty = int(pos["quantity"])
    old_cost = float(pos["avg_cost"])
    new_qty = old_qty + quantity
    new_avg = ((old_qty * old_cost) + value) / new_qty if new_qty else 0

    account["positions"][ticker] = {"quantity": new_qty, "avg_cost": round(new_avg, 4)}
    account["cash"] = round(float(account["cash"]) - value, 2)
    save_account(account)

    order = {
        "time": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
        "ticker": ticker,
        "side": "BUY",
        "quantity": quantity,
        "price": round(price, 2),
        "value": value,
        "status": "FILLED",
        "notes": notes,
    }
    log_order(order)
    return {"status": "FILLED", "message": f"Bought {quantity} {ticker} @ ${price}", "order": order}


def sell(ticker: str, quantity: int, price: float, notes: str = "") -> dict:
    ticker = ticker.upper()
    quantity = int(quantity)
    price = float(price)
    account = ensure_account()
    positions = account.get("positions", {})
    pos = positions.get(ticker)

    if quantity <= 0:
        return {"status": "REJECTED", "message": "Quantity must be positive."}
    if not pos or int(pos.get("quantity", 0)) < quantity:
        return {"status": "REJECTED", "message": "Not enough shares to sell."}

    avg_cost = float(pos["avg_cost"])
    value = round(quantity * price, 2)
    realized = round((price - avg_cost) * quantity, 2)

    remaining = int(pos["quantity"]) - quantity
    if remaining > 0:
        positions[ticker] = {"quantity": remaining, "avg_cost": avg_cost}
    else:
        positions.pop(ticker, None)

    account["cash"] = round(float(account["cash"]) + value, 2)
    account["realized_pnl"] = round(float(account.get("realized_pnl", 0)) + realized, 2)
    account["positions"] = positions
    save_account(account)

    order = {
        "time": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
        "ticker": ticker,
        "side": "SELL",
        "quantity": quantity,
        "price": round(price, 2),
        "value": value,
        "status": "FILLED",
        "notes": notes or f"Realized P/L ${realized}",
    }
    log_order(order)
    return {"status": "FILLED", "message": f"Sold {quantity} {ticker} @ ${price}; P/L ${realized}", "order": order}


def account_summary(price_lookup=None) -> dict:
    account = ensure_account()
    positions = account.get("positions", {})
    market_value = 0.0
    unrealized = 0.0
    enriched = []

    for ticker, pos in positions.items():
        qty = int(pos.get("quantity", 0))
        avg = float(pos.get("avg_cost", 0))
        current = avg
        if price_lookup:
            try:
                current = float(price_lookup(ticker) or avg)
            except Exception:
                current = avg
        value = qty * current
        pnl = (current - avg) * qty
        market_value += value
        unrealized += pnl
        enriched.append({
            "ticker": ticker,
            "quantity": qty,
            "avg_cost": round(avg, 2),
            "current_price": round(current, 2),
            "market_value": round(value, 2),
            "unrealized_pnl": round(pnl, 2),
        })

    equity = float(account.get("cash", 0)) + market_value

    return {
        "cash": round(float(account.get("cash", 0)), 2),
        "market_value": round(market_value, 2),
        "equity": round(equity, 2),
        "realized_pnl": round(float(account.get("realized_pnl", 0)), 2),
        "unrealized_pnl": round(unrealized, 2),
        "positions": enriched,
    }


def account_report(summary: dict) -> str:
    return f"""PAPER TRADING ACCOUNT

Cash:
${summary['cash']:,}

Market Value:
${summary['market_value']:,}

Equity:
${summary['equity']:,}

Realized P/L:
${summary['realized_pnl']:,}

Unrealized P/L:
${summary['unrealized_pnl']:,}

Open Positions:
{len(summary['positions'])}

Note:
This is simulated paper trading only. No real broker orders are sent.
"""
