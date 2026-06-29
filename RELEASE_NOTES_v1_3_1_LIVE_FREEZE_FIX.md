# ATIS CLEAN OPERATIONAL v1.3.1 — Live Mode Freeze Fix

## Fixed
- Selecting Live mode no longer bulk-fetches every ticker.
- Watchlist remains fast using fallback data.
- Live lookup uses timeout protection.
- If live data is slow or unavailable, ATIS falls back safely.
- UI should remain responsive when switching Fallback / Live.

## How to test
1. Open ATIS.
2. Switch Data selector from Fallback to Live.
3. App should not freeze.
4. Type TSLA and press Enter.
5. If live is slow/unavailable, it should safely use fallback.
