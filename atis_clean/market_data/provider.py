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


from atis_clean.core.logging import log_error


class YFinanceProvider:
    name = "Yahoo Finance Live"

    def __init__(self):
        self.last_error = ""

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
            self.last_error = "No symbol provided for live lookup."
            return None

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._get_row_live_blocking, symbol)
                row = future.result(timeout=4)
                if row is None:
                    self.last_error = self.last_error or f"Live lookup for {symbol} returned no data."
                return row
        except TimeoutError:
            self.last_error = f"Live lookup for {symbol} timed out after 4 seconds."
            log_error("YFinanceProvider.get_row timeout", TimeoutError(f"{symbol} timed out"))
            return None
        except Exception as exc:
            self.last_error = f"Live lookup error for {symbol}: {exc}"
            log_error("YFinanceProvider.get_row", exc)
            return None

    def _get_row_live_blocking(self, symbol: str) -> Optional[dict]:
        symbol = (symbol or "").strip().upper()
        if not symbol:
            return None

        try:
            import yfinance as yf
        except Exception as exc:
            self.last_error = (
                "yfinance package is unavailable or failed to import. "
                "Install yfinance and retry."
            )
            log_error("YFinanceProvider._get_row_live_blocking import yfinance", exc)
            return None

        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="5d", interval="5m", prepost=False)
            if hist is None or hist.empty:
                self.last_error = f"yfinance returned no historical data for {symbol}."
                return None
            hist = hist.dropna()

            if hist.empty:
                self.last_error = f"yfinance returned only empty historical rows for {symbol}."
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
            sma50 = float(hist["Close"].rolling(50).mean().dropna().iloc[-1]) if len(hist) >= 50 else price
            sma200 = float(hist["Close"].rolling(200).mean().dropna().iloc[-1]) if len(hist) >= 200 else price

            delta = hist["Close"].diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = gain / loss.replace(0, 1)
            rsi14 = float((100 - (100 / (1 + rs))).dropna().iloc[-1]) if len(hist) >= 20 else 50.0

            ema12 = hist["Close"].ewm(span=12, adjust=False).mean()
            ema26 = hist["Close"].ewm(span=26, adjust=False).mean()
            macd_line = ema12 - ema26
            macd_signal = macd_line.ewm(span=9, adjust=False).mean()
            macd = float(macd_line.iloc[-1]) if len(macd_line) else 0.0
            macd_sig = float(macd_signal.iloc[-1]) if len(macd_signal) else 0.0

            tr1 = hist["High"] - hist["Low"]
            tr2 = (hist["High"] - hist["Close"].shift()).abs()
            tr3 = (hist["Low"] - hist["Close"].shift()).abs()
            atr14 = float(__import__("pandas").concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(14).mean().dropna().iloc[-1]) if len(hist) >= 20 else max(day_high - day_low, 0.01)

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

            # Company profile / explorer metadata.
            name = info.get("shortName") or info.get("longName") or symbol

            # yfinance sometimes returns news as list[dict]. Keep this safe.
            news_items = []
            try:
                raw_news = stock.news or []
                for item in raw_news[:8]:
                    content = item.get("content", item) if isinstance(item, dict) else {}
                    title = (
                        content.get("title")
                        or item.get("title", "")
                        if isinstance(item, dict)
                        else ""
                    )
                    publisher = (
                        content.get("provider", {}).get("displayName")
                        if isinstance(content.get("provider", {}), dict)
                        else item.get("publisher", "")
                    )
                    link = content.get("canonicalUrl", {}).get("url") if isinstance(content.get("canonicalUrl", {}), dict) else item.get("link", "")
                    if title:
                        news_items.append({
                            "title": title,
                            "publisher": publisher or "News",
                            "link": link or "",
                        })
            except Exception as exc:
                self.last_error = f"News parsing failed for {symbol}: {exc}"
                log_error("YFinanceProvider._get_row_live_blocking news parsing", exc)
                news_items = []

            profile = {
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "exchange": info.get("exchange") or info.get("fullExchangeName") or "N/A",
                "quote_type": info.get("quoteType", "N/A"),
                "market_cap": info.get("marketCap", "N/A"),
                "previous_close": info.get("previousClose", "N/A"),
                "open": info.get("open", "N/A"),
                "fifty_two_week_low": info.get("fiftyTwoWeekLow", "N/A"),
                "fifty_two_week_high": info.get("fiftyTwoWeekHigh", "N/A"),
                "average_volume": info.get("averageVolume", "N/A"),
                "float_shares": info.get("floatShares", "N/A"),
                "shares_outstanding": info.get("sharesOutstanding", "N/A"),
                "beta": info.get("beta", "N/A"),
                "trailing_pe": info.get("trailingPE", "N/A"),
                "forward_pe": info.get("forwardPE", "N/A"),
                "dividend_yield": info.get("dividendYield", "N/A"),
                "earnings_date": str(info.get("earningsDate", "N/A")),
                "recommendation": info.get("recommendationKey", "N/A"),
                "target_mean_price": info.get("targetMeanPrice", "N/A"),
                "target_high_price": info.get("targetHighPrice", "N/A"),
                "target_low_price": info.get("targetLowPrice", "N/A"),
                "website": info.get("website", "N/A"),
                "business_summary": info.get("longBusinessSummary", "Live company summary unavailable."),
            }

            self.last_error = ""
            row = {
                "ticker": symbol,
                "name": name,
                "price": round(price, 2),
                "day_high": round(day_high, 2),
                "day_low": round(day_low, 2),
                "vwap": round(vwap, 2),
                "ema9": round(ema9, 2),
                "ema20": round(ema20, 2),
                "sma50": round(sma50, 2),
                "sma200": round(sma200, 2),
                "rsi14": round(rsi14, 2),
                "macd": round(macd, 4),
                "macd_signal": round(macd_sig, 4),
                "atr14": round(atr14, 2),
                "change_pct": chg,
                "relative_volume": rvol,
                "volume": vol,
                "news": bool(news_items),
                "news_items": news_items,
                "profile": profile,
                "live_info_available": bool(info),
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
        except Exception as exc:
            self.last_error = f"YFinance internal exception for {symbol}: {exc}"
            log_error("YFinanceProvider._get_row_live_blocking", exc)
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
        self.last_error = self.live.last_error

    def set_mode(self, mode: str) -> None:
        mode = (mode or "fallback").strip().lower()
        self.mode = "live" if mode == "live" else "fallback"

    def get_mode(self) -> str:
        return self.mode

    def get_row(self, symbol: str) -> Tuple[Optional[dict], str]:
        """
        Resolve any searched ticker.

        Behavior:
        - Built-in fallback symbols always work.
        - Live mode tries yfinance first.
        - If a symbol is not in fallback, ATIS also tries live lookup even when the
          selector is on Fallback. This allows the one global search bar to search
          any valid ticker instead of only the built-in fallback list.
        - Live requests remain timeout-protected inside YFinanceProvider.
        """
        symbol = (symbol or "").strip().upper()
        if not symbol:
            return None, "Enter a ticker."

        fallback_row = self.fallback.get_row(symbol)

        if self.mode == "live":
            row = self.live.get_row(symbol)
            self.last_error = self.live.last_error
            if row:
                return row, ""
            self.last_error = (
                self.last_error or f"Live data unavailable for {symbol}; using fallback if available."
            )
            if fallback_row:
                fallback_row["data_source"] = "Fallback after live miss"
                return fallback_row, ""
            return None, (
                f"{symbol} could not be loaded from live data. "
                "Check internet/yfinance or try again later."
            )

        # Fallback mode: use instant fallback rows first.
        if fallback_row:
            return fallback_row, ""

        # All-symbol support: unknown fallback tickers automatically try live.
        row = self.live.get_row(symbol)
        self.last_error = self.live.last_error
        if row:
            row["data_source"] = "Yahoo Finance Live Auto-Lookup"
            return row, ""

        return None, (
            f"{symbol} is not in fallback data and live lookup did not return data. "
            "Install/verify yfinance and internet access, or switch Data to Live and retry."
        )

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
