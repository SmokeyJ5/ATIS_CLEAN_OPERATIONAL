from __future__ import annotations

from datetime import datetime
import platform
import sys
from pathlib import Path


MODULES = [
    "market_data",
    "scanner",
    "decision",
    "portfolio",
    "journal",
    "alerts",
    "market_intelligence",
    "workspace",
    "paper_trading",
    "strategy_lab",
    "command_center",
    "plugins",
    "workstation",
    "watchlists",
    "release",
    "core",
]


def check_module(name: str) -> dict:
    try:
        __import__(f"atis_clean.{name}")
        return {"module": name, "status": "PASS", "message": "Import OK"}
    except Exception as exc:
        return {"module": name, "status": "FAIL", "message": f"{type(exc).__name__}: {exc}"}


from atis_clean.core.paths import app_root, build_info_path


def check_files() -> list[dict]:
    required = [
        "run_atis.py",
        "requirements.txt",
        "atis_clean/app.py",
        "atis_clean/data.py",
        "atis_clean/chart_widget.py",
    ]
    out = []
    root = app_root()
    for item in required:
        exists = (root / item).exists()
        out.append({"module": item, "status": "PASS" if exists else "FAIL", "message": "Found" if exists else "Missing"})
    return out


def system_health() -> dict:
    all_checks = [check_module(name) for name in MODULES] + check_files()
    failures = [x for x in all_checks if x["status"] != "PASS"]
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "checks": all_checks,
        "overall": "PASS" if not failures else "WARNING",
        "failures": failures,
    }


def health_report() -> str:
    h = system_health()
    lines = [
        "ATIS PRODUCTION HEALTH CHECK",
        "",
        f"Timestamp: {h['timestamp']}",
        f"Python: {h['python']}",
        f"Platform: {h['platform']}",
        f"Overall: {h['overall']}",
        "",
        "Module/File Checks:",
    ]
    for check in h["checks"]:
        lines.append(f"- {check['status']} | {check['module']} | {check['message']}")

    lines.append("")
    if h["failures"]:
        lines.append("Action Required:")
        for item in h["failures"]:
            lines.append(f"- Fix {item['module']}: {item['message']}")
    else:
        lines.append("All production health checks passed.")

    return "\n".join(lines)


def version_info() -> str:
    build = build_info_path()
    if build.exists():
        return build.read_text(encoding="utf-8", errors="ignore").strip()
    return "ATIS build info unavailable"
