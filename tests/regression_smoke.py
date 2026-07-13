import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from atis_clean.core.paths import atomic_write_text
from atis_clean.market_data.provider import FallbackProvider, market_data_engine
from atis_clean.decision.engine import build_ai_decision
from atis_clean.scanner.engine import scan_rows
from atis_clean.alerts.engine import evaluate_alerts
from atis_clean.strategy_lab.backtester import backtest, strategy_names
from atis_clean.paper_trading.simulator import reset_account, buy, sell
from atis_clean.diagnostics.health import system_health, health_report
from atis_clean.data import make_row
from atis_clean.watchlists.manager import ensure_default_watchlists, list_watchlists, load_watchlist, add_symbol, remove_symbol
from atis_clean.workspace.manager import ensure_default_workspaces, list_workspaces, load_workspace, save_workspace, delete_workspace


def test_fallback_candles_span_price():
    fallback_row = FallbackProvider().get_row("TSLA")
    stable_row = make_row("TSLA")
    assert fallback_row, "fallback row missing"
    assert stable_row, "stable row missing"
    last_candle = fallback_row["candles"][-1]
    assert last_candle["close"] == stable_row["price"]
    assert last_candle["high"] >= stable_row["price"]
    assert last_candle["low"] <= stable_row["price"]


def test_ai_decision_aliases_and_scanner_compatibility():
    row = make_row("TSLA")
    ai = build_ai_decision(row)
    assert ai["score"] == ai["ai_score"]
    assert ai["action"] == ai["ai_action"]

    ai_like_row = {
        "ticker": "TSLA",
        "ai_score": 100,
        "ai_action": "BUY WATCH",
        "change_pct": 5.0,
        "relative_volume": 3.0,
        "above_vwap": True,
        "above_9ema": True,
        "above_20ema": True,
        "news": False,
        "new_intraday_high": True,
    }
    matches = scan_rows([ai_like_row], preset="All")
    assert matches and matches[0]["scanner_preset"] == "All"


def test_paper_trading_rejects_bad_inputs():
    reset_account()
    assert buy("TSLA", 0, 100)["status"] == "REJECTED"
    assert buy("TSLA", 1, None)["status"] == "REJECTED"
    assert sell("TSLA", 0, 100)["status"] == "REJECTED"
    assert sell("TSLA", 1, None)["status"] == "REJECTED"


def test_atomic_write_preserves_existing_file_on_failure():
    with tempfile.TemporaryDirectory() as tmp_dir:
        target = Path(tmp_dir) / "state.json"
        target.write_text("old", encoding="utf-8")

        import atis_clean.core.paths as paths
        original_replace = paths.os.replace

        def failing_replace(source, destination):
            raise OSError("simulated replace failure")

        paths.os.replace = failing_replace
        try:
            try:
                atomic_write_text(target, "new")
                assert False, "expected atomic write to fail"
            except OSError:
                pass
        finally:
            paths.os.replace = original_replace

        assert target.read_text(encoding="utf-8") == "old"


def test_search_and_market_data_round_trip():
    row, err = market_data_engine.get_row("TSLA")
    assert row, err
    assert row["ticker"] == "TSLA"
    assert row["candles"]
    assert market_data_engine.get_mode() in {"fallback", "live"}


def test_watchlists_and_workspaces_persist():
    ensure_default_watchlists()
    ensure_default_workspaces()

    add_symbol("Favorites", "AAPL")
    assert "AAPL" in load_watchlist("Favorites")
    assert "Favorites" in list_watchlists()

    save_workspace("Regression Workspace", {"selected_symbol": "NVDA", "notes": "test"})
    loaded_workspace = load_workspace("Regression Workspace")
    assert loaded_workspace["selected_symbol"] == "NVDA"
    assert delete_workspace("Regression Workspace") is True


def test_diagnostics_and_strategy_lab_outputs():
    health = system_health()
    report = health_report()
    assert health["checks"]
    assert "ATIS PRODUCTION HEALTH CHECK" in report

    row, _ = market_data_engine.get_row("TSLA")
    for name in strategy_names():
        result = backtest(row, strategy=name)
        assert "report" in result
        assert result["strategy"] == name


def test_app_starts_when_a_tab_builder_fails():
    from PySide6.QtWidgets import QApplication
    from atis_clean.app import ATISClean

    app = QApplication.instance() or QApplication([])
    original_dashboard_tab = ATISClean.dashboard_tab

    def failing_dashboard_tab(self):
        raise RuntimeError("simulated tab failure")

    ATISClean.dashboard_tab = failing_dashboard_tab
    try:
        window = ATISClean()
        assert window.tabs.count() > 0
        assert window.centralWidget() is not None
    finally:
        ATISClean.dashboard_tab = original_dashboard_tab
        app.quit()


def main():
    test_fallback_candles_span_price()
    test_ai_decision_aliases_and_scanner_compatibility()
    test_paper_trading_rejects_bad_inputs()
    test_atomic_write_preserves_existing_file_on_failure()
    test_search_and_market_data_round_trip()
    test_watchlists_and_workspaces_persist()
    test_diagnostics_and_strategy_lab_outputs()
    test_app_starts_when_a_tab_builder_fails()
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
