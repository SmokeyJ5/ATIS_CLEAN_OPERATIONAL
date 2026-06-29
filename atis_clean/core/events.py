from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Any


@dataclass
class Event:
    name: str
    payload: dict
    timestamp: str


class EventBus:
    """
    Lightweight in-process event bus.

    v4.0 foundation:
    - Ticker search can publish SYMBOL_SELECTED.
    - Future modules can subscribe without making app.py call every widget directly.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Event], None]]] = {}
        self.history: List[Event] = []

    def subscribe(self, event_name: str, callback: Callable[[Event], None]) -> None:
        self._subscribers.setdefault(event_name, [])
        if callback not in self._subscribers[event_name]:
            self._subscribers[event_name].append(callback)

    def publish(self, event_name: str, **payload: Any) -> Event:
        event = Event(
            name=event_name,
            payload=payload,
            timestamp=datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
        )
        self.history.append(event)
        self.history = self.history[-250:]

        for callback in list(self._subscribers.get(event_name, [])):
            try:
                callback(event)
            except Exception:
                # Event bus should never crash the workstation.
                pass
        return event

    def recent_report(self) -> str:
        lines = ["ATIS EVENT BUS", "", f"Events stored: {len(self.history)}", ""]
        for event in self.history[-20:]:
            lines.append(f"{event.timestamp} | {event.name} | {event.payload}")
        return "\n".join(lines)


event_bus = EventBus()
SYMBOL_SELECTED = "symbol.selected"
WORKSPACE_CHANGED = "workspace.changed"
WATCHLIST_CHANGED = "watchlist.changed"
