# ATIS CLEAN OPERATIONAL v3.1 — Live Market Intelligence Workstation Foundation

## Added / Improved
- Richer live stock metadata from yfinance where available.
- Dashboard now displays a full market workstation report for searched tickers.
- Explorer now includes more fundamentals and technicals.
- Chart report now includes RSI, ATR, and MACD fields.
- Provider abstraction foundation added under `atis_clean/providers`.
- Integration registry now includes future provider slots:
  - Polygon.io
  - Finnhub
  - Alpha Vantage
  - Twelve Data

## Important
Live market details depend on:
- internet access
- yfinance installed
- Yahoo Finance supporting the searched ticker/field

## Preserved
- One global search bar.
- All-symbol lookup behavior.
- No real broker execution.
- Stable certification tests.
