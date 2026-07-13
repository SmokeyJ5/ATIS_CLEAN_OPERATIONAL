from __future__ import annotations

import os
from pathlib import Path

from atis_clean.core.paths import app_root


def configure_qt_runtime() -> Path:
    """Ensure Qt can resolve its bundled font directory in a local source checkout."""
    qt_root = app_root() / ".venv" / "Lib" / "site-packages" / "PySide6"
    fonts_dir = qt_root / "lib" / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)

    qt_plugin_path = str(qt_root / "plugins")
    if qt_plugin_path not in os.environ.get("QT_PLUGIN_PATH", ""):
        os.environ["QT_PLUGIN_PATH"] = os.pathsep.join(filter(None, [os.environ.get("QT_PLUGIN_PATH", ""), qt_plugin_path]))

    return fonts_dir
