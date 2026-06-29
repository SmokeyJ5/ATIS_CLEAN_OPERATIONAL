from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from atis_clean.core.events import event_bus, SYMBOL_SELECTED, WATCHLIST_CHANGED
from atis_clean.watchlists.manager import ensure_default_watchlists, list_watchlists, load_watchlist, add_symbol, remove_symbol
from atis_clean.workstation.architecture import architecture_report

def main():
    ensure_default_watchlists()
    names = list_watchlists()
    assert "Favorites" in names
    add_symbol("Favorites", "MSFT")
    assert "MSFT" in load_watchlist("Favorites")
    remove_symbol("Favorites", "MSFT")
    event_bus.publish(SYMBOL_SELECTED, symbol="TSLA")
    event_bus.publish(WATCHLIST_CHANGED, watchlist="Favorites")
    assert event_bus.history
    assert architecture_report()
    print("ATIS v4.0 architecture smoke PASS")

if __name__ == "__main__":
    main()
