from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from atis_clean.market_data.provider import market_data_engine
from atis_clean.decision.engine import build_ai_decision
from atis_clean.scanner.engine import scan_rows
from atis_clean.alerts.engine import evaluate_alerts
from atis_clean.strategy_lab.backtester import backtest
from atis_clean.paper_trading.simulator import reset_account, buy, sell
from atis_clean.diagnostics.health import system_health


def main():
    rows = market_data_engine.all_rows()
    assert rows, "market rows missing"

    for symbol in ["TSLA", "NVDA", "SLV", "HL"]:
        row, err = market_data_engine.get_row(symbol)
        assert row, err
        ai = build_ai_decision(row)
        assert 0 <= ai["ai_score"] <= 100
        assert evaluate_alerts(row)
        result = backtest(row)
        assert "report" in result

    assert scan_rows(rows, preset="All")

    reset_account()
    assert buy("TSLA", 1, 100)["status"] == "FILLED"
    assert sell("TSLA", 1, 101)["status"] == "FILLED"

    health = system_health()
    assert health["checks"]

    print("ATIS regression smoke PASS")


if __name__ == "__main__":
    main()
