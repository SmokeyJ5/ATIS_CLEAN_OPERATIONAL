# ATIS Installation

## Run from source

```powershell
cd ATIS_CLEAN_OPERATIONAL
pip install -r requirements.txt
python run_atis.py
```

## Regression test

```powershell
scripts\run_regression.ps1
```

## Formal endurance soak suite

Run a certification-grade soak pass (default 3 hours):

```powershell
scripts\run_soak.ps1
```

Short validation run example:

```powershell
scripts\run_soak.ps1 -Seconds 60
```

## Notes

- Use Fallback mode first.
- Live mode requires internet and optional yfinance access.
- Paper Trading is simulated only.
- Broker integrations are disabled by default.
