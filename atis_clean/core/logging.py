from __future__ import annotations

from datetime import datetime
from pathlib import Path
import traceback

from atis_clean.core.paths import logs_root


def log_dir() -> Path:
    return logs_root()


def app_log_path() -> Path:
    return log_dir() / "atis_app.log"


def error_log_path() -> Path:
    return log_dir() / "atis_errors.log"


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")


def log_event(message: str) -> None:
    line = f"[{_timestamp()}] {message}\n"
    try:
        with app_log_path().open("a", encoding="utf-8") as handle:
            handle.write(line)
    except OSError:
        try:
            Path("logs").mkdir(parents=True, exist_ok=True)
            with app_log_path().open("a", encoding="utf-8") as handle:
                handle.write(line)
        except OSError:
            pass


def log_error(context: str, exc: BaseException) -> None:
    text = (
        f"\n[{_timestamp()}] ERROR: {context}\n"
        f"{type(exc).__name__}: {exc}\n"
        f"{traceback.format_exc()}\n"
    )
    try:
        with error_log_path().open("a", encoding="utf-8") as handle:
            handle.write(text)
    except OSError:
        try:
            Path("logs").mkdir(parents=True, exist_ok=True)
            with error_log_path().open("a", encoding="utf-8") as handle:
                handle.write(text)
        except OSError:
            pass
