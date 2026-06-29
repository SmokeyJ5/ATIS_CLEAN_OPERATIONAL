from pathlib import Path
import sys
import py_compile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def compile_all():
    errors = []
    for py in ROOT.rglob("*.py"):
        if "__pycache__" in py.parts or ".git" in py.parts:
            continue
        try:
            py_compile.compile(str(py), doraise=True)
        except Exception as exc:
            errors.append((str(py.relative_to(ROOT)), repr(exc)))
    assert not errors, errors

def main():
    compile_all()

    from atis_clean.market_data.provider import market_data_engine
    from atis_clean.decision.engine import build_ai_decision
    from atis_clean.scanner.engine import scan_rows
    from atis_clean.alerts.engine import evaluate_alerts
    from atis_clean.strategy_lab.backtester import backtest, strategy_names
    from atis_clean.paper_trading.simulator import reset_account, buy, sell, account_summary
    from atis_clean.diagnostics.health import system_health
    from atis_clean.plugins.broker import disabled_live_broker, BrokerOrder
    from atis_clean.release.manifest import manifest_text
    from atis_clean.core.settings import settings_report

    rows = market_data_engine.all_rows()
    assert rows, "No market rows loaded"
    assert scan_rows(rows, preset="All"), "Scanner returned no rows"

    for symbol in ["TSLA", "NVDA", "SLV", "HL", "AG", "CDE", "SPY", "QQQ"]:
        row, err = market_data_engine.get_row(symbol)
        assert row, err
        ai = build_ai_decision(row)
        assert 0 <= ai["ai_score"] <= 100
        assert evaluate_alerts(row)
        for strategy in strategy_names():
            result = backtest(row, strategy=strategy)
            assert "report" in result

    reset_account()
    assert buy("TSLA", 10, 100)["status"] == "FILLED"
    assert sell("TSLA", 10, 101)["status"] == "FILLED"
    summary = account_summary(lambda t: 101)
    assert summary["cash"] > 0

    broker_result = disabled_live_broker.submit_order(BrokerOrder("TSLA", "BUY", 1, "MARKET"))
    assert broker_result["status"] == "REJECTED"

    assert system_health()["checks"]
    assert manifest_text()
    assert settings_report()

    app_py = (ROOT / "atis_clean" / "app.py").read_text(encoding="utf-8", errors="ignore")
    assert app_py.count("QLineEdit(") == 1, "Expected exactly one global search box"

    print("ATIS v3.0 Stable Certification PASS")

if __name__ == "__main__":
    main()
