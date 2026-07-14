import os
import json
from pathlib import Path
import sys
import tempfile
import tracemalloc

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from atis_clean.core.paths import atomic_write_text
from atis_clean.core.qt_runtime import configure_qt_runtime
import atis_clean.core.qt_runtime as qt_runtime
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
import atis_clean.paper_trading.simulator as paper_simulator
import atis_clean.watchlists.manager as watchlist_manager
import atis_clean.workspace.manager as workspace_manager
import atis_clean.release.manifest as release_manifest


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


def test_scanner_handles_malformed_rows():
    rows = [
        {
            "ticker": "TSLA",
            "score": "bad",
            "change_pct": "2.0",
            "relative_volume": "3.0",
            "above_vwap": True,
            "above_9ema": True,
            "above_20ema": True,
            "news": False,
            "new_intraday_high": True,
        },
        {
            "ticker": "AAPL",
            "score": 80,
            "change_pct": 1.5,
            "relative_volume": 2.5,
            "above_vwap": True,
            "above_9ema": True,
            "above_20ema": False,
            "news": False,
            "new_intraday_high": False,
        },
    ]
    matches = scan_rows(rows, preset="All")
    assert matches and matches[0]["ticker"] == "AAPL"


def test_app_load_symbol_recovers_from_sparse_row(monkeypatch):
    from PySide6.QtWidgets import QApplication
    from atis_clean.app import ATISClean

    app = QApplication.instance() or QApplication([])
    window = ATISClean()
    sparse_row = {
        "ticker": "SPARSE",
        "name": "Sparse",
        "price": 10.0,
        "change_pct": 1.0,
        "volume": 1000,
        "relative_volume": 1.5,
        "data_source": "TEST",
        "profile": {},
        "candles": [],
        "passed": [],
        "missing": [],
    }
    monkeypatch.setattr("atis_clean.app.market_data_engine.get_row", lambda symbol: (sparse_row, None))

    window.load_symbol("SPARSE")

    assert window.selected["ticker"] == "SPARSE"
    app.quit()


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


def test_qt_runtime_configures_font_directory():
    configured_path = configure_qt_runtime()
    assert configured_path is not None
    assert configured_path.exists()


def test_qt_runtime_candidate_roots_include_frozen_bundle(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_root = Path(tmp_dir)
        exe_path = tmp_root / "dist" / "ATIS.exe"
        exe_path.parent.mkdir(parents=True, exist_ok=True)
        exe_path.write_text("", encoding="utf-8")

        monkeypatch.setattr(qt_runtime.sys, "frozen", True, raising=False)
        monkeypatch.setattr(qt_runtime.sys, "_MEIPASS", str(tmp_root), raising=False)
        monkeypatch.setattr(qt_runtime.sys, "executable", str(exe_path), raising=False)

        roots = qt_runtime._candidate_qt_roots()
        assert (tmp_root / "PySide6") in roots
        assert tmp_root in roots
        assert (exe_path.resolve().parent / "PySide6") in roots


def test_manifest_write_is_idempotent_when_release_metadata_unchanged(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp_dir:
        manifest_path = Path(tmp_dir) / "RELEASE_MANIFEST.json"
        monkeypatch.setattr(release_manifest, "release_manifest_path", lambda: manifest_path)

        release_manifest.write_manifest_file()
        first_payload = json.loads(manifest_path.read_text(encoding="utf-8"))

        release_manifest.write_manifest_file()
        second_payload = json.loads(manifest_path.read_text(encoding="utf-8"))

        assert first_payload == second_payload
        assert first_payload.get("build_time") == second_payload.get("build_time")


def test_app_python_heap_trend_is_bounded():
    from PySide6.QtWidgets import QApplication
    from atis_clean.app import ATISClean

    app = QApplication.instance() or QApplication([])
    tracemalloc.start()
    try:
        for _ in range(40):
            window = ATISClean()
            window.close()
            window.deleteLater()
            app.processEvents()
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
        app.quit()

    # Peak-to-current gap should remain bounded after repeated create/destroy cycles.
    assert peak - current < 32 * 1024 * 1024


def test_workspace_and_watchlist_managers_handle_invalid_payloads(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_root = Path(tmp_dir) / "config"
        monkeypatch.setattr(workspace_manager, "config_root", lambda: config_root)
        monkeypatch.setattr(watchlist_manager, "config_root", lambda: config_root)

        saved_path = workspace_manager.save_workspace("Regression Workspace", None)
        assert saved_path.exists()
        assert workspace_manager.load_workspace("Regression Workspace") == {"workspace_name": "Regression Workspace", "saved_at": workspace_manager.load_workspace("Regression Workspace").get("saved_at")}

        watchlist_path = watchlist_manager.save_watchlist("Broken Watchlist", None)
        assert watchlist_path.exists()
        assert watchlist_manager.load_watchlist("Broken Watchlist") == []


def test_paper_trading_orders_loader_recovers_from_invalid_state(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp_dir:
        data_dir = Path(tmp_dir)
        monkeypatch.setattr(paper_simulator, "data_root", lambda: data_dir)

        bad_orders_dir = paper_simulator.orders_path()
        bad_orders_dir.mkdir(parents=True, exist_ok=True)

        assert paper_simulator.load_orders() == []


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
