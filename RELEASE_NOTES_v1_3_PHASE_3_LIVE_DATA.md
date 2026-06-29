# ATIS CLEAN OPERATIONAL v1.3 — Phase 3 Live Data Architecture

## Added
- MarketDataEngine
- FallbackProvider
- Optional YFinanceProvider
- Data mode selector: Fallback / Live
- Provider diagnostics in Data Provider tab
- Safe fallback behavior if live data is unavailable
- Search now routes through MarketDataEngine

## Preserved
- One top search bar
- Search controls every tab
- Fallback mode remains stable and fast

## Notes
Live mode requires yfinance, pandas, and internet access. If live mode cannot fetch a ticker, ATIS safely falls back when possible.
