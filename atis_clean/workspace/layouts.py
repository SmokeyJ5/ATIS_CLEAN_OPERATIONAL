from __future__ import annotations

LAYOUTS = {
    "2 Charts": 2,
    "4 Charts": 4,
    "6 Charts": 6,
}

DEFAULT_SYMBOLS = ["TSLA", "NVDA", "SLV", "HL", "SPY", "QQQ"]

DEFAULT_TIMEFRAMES = ["5m", "15m", "1h", "Daily", "5m", "15m"]


def layout_count(name: str) -> int:
    return LAYOUTS.get(name, 4)


def layout_names():
    return list(LAYOUTS.keys())


def default_symbol(index: int) -> str:
    return DEFAULT_SYMBOLS[index % len(DEFAULT_SYMBOLS)]


def default_timeframe(index: int) -> str:
    return DEFAULT_TIMEFRAMES[index % len(DEFAULT_TIMEFRAMES)]
