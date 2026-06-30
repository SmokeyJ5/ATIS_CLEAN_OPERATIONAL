from __future__ import annotations

from datetime import datetime
import traceback

from pathlib import Path

from atis_clean.core.paths import logs_root


def log_dir() -> Path:
    return logs_root()


def app_log_path() -> Path:
    return log_dir() / "atis_app.log"


def error_log_path() -> Path:
    return log_dir() / "atis_errors.log"


def log_event(message: str) -> None:
    line = f"[{datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}] {message}\n"
    try:
        app_log_path().open("a", encoding="utf-8").write(line)
    except Exception:
        pass


def log_error(context: str, exc: BaseException) -> None:
    text = (
        f"\n[{datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}] ERROR: {context}\n"
        f"{type(exc).__name__}: {exc}\n"
        f"{traceback.format_exc()}\n"
    )
    try:
        error_log_path().open("a", encoding="utf-8").write(text)
    except Exception:
        pass
