# ATIS Installation

## Run from source

```powershell
cd ATIS_CLEAN_OPERATIONAL
pip install -r requirements.txt
python run_atis.py
```

## Regression test

```powershell
python tests\regression_smoke.py
```

## Notes

- Use Fallback mode first.
- Live mode requires internet and optional yfinance access.
- Paper Trading is simulated only.
- Broker integrations are disabled by default.
