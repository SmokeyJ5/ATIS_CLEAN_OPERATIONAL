import argparse
import os
import time

import pytest
from PySide6.QtWidgets import QApplication

from atis_clean.app import ATISClean
from atis_clean.market_data.provider import market_data_engine
from atis_clean.paper_trading.simulator import reset_account, buy, sell


def run_soak(duration_seconds: int = 10_800) -> dict:
    app = QApplication.instance() or QApplication([])
    market_data_engine.set_mode("fallback")
    reset_account()

    symbols = ["TSLA", "NVDA", "AAPL", "SPY", "QQQ", "SLV", "GLD", "HL", "AG", "CDE"]
    deadline = time.monotonic() + max(1, int(duration_seconds))

    startup_failures = 0
    symbol_failures = 0
    data_failures = 0
    trade_failures = 0
    cycles = 0

    while time.monotonic() < deadline:
        window = None
        try:
            window = ATISClean()
        except Exception:
            startup_failures += 1

        if window is not None:
            for symbol in symbols:
                try:
                    window.load_symbol(symbol)
                    if not window.selected or window.selected.get("ticker") != symbol:
                        symbol_failures += 1
                except Exception:
                    symbol_failures += 1
                app.processEvents()

            try:
                window.close()
                window.deleteLater()
            except Exception:
                pass

        row, _ = market_data_engine.get_row("TSLA")
        if not row:
            data_failures += 1
        else:
            try:
                b = buy("TSLA", 1, float(row["price"]))
                s = sell("TSLA", 1, float(row["price"]))
                if b.get("status") != "FILLED" or s.get("status") != "FILLED":
                    trade_failures += 1
            except Exception:
                trade_failures += 1

        cycles += 1
        app.processEvents()
        time.sleep(0.02)

    app.quit()
    return {
        "duration_seconds": int(duration_seconds),
        "cycles": cycles,
        "startup_failures": startup_failures,
        "symbol_failures": symbol_failures,
        "data_failures": data_failures,
        "trade_failures": trade_failures,
    }


@pytest.mark.skipif(os.environ.get("ATIS_ENABLE_SOAK") != "1", reason="Set ATIS_ENABLE_SOAK=1 to run endurance soak suite")
def test_endurance_soak_suite():
    duration = int(os.environ.get("ATIS_SOAK_SECONDS", "10800"))
    stats = run_soak(duration)
    assert stats["startup_failures"] == 0, stats
    assert stats["symbol_failures"] == 0, stats
    assert stats["data_failures"] == 0, stats
    assert stats["trade_failures"] == 0, stats


def main():
    parser = argparse.ArgumentParser(description="ATIS formal endurance soak suite")
    parser.add_argument("--hours", type=float, default=3.0, help="Soak duration in hours (default: 3.0)")
    parser.add_argument("--seconds", type=int, default=0, help="Explicit duration in seconds (overrides --hours)")
    args = parser.parse_args()

    duration_seconds = args.seconds if args.seconds > 0 else int(args.hours * 3600)
    stats = run_soak(duration_seconds)
    print(stats)

    if any(stats[key] > 0 for key in ("startup_failures", "symbol_failures", "data_failures", "trade_failures")):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
