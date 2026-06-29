# ATIS v3.0.0-rc1 Release Checklist

## Required checks
- [ ] App starts
- [ ] Dashboard opens
- [ ] Search TSLA
- [ ] Search SLV
- [ ] Scanner opens
- [ ] Chart updates
- [ ] AI Decision tab updates
- [ ] Portfolio Risk updates
- [ ] Journal opens
- [ ] Alerts opens
- [ ] Market Intelligence opens
- [ ] Workspace Manager opens
- [ ] Paper Trading buy/sell simulation works
- [ ] Strategy Lab backtest runs
- [ ] Diagnostics health check runs
- [ ] Integrations Broker Safety rejects live orders
- [ ] Regression smoke passes

## Regression command

```powershell
python tests\regression_smoke.py
```

## Safety
ATIS v3.0.0-rc1 does not send live broker orders. Paper trading is simulated only.
