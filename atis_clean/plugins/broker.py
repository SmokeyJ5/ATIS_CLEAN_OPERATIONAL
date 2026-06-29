from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class BrokerOrder:
    ticker: str
    side: str
    quantity: int
    order_type: str
    limit_price: float | None = None
    stop_price: float | None = None


class BrokerAdapter(Protocol):
    name: str

    def connect(self) -> bool:
        ...

    def account(self) -> dict:
        ...

    def positions(self) -> list[dict]:
        ...

    def submit_order(self, order: BrokerOrder) -> dict:
        ...


class DisabledLiveBrokerAdapter:
    name = "Disabled Live Broker Adapter"

    def connect(self) -> bool:
        return False

    def account(self) -> dict:
        return {"status": "disabled", "message": "Live broker integration is not enabled."}

    def positions(self) -> list[dict]:
        return []

    def submit_order(self, order: BrokerOrder) -> dict:
        return {
            "status": "REJECTED",
            "message": "Live broker orders are disabled. Use Paper Trading simulator only.",
            "order": order.__dict__,
        }


disabled_live_broker = DisabledLiveBrokerAdapter()
