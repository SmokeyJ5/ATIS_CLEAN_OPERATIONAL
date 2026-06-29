from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import sin
from typing import Dict, List, Optional, Tuple

from atis_clean.data import SAMPLE, decision


@dataclass
class MarketRow:
    ticker: str
    name: str
    price: float
    day_high: float
    day_low: float
    vwap: float
    ema9: float
    ema20: float
    change_pct: float
    relative_volume: float
    volume: int
    news: bool
    new_intraday_high: bool
    data_source: str


class FallbackProvider:
    name = "Stable Fallback"

    def available_symbols(self) -> List[str]:
        return sorted(SAMPLE.keys())

    def get_row(self, symbol: str) -> Optional[dict]:
        symbol = (symbol or "").strip().upper()
        data = SAMPLE.get(symbol)
        if not data:
            return None

        name, price, high, low, vwap, ema9, ema20, chg, rvol, vol, news, new_high = data
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
            "data_source": self.name,
            "updated": datetime.now().strftime("%I:%M:%S %p"),
        }
        row.update(decision(row))
        row["candles"] = self.get_candles(symbol, row)
        return row

    def get_candles(self, symbol: str, row: Optional[dict] = None, count: int = 80) -> List[dict]:
        row = row or self.get_row(symbol)
        if not row:
            return []

        low = row["day_low"]
        high = row["day_high"]
        price = row["price"]
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
        output[-1]["high"] = max(output[-1]["high"], price)
        output[-1]["low"] = min(output[-1]["low"], price)
        return output


class YFinanceProvider:
    name = "Yahoo Finance Live"

    def available_symbols(self) -> List[str]:
        return []

    def get_row(self, symbol: str) -> Optional[dict]:
        """
        Fetch live data with a strict timeout.

        yfinance/network calls can hang. This wrapper prevents the ATIS UI from
        freezing by giving the live provider only a few seconds before falling
        back.
        """
        from concurrent.futures import ThreadPoolExecutor, TimeoutError

        symbol = (symbol or "").strip().upper()
        if not symbol:
            return None

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._get_row_live_blocking, symbol)
                return future.result(timeout=4)
        except TimeoutError:
            return None
        except Exception:
            return None

    def _get_row_live_blocking(self, symbol: str) -> Optional[dict]:
        symbol = (symbol or "").strip().upper()
        if not symbol:
            return None

        try:
            import yfinance as yf
        except Exception:
            return None

        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="5d", interval="5m", prepost=False).dropna()
            if hist.empty:
                return None

            today = hist[hist.index.date == hist.index[-1].date()]
            if today.empty:
                today = hist.tail(78)

            price = float(hist.iloc[-1]["Close"])
            day_high = float(today["High"].max())
            day_low = float(today["Low"].min())
            vol = int(today["Volume"].sum())
            vwap = float((today["Close"] * today["Volume"]).sum() / today["Volume"].sum()) if today["Volume"].sum() else price
            ema9 = float(today["Close"].ewm(span=9, adjust=False).mean().iloc[-1])
            ema20 = float(today["Close"].ewm(span=20, adjust=False).mean().iloc[-1])

            daily = stock.history(period="5d", interval="1d")
            prev = float(daily["Close"].iloc[-2]) if daily is not None and len(daily) >= 2 else None
            chg = round(((price - prev) / prev) * 100, 2) if prev else 0.0

            avg = float(hist["Volume"].tail(312).mean())
            rvol = round(float(today["Volume"].mean()) / avg, 2) if avg else 1.0

            info = {}
            try:
                info = stock.get_info() or {}
            except Exception:
                info = {}

            name = info.get("shortName") or info.get("longName") or symbol
            row = {
                "ticker": symbol,
                "name": name,
                "price": round(price, 2),
                "day_high": round(day_high, 2),
                "day_low": round(day_low, 2),
                "vwap": round(vwap, 2),
                "ema9": round(ema9, 2),
                "ema20": round(ema20, 2),
                "change_pct": chg,
                "relative_volume": rvol,
                "volume": vol,
                "news": False,
                "new_intraday_high": price >= day_high * 0.999,
                "above_vwap": price > vwap if vwap else False,
                "above_9ema": price > ema9 if ema9 else False,
                "above_20ema": price > ema20 if ema20 else False,
                "data_source": self.name,
                "updated": datetime.now().strftime("%I:%M:%S %p"),
            }
            row.update(decision(row))
            row["candles"] = self._candles_from_history(hist.tail(80), row)
            return row
        except Exception:
            return None

    def _candles_from_history(self, hist, row: dict) -> List[dict]:
        candles = []
        try:
            for _, item in hist.iterrows():
                candles.append({
                    "open": round(float(item["Open"]), 2),
                    "high": round(float(item["High"]), 2),
                    "low": round(float(item["Low"]), 2),
                    "close": round(float(item["Close"]), 2),
                    "volume": int(item["Volume"]),
                })
        except Exception:
            return FallbackProvider().get_candles(row["ticker"], row)
        return candles or FallbackProvider().get_candles(row["ticker"], row)


class MarketDataEngine:
    def __init__(self):
        self.mode = "fallback"
        self.fallback = FallbackProvider()
        self.live = YFinanceProvider()
        self.last_error = ""

    def set_mode(self, mode: str) -> None:
        mode = (mode or "fallback").strip().lower()
        self.mode = "live" if mode == "live" else "fallback"

    def get_mode(self) -> str:
        return self.mode

    def get_row(self, symbol: str) -> Tuple[Optional[dict], str]:
        symbol = (symbol or "").strip().upper()
        if not symbol:
            return None, "Enter a ticker."

        if self.mode == "live":
            row = self.live.get_row(symbol)
            if row:
                return row, ""
            self.last_error = f"Live data unavailable for {symbol}; using fallback if available."

        row = self.fallback.get_row(symbol)
        if row:
            if self.mode == "live" and self.last_error:
                row["data_source"] = f"Fallback after live miss"
            return row, ""

        return None, f"{symbol} not found. Available fallback symbols: {', '.join(self.fallback.available_symbols())}"

    def all_rows(self) -> List[dict]:
        """
        Build the table/watchlist quickly.

        Important:
        Do NOT bulk-fetch live data here. Doing that from the UI thread can freeze
        the desktop app when the user selects Live mode. The watchlist remains
        fallback-fast, while individual searched symbols may use live data safely.
        """
        rows = []
        for symbol in self.fallback.available_symbols():
            row = self.fallback.get_row(symbol)
            if row:
                rows.append(row)
        rows.sort(key=lambda item: item["score"], reverse=True)
        for idx, row in enumerate(rows, 1):
            row["rank"] = idx
        return rows

    def diagnostics(self) -> str:
        return f"""MARKET DATA ENGINE

Mode:
{self.mode.upper()}

Live provider:
Yahoo Finance via yfinance

Fallback provider:
Stable built-in ATIS fallback data

Fallback symbols:
{', '.join(self.fallback.available_symbols())}

Last live status:
{self.last_error or 'No live errors recorded.'}

Notes:
- Fallback mode is safest and fastest.
- Live mode requires the yfinance package and internet access.
- If live mode fails, ATIS falls back safely when the symbol exists in fallback data.
"""


market_data_engine = MarketDataEngine()
