# ATIS CLEAN OPERATIONAL v3.0.1 — All-Symbol Search Hotfix

## Fixed
- The global search bar is no longer limited to fallback symbols.
- If a symbol is not found in fallback data, ATIS automatically attempts live lookup.
- Live mode still tries live data first and safely falls back when available.
- Timeout protection remains in place to prevent freezes.

## Notes
To search all valid stocks, yfinance and internet access are required.
Fallback mode still includes built-in stable sample symbols for offline use.
