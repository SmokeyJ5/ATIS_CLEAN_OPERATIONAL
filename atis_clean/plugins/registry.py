from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List


@dataclass
class PluginInfo:
    name: str
    category: str
    status: str
    version: str
    description: str


class PluginRegistry:
    def __init__(self):
        self.plugins: Dict[str, PluginInfo] = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register("Fallback Market Data", "Market Data", "ACTIVE", "1.0", "Stable internal fallback quote/candle provider.")
        self.register("Yahoo Finance Adapter", "Market Data", "OPTIONAL", "0.1", "Optional yfinance live quote adapter with timeout fallback.")
        self.register("Paper Trading Simulator", "Broker", "ACTIVE", "1.0", "Simulated order execution only; no real broker orders.")
        self.register("Broker Adapter Interface", "Broker", "STUB", "0.1", "Placeholder interface for future broker API integration.")
        self.register("News Adapter Interface", "News", "STUB", "0.1", "Placeholder interface for future news/API integrations.")
        self.register("Economic Calendar Adapter", "Macro", "STUB", "0.1", "Placeholder interface for future economic calendar providers.")
        self.register("Polygon.io Adapter", "Market Data", "FUTURE", "0.1", "Future provider slot for professional real-time market data.")
        self.register("Finnhub Adapter", "Market Data", "FUTURE", "0.1", "Future provider slot for fundamentals, news, and estimates.")
        self.register("Alpha Vantage Adapter", "Market Data", "FUTURE", "0.1", "Future provider slot for historical/technical data.")
        self.register("Twelve Data Adapter", "Market Data", "FUTURE", "0.1", "Future provider slot for multi-asset time series.")

    def register(self, name: str, category: str, status: str, version: str, description: str):
        self.plugins[name] = PluginInfo(name, category, status, version, description)

    def list_plugins(self) -> List[PluginInfo]:
        return sorted(self.plugins.values(), key=lambda p: (p.category, p.name))

    def diagnostics(self) -> dict:
        items = self.list_plugins()
        active = [p for p in items if p.status == "ACTIVE"]
        optional = [p for p in items if p.status == "OPTIONAL"]
        stubs = [p for p in items if p.status == "STUB"]
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
            "total": len(items),
            "active": len(active),
            "optional": len(optional),
            "stubs": len(stubs),
            "plugins": items,
        }


registry = PluginRegistry()


def plugin_report() -> str:
    d = registry.diagnostics()
    lines = [
        "ATIS PLUGIN / API FRAMEWORK",
        "",
        f"Timestamp: {d['timestamp']}",
        f"Total plugins/adapters: {d['total']}",
        f"Active: {d['active']}",
        f"Optional: {d['optional']}",
        f"Future stubs: {d['stubs']}",
        "",
        "Registered Adapters:",
    ]
    for p in d["plugins"]:
        lines.append(f"- {p.status} | {p.category} | {p.name} v{p.version}")
        lines.append(f"  {p.description}")
    lines.append("")
    lines.append("Safety:")
    lines.append("Broker interfaces are stubs only. ATIS does not place real money trades.")
    return "\n".join(lines)
