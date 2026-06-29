from __future__ import annotations

from datetime import datetime
from pathlib import Path
import traceback


def log_dir() -> Path:
    path = Path.cwd() / "logs"
    path.mkdir(exist_ok=True)
    return path


def app_log_path() -> Path:
    return log_dir() / "atis_app.log"


def error_log_path() -> Path:
    return log_dir() / "atis_errors.log"


def log_event(message: str) -> None:
    line = f"[{datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}] {message}\n"
    app_log_path().open("a", encoding="utf-8").write(line)


def log_error(context: str, exc: BaseException) -> None:
    text = (
        f"\n[{datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}] ERROR: {context}\n"
        f"{type(exc).__name__}: {exc}\n"
        f"{traceback.format_exc()}\n"
    )
    error_log_path().open("a", encoding="utf-8").write(text)
