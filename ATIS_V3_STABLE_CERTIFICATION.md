# ATIS v3.0 Stable Certification

## Certification Status
This build is the ATIS v3.0 Stable baseline package created from the user's uploaded current project.

## Automated Checks Completed
- Python compile check: PASS
- Backend regression smoke: PASS
- One global QLineEdit search check: PASS
- Required project files present: PASS
- Phase modules import through regression script: PASS

## Manual UI Checks To Run On Windows
Run:

```powershell
python run_atis.py
```

Then verify:
- Dashboard opens
- Trading / Chart opens
- Scanner opens
- AI Analyst opens
- Portfolio opens
- Journal opens
- Alerts opens
- Market Intelligence opens
- Workspace Manager opens
- Paper Trading opens
- Strategy Lab opens
- Diagnostics opens
- Integrations opens
- Release Candidate opens
- Multi-Chart opens

## Search Verification
Search these tickers:
TSLA, NVDA, AAPL, SPY, QQQ, SLV, GLD, HL, AG, CDE

For each, confirm:
- chart updates
- AI updates
- dashboard updates
- alerts update
- paper trading uses selected ticker
- strategy lab recognizes selected ticker

## Paper Trading Verification
- BUY 10 shares
- SELL 10 shares
- Verify account values update
- Verify no real broker order is sent

## Safety
ATIS v3.0 Stable is a decision-support and paper-trading platform. It is not an autopilot and does not send live broker orders.


## v3.0.1 All-Symbol Search Update
The search bar now attempts live lookup for tickers that are not in fallback data. This allows broader ticker search when internet/yfinance is available.


## v3.0.2 UI Layout Stability Update
The Command Center/Dashboard now uses a scrollable responsive layout to prevent lower panels from being hidden by the Windows taskbar or clipped on smaller display heights.
