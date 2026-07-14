from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json


VERSION = "v4.0.1"
BUILD_NAME = "ATIS Clean Operational"
PHASE = "Watchlist Rank Hotfix"


def manifest() -> dict:
    return {
        "app": BUILD_NAME,
        "version": VERSION,
        "phase": PHASE,
        "build_time": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
        "core_features": [
            "Single global search",
            "Fallback/live market data architecture",
            "Professional scanner",
            "Professional chart engine",
            "AI decision engine",
            "Portfolio risk manager",
            "Trade journal analytics",
            "Alerts automation",
            "Market intelligence",
            "Multi-chart workspace",
            "Workspace manager",
            "Paper trading simulator",
            "Strategy lab",
            "Institutional command center",
            "Diagnostics",
            "Plugin/API framework",
        ],
        "safety": [
            "No real broker orders",
            "Live broker adapter disabled",
            "Paper trading only",
            "Fallback mode available",
        ],
    }


def _release_fingerprint() -> dict:
    """Fields that should trigger a manifest rewrite when changed."""
    m = manifest()
    return {
        "app": m["app"],
        "version": m["version"],
        "phase": m["phase"],
        "core_features": m["core_features"],
        "safety": m["safety"],
    }


def manifest_text() -> str:
    m = manifest()
    lines = [
        "ATIS RELEASE MANIFEST",
        "",
        f"Application: {m['app']}",
        f"Version: {m['version']}",
        f"Phase: {m['phase']}",
        f"Build Time: {m['build_time']}",
        "",
        "Core Features:",
    ]
    for item in m["core_features"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("Safety:")
    for item in m["safety"]:
        lines.append(f"- {item}")
    return "\n".join(lines)


from atis_clean.core.paths import atomic_write_text, release_manifest_path


def write_manifest_file() -> Path:
    path = release_manifest_path()

    existing: dict | None = None
    if path.exists():
        try:
            existing_payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(existing_payload, dict):
                existing = existing_payload
        except (OSError, json.JSONDecodeError, TypeError, ValueError, UnicodeDecodeError):
            existing = None

    current = manifest()
    if existing:
        fingerprint = _release_fingerprint()
        unchanged = all(existing.get(key) == fingerprint[key] for key in fingerprint)
        if unchanged and isinstance(existing.get("build_time"), str) and existing.get("build_time"):
            # Keep existing build_time and avoid dirtying the worktree on each startup.
            return path

    atomic_write_text(path, json.dumps(current, indent=2) + "\n", encoding="utf-8")
    return path
