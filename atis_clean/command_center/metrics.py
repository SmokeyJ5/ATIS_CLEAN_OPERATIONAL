from __future__ import annotations

from typing import List


def top_opportunities(rows: List[dict], limit: int = 8) -> List[dict]:
    ranked = sorted(rows or [], key=lambda r: (r.get("ai_decision", {}).get("ai_score", r.get("score", 0)), r.get("relative_volume", 0)), reverse=True)
    return ranked[:limit]


def active_alert_count(alert_rows: List[dict]) -> int:
    return len([a for a in alert_rows if a.get("status") in {"ACTIVE", "WARNING"}])


def command_center_report(rows: List[dict], selected: dict | None = None) -> str:
    selected = selected or (rows[0] if rows else {})
    top = top_opportunities(rows, 5)
    lines = [
        "ATIS INSTITUTIONAL COMMAND CENTER",
        "",
        f"Selected Symbol: {selected.get('ticker', 'N/A')}",
        f"Selected Price: ${selected.get('price', 'N/A')}",
        f"Selected Score: {selected.get('score', 'N/A')}/100",
        f"Selected Action: {selected.get('ai_decision', {}).get('ai_action', selected.get('action', 'N/A'))}",
        "",
        "Top AI Opportunities:",
    ]
    for i, row in enumerate(top, 1):
        ai = row.get("ai_decision", {})
        lines.append(f"{i}. {row.get('ticker')} | AI {ai.get('ai_score', row.get('score'))}/100 | {ai.get('ai_action', row.get('action'))} | RVOL {row.get('relative_volume')}x")
    lines.append("")
    lines.append("Command Center Guidance:")
    lines.append("Use this dashboard as the launch screen: verify market context, scan leaders, review alerts, then open charts or Strategy Lab.")
    return "\n".join(lines)


def heatmap_rows(rows: List[dict], limit: int = 12) -> List[dict]:
    return sorted(rows or [], key=lambda r: r.get("score", 0), reverse=True)[:limit]
