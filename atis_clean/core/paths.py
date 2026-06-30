from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    """Return the application root directory.

    In a frozen executable, use the executable location. Otherwise use the
    repository root relative to this module.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def config_root() -> Path:
    path = app_root() / "config"
    path.mkdir(parents=True, exist_ok=True)
    return path


def data_root() -> Path:
    path = app_root() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_root() -> Path:
    path = app_root() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def release_manifest_path() -> Path:
    return app_root() / "RELEASE_MANIFEST.json"


def build_info_path() -> Path:
    return app_root() / "BUILD_INFO.txt"
