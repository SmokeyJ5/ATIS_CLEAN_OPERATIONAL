from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
import traceback

from atis_clean.core.paths import logs_root


MAX_LOG_BYTES = 2 * 1024 * 1024
LOG_BACKUP_COUNT = 5


def log_dir() -> Path:
    return logs_root()


def app_log_path() -> Path:
    return log_dir() / "atis_app.log"


def error_log_path() -> Path:
    return log_dir() / "atis_errors.log"


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")


def _emit_stderr(message: str) -> None:
    try:
        sys.stderr.write(f"[ATIS logging] {message}\n")
    except Exception:
        pass


def _rotate_if_needed(path: Path) -> None:
    try:
        if not path.exists() or path.stat().st_size < MAX_LOG_BYTES:
            return
    except OSError:
        return

    oldest = path.with_name(f"{path.name}.{LOG_BACKUP_COUNT}")
    try:
        oldest.unlink(missing_ok=True)
    except OSError as exc:
        _emit_stderr(f"Failed to remove oldest log backup {oldest}: {exc}")

    for idx in range(LOG_BACKUP_COUNT - 1, 0, -1):
        source = path.with_name(f"{path.name}.{idx}")
        target = path.with_name(f"{path.name}.{idx + 1}")
        if source.exists():
            try:
                source.replace(target)
            except OSError as exc:
                _emit_stderr(f"Failed to rotate {source} -> {target}: {exc}")

    first_backup = path.with_name(f"{path.name}.1")
    try:
        if path.exists():
            path.replace(first_backup)
    except OSError as exc:
        _emit_stderr(f"Failed to rotate active log {path} -> {first_backup}: {exc}")


def log_event(message: str) -> None:
    line = f"[{_timestamp()}] {message}\n"
    try:
        _rotate_if_needed(app_log_path())
        with app_log_path().open("a", encoding="utf-8") as handle:
            handle.write(line)
    except OSError:
        try:
            Path("logs").mkdir(parents=True, exist_ok=True)
            _rotate_if_needed(app_log_path())
            with app_log_path().open("a", encoding="utf-8") as handle:
                handle.write(line)
        except OSError as exc:
            _emit_stderr(f"Unable to write app log: {exc}")


def log_error(context: str, exc: BaseException) -> None:
    text = (
        f"\n[{_timestamp()}] ERROR: {context}\n"
        f"{type(exc).__name__}: {exc}\n"
        f"{traceback.format_exc()}\n"
    )
    try:
        _rotate_if_needed(error_log_path())
        with error_log_path().open("a", encoding="utf-8") as handle:
            handle.write(text)
    except OSError:
        try:
            Path("logs").mkdir(parents=True, exist_ok=True)
            _rotate_if_needed(error_log_path())
            with error_log_path().open("a", encoding="utf-8") as handle:
                handle.write(text)
        except OSError as exc2:
            _emit_stderr(f"Unable to write error log for {context}: {exc2}")
