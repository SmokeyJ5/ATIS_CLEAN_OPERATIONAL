from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Optional


@dataclass
class ProviderResult:
    symbol: str
    provider: str
    status: str
    data: dict | None
    error: str = ""


class MarketProvider(Protocol):
    name: str

    def get_row(self, symbol: str) -> Optional[dict]:
        ...

    def available_symbols(self) -> list[str]:
        ...


class ProviderRouter:
    """
    Foundation for multi-provider ATIS data.

    v3.1 keeps Yahoo/yfinance as the first live provider, but this router gives
    ATIS a place to add Polygon, Finnhub, Alpha Vantage, Twelve Data, etc.
    """

    def __init__(self):
        self.providers = []

    def register(self, provider):
        self.providers.append(provider)

    def list_providers(self):
        return [getattr(p, "name", p.__class__.__name__) for p in self.providers]

    def first_success(self, symbol: str) -> ProviderResult:
        last_error = ""
        for provider in self.providers:
            try:
                row = provider.get_row(symbol)
                if row:
                    return ProviderResult(symbol=symbol, provider=getattr(provider, "name", "Unknown"), status="OK", data=row)
            except (AttributeError, TypeError, ValueError, RuntimeError, OSError) as exc:
                last_error = str(exc)
        message = "No provider returned data."
        if last_error:
            message = f"{message} Last provider error: {last_error}"
        return ProviderResult(symbol=symbol, provider="None", status="MISS", data=None, error=message)
