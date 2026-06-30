from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json


VERSION = "v3.0.0-STABLE"
BUILD_NAME = "ATIS Clean Operational"
PHASE = "v3.0 Stable Certified Baseline"


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


from atis_clean.core.paths import release_manifest_path


def write_manifest_file() -> Path:
    path = release_manifest_path()
    path.write_text(json.dumps(manifest(), indent=2), encoding="utf-8")
    return path
