# ATIS CLEAN OPERATIONAL v4.0.1 — Watchlist Rank Hotfix

## Fixed
- Loading a watchlist no longer crashes with `KeyError: 'rank'`.
- Live rows loaded from watchlists now receive rank values.
- Table updates now safely fall back to row order if rank is missing.

## Preserved
- One global search
- All-symbol live lookup
- v4 event bus foundation
- Watchlist persistence
- No real broker execution
