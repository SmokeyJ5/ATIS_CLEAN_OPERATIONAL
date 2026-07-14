from __future__ import annotations

import os
import sys
from pathlib import Path

from atis_clean.core.logging import log_error
from atis_clean.core.paths import app_root


def _candidate_qt_roots() -> list[Path]:
    roots: list[Path] = []

    # Prefer the currently installed interpreter environment.
    try:
        import PySide6  # type: ignore

        roots.append(Path(PySide6.__file__).resolve().parent)
    except (ImportError, AttributeError, OSError) as exc:
        log_error("qt_runtime PySide6 discovery failed", exc)

    # Local source checkout fallback.
    roots.append(app_root() / ".venv" / "Lib" / "site-packages" / "PySide6")

    # Frozen/runtime bundle candidates.
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            roots.append(Path(meipass) / "PySide6")
            roots.append(Path(meipass))
        roots.append(Path(sys.executable).resolve().parent / "PySide6")

    # De-duplicate while preserving order.
    seen = set()
    ordered: list[Path] = []
    for root in roots:
        key = str(root)
        if key not in seen:
            seen.add(key)
            ordered.append(root)
    return ordered


def configure_qt_runtime() -> Path:
    """Configure Qt plugin/font lookup across source and frozen Windows runtimes."""
    selected_fonts = app_root() / "fonts"
    for qt_root in _candidate_qt_roots():
        plugins_dir = qt_root / "plugins"
        fonts_dir = qt_root / "lib" / "fonts"

        if plugins_dir.exists():
            existing = [p for p in os.environ.get("QT_PLUGIN_PATH", "").split(os.pathsep) if p]
            plugin_path = str(plugins_dir)
            if plugin_path not in existing:
                os.environ["QT_PLUGIN_PATH"] = os.pathsep.join(existing + [plugin_path])

        if fonts_dir.exists():
            os.environ.setdefault("QT_QPA_FONTDIR", str(fonts_dir))
            selected_fonts = fonts_dir

        if plugins_dir.exists() and fonts_dir.exists():
            break

    return selected_fonts
