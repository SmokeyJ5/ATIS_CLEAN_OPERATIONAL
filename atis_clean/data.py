from dataclasses import dataclass
from math import sin


def _build_candles_from_row(row, count=70, last_price=None):
    low = row["day_low"]
    high = row["day_high"]
    price = row["price"] if last_price is None else last_price
    span = max(high - low, 0.01)
    output = []
    previous = low
    for i in range(count):
        progress = i / max(count - 1, 1)
        base = low + (price - low) * progress
        wave = sin(i / 4) * span * 0.08
        close = max(min(base + wave, high * 1.01), low * 0.99)
        open_ = previous
        candle_high = max(open_, close) + span * 0.04
        candle_low = min(open_, close) - span * 0.04
        output.append({
            "open": round(open_, 2),
            "high": round(candle_high, 2),
            "low": round(candle_low, 2),
            "close": round(close, 2),
            "volume": int(row["volume"] / count),
        })
        previous = close
    output[-1]["close"] = price
    return output

SAMPLE = {
    "NVDA": ("NVIDIA", 128.50, 129.40, 124.20, 126.70, 127.60, 126.10, 2.85, 2.9, 61200000, True, False),
    "TSLA": ("Tesla", 244.80, 247.20, 236.50, 241.30, 243.60, 239.90, 3.65, 3.4, 88900000, True, True),
    "AAPL": ("Apple", 213.10, 214.40, 210.20, 212.50, 212.80, 211.90, 0.75, 1.1, 38900000, False, False),
    "MSFT": ("Microsoft", 449.20, 451.00, 444.60, 447.80, 448.90, 446.50, 1.10, 1.4, 22100000, False, False),
    "AMD": ("Advanced Micro Devices", 164.25, 165.10, 159.40, 162.20, 163.70, 161.60, 2.25, 2.5, 42100000, False, True),
    "PLTR": ("Palantir", 24.70, 25.10, 23.95, 24.35, 24.55, 24.10, 1.95, 2.2, 38200000, False, False),
    "MARA": ("MARA Holdings", 21.55, 22.05, 20.80, 21.20, 21.42, 21.05, 4.10, 3.7, 29600000, True, True),
    "COIN": ("Coinbase", 238.90, 242.30, 230.10, 236.20, 237.60, 234.80, 2.60, 2.6, 14200000, True, False),
    "SLV": ("iShares Silver Trust", 29.85, 30.10, 29.42, 29.72, 29.88, 29.66, 1.25, 2.1, 38500000, True, True),
    "GLD": ("SPDR Gold Shares", 218.40, 219.20, 216.90, 217.75, 218.10, 217.60, 0.82, 1.6, 11400000, False, False),
    "SPY": ("SPDR S&P 500 ETF", 548.10, 550.25, 546.70, 548.30, 548.50, 547.80, 0.35, 1.2, 60000000, False, False),
    "QQQ": ("Invesco QQQ Trust", 472.55, 475.10, 470.40, 472.80, 473.10, 471.90, 0.64, 1.5, 42000000, False, False),
    "GDX": ("VanEck Gold Miners ETF", 39.40, 40.05, 38.80, 39.25, 39.45, 39.10, 1.44, 1.8, 22000000, False, True),
    "GDXJ": ("VanEck Junior Gold Miners ETF", 48.25, 49.10, 47.55, 48.00, 48.20, 47.80, 1.72, 1.9, 11000000, False, True),
    "SILJ": ("Amplify Junior Silver Miners ETF", 14.80, 15.15, 14.40, 14.70, 14.82, 14.62, 2.10, 2.3, 4300000, True, True),
    "HL": ("Hecla Mining", 6.85, 7.02, 6.61, 6.78, 6.86, 6.72, 2.40, 2.5, 19000000, True, True),
    "AG": ("First Majestic Silver", 7.95, 8.18, 7.70, 7.88, 7.98, 7.82, 2.75, 2.7, 12000000, True, True),
    "CDE": ("Coeur Mining", 7.10, 7.35, 6.90, 7.02, 7.12, 6.98, 2.20, 2.4, 15000000, True, True),
}

def normalize(symbol: str) -> str:
    return (symbol or "").strip().upper()

def make_row(symbol: str):
    symbol = normalize(symbol)
    if symbol not in SAMPLE:
        return None

    name, price, high, low, vwap, ema9, ema20, chg, rvol, vol, news, new_high = SAMPLE[symbol]
    row = {
        "ticker": symbol,
        "name": name,
        "price": price,
        "day_high": high,
        "day_low": low,
        "vwap": vwap,
        "ema9": ema9,
        "ema20": ema20,
        "change_pct": chg,
        "relative_volume": rvol,
        "volume": vol,
        "news": news,
        "new_intraday_high": new_high,
        "above_vwap": price > vwap,
        "above_9ema": price > ema9,
        "above_20ema": price > ema20,
        "data_source": "STABLE FALLBACK",
    }
    row.update(decision(row))
    row["candles"] = candles(row)
    return row

def decision(row):
    score = 0
    passed = []
    missing = []

    if row["change_pct"] >= 3:
        score += 18; passed.append("Strong momentum")
    elif row["change_pct"] >= 1:
        score += 12; passed.append("Positive momentum")
    else:
        missing.append("Momentum")

    if row["relative_volume"] >= 3:
        score += 20; passed.append("RVOL above 3x")
    elif row["relative_volume"] >= 2:
        score += 15; passed.append("RVOL above 2x")
    else:
        missing.append("RVOL 2x+")

    for label, key, pts in [
        ("Above VWAP", "above_vwap", 15),
        ("Above 9 EMA", "above_9ema", 12),
        ("Above 20 EMA", "above_20ema", 12),
        ("New intraday high", "new_intraday_high", 13),
        ("News catalyst", "news", 8),
    ]:
        if row[key]:
            score += pts; passed.append(label)
        else:
            missing.append(label)

    score = max(0, min(100, score))

    if score >= 85:
        action = "BUY WATCH"
        status = "READY IF CONFIRMED"
    elif score >= 70:
        action = "WATCH"
        status = "NEEDS CONFIRMATION"
    elif score >= 55:
        action = "WAIT"
        status = "NOT READY"
    else:
        action = "AVOID"
        status = "SKIP"

    entry = round(row["price"], 2)
    stop = round(max(row["day_low"], row["price"] * 0.97), 2)
    target1 = round(row["price"] * 1.035, 2)
    target2 = round(row["price"] * 1.07, 2)
    risk = max(entry - stop, 0.01)
    reward = max(target1 - entry, 0.01)

    return {
        "score": score,
        "action": action,
        "status": status,
        "probability": min(96, max(25, score)),
        "confidence": "High" if score >= 85 else "Medium" if score >= 70 else "Low",
        "entry": entry,
        "stop": stop,
        "target1": target1,
        "target2": target2,
        "risk_reward": round(reward / risk, 2),
        "passed": passed,
        "missing": missing,
    }

def candles(row, count=70):
    return _build_candles_from_row(row, count=count)

def all_rows():
    rows = [make_row(symbol) for symbol in SAMPLE]
    rows = [r for r in rows if r]
    rows.sort(key=lambda r: r["score"], reverse=True)
    for i, row in enumerate(rows, 1):
        row["rank"] = i
    return rows


# Phase 3 market-data bridge.
def set_data_mode(mode: str):
    from atis_clean.market_data.provider import market_data_engine
    market_data_engine.set_mode(mode)

def get_data_mode() -> str:
    from atis_clean.market_data.provider import market_data_engine
    return market_data_engine.get_mode()

def market_diagnostics() -> str:
    from atis_clean.market_data.provider import market_data_engine
    return market_data_engine.diagnostics()

def make_row_live(symbol: str):
    from atis_clean.market_data.provider import market_data_engine
    row, _ = market_data_engine.get_row(symbol)
    return row

def all_rows_live():
    from atis_clean.market_data.provider import market_data_engine
    return market_data_engine.all_rows()
