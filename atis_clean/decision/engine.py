from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


def clamp(value, low=0, high=100):
    return max(low, min(high, value))


def trend_signal(row: dict) -> dict:
    price = row.get("price", 0)
    ema9 = row.get("ema9", 0)
    ema20 = row.get("ema20", 0)
    vwap = row.get("vwap", 0)

    score = 0
    notes = []

    if price > vwap:
        score += 18
        notes.append("Price is above VWAP, showing intraday strength.")
    else:
        notes.append("Price is below VWAP, which weakens the setup.")

    if price > ema9:
        score += 14
        notes.append("Price is above the 9 EMA.")
    else:
        notes.append("Price is not above the 9 EMA.")

    if price > ema20:
        score += 14
        notes.append("Price is above the 20 EMA.")
    else:
        notes.append("Price is not above the 20 EMA.")

    if ema9 > ema20:
        score += 10
        notes.append("9 EMA is above 20 EMA, showing short-term trend alignment.")
    else:
        notes.append("9 EMA is not above 20 EMA yet.")

    return {"score": clamp(score, 0, 56), "notes": notes}


def momentum_signal(row: dict) -> dict:
    change = row.get("change_pct", 0)
    rvol = row.get("relative_volume", 0)
    score = 0
    notes = []

    if change >= 4:
        score += 18
        notes.append("Strong price momentum above 4%.")
    elif change >= 2:
        score += 14
        notes.append("Healthy price momentum above 2%.")
    elif change >= 1:
        score += 8
        notes.append("Mild positive momentum.")
    else:
        notes.append("Momentum is not strong yet.")

    if rvol >= 3:
        score += 18
        notes.append("Relative volume is above 3x.")
    elif rvol >= 2:
        score += 13
        notes.append("Relative volume is above 2x.")
    elif rvol >= 1:
        score += 5
        notes.append("Relative volume is acceptable but not explosive.")
    else:
        notes.append("Relative volume is weak.")

    if row.get("new_intraday_high"):
        score += 8
        notes.append("Symbol is making or testing a new intraday high.")

    if row.get("news"):
        score += 6
        notes.append("News/catalyst flag is active.")

    return {"score": clamp(score, 0, 50), "notes": notes}


def risk_signal(row: dict) -> dict:
    entry = row.get("entry", row.get("price", 0))
    stop = row.get("stop", 0)
    target1 = row.get("target1", 0)
    price = row.get("price", 0)

    risk = max(entry - stop, 0.01)
    reward = max(target1 - entry, 0.01)
    rr = reward / risk if risk else 0

    score = 0
    notes = []

    if rr >= 2:
        score += 20
        notes.append("Risk/reward is strong at 2:1 or better.")
    elif rr >= 1.3:
        score += 12
        notes.append("Risk/reward is acceptable.")
    else:
        notes.append("Risk/reward is not attractive yet.")

    extension = abs(price - row.get("vwap", price)) / row.get("vwap", price) * 100 if row.get("vwap") else 0
    if extension <= 2.5:
        score += 10
        notes.append("Price is not overly extended from VWAP.")
    elif extension <= 5:
        score += 4
        notes.append("Price is somewhat extended from VWAP.")
    else:
        notes.append("Price is extended from VWAP; avoid chasing.")

    return {"score": clamp(score, 0, 30), "notes": notes, "risk_reward": round(rr, 2), "extension_pct": round(extension, 2)}


def action_from_score(score: int, row: dict) -> str:
    if score >= 88:
        return "STRONG BUY WATCH"
    if score >= 76:
        return "BUY WATCH"
    if score >= 62:
        return "WATCH"
    if score >= 45:
        return "WAIT"
    return "AVOID"


def confidence_from_score(score: int) -> str:
    if score >= 85:
        return "High"
    if score >= 70:
        return "Medium-High"
    if score >= 55:
        return "Medium"
    if score >= 40:
        return "Low-Medium"
    return "Low"


def build_ai_decision(row: dict) -> dict:
    trend = trend_signal(row)
    momentum = momentum_signal(row)
    risk = risk_signal(row)

    raw = trend["score"] + momentum["score"] + risk["score"]
    score = int(clamp(round(raw / 136 * 100), 0, 100))

    action = action_from_score(score, row)
    confidence = confidence_from_score(score)

    decision = {
        "ai_score": score,
        "ai_action": action,
        "ai_confidence": confidence,
        "score": score,
        "action": action,
        "confidence": confidence,
    }

    entry = row.get("entry", row.get("price", 0))
    stop = row.get("stop", 0)
    target1 = row.get("target1", 0)
    target2 = row.get("target2", 0)

    positives = []
    warnings = []

    for note in trend["notes"] + momentum["notes"] + risk["notes"]:
        lower = note.lower()
        if "not" in lower or "weak" in lower or "below" in lower or "extended" in lower or "avoid" in lower:
            warnings.append(note)
        else:
            positives.append(note)

    decision.update({
        "entry_zone": f"${entry}",
        "stop_level": f"${stop}",
        "target_zone": f"${target1} - ${target2}",
        "risk_reward": risk["risk_reward"],
        "extension_pct": risk["extension_pct"],
        "trend_score": trend["score"],
        "momentum_score": momentum["score"],
        "risk_score": risk["score"],
        "positives": positives,
        "warnings": warnings,
        "summary": build_ai_summary(row, score, action, confidence, positives, warnings),
        "trade_plan": build_trade_plan(row, score, action, confidence, risk),
    })
    return decision


def build_ai_summary(row: dict, score: int, action: str, confidence: str, positives: List[str], warnings: List[str]) -> str:
    return f"""AI DECISION ENGINE — {row.get('ticker')}

Action:
{action}

AI Score:
{score}/100

Confidence:
{confidence}

Why ATIS sees this setup:
{chr(10).join(['✓ ' + x for x in positives[:8]]) if positives else 'No strong positives yet.'}

Warnings / What must improve:
{chr(10).join(['⚠ ' + x for x in warnings[:8]]) if warnings else 'No major warnings.'}

Plain-English Read:
ATIS is weighing trend alignment, momentum, volume, VWAP/EMA location, risk/reward, and extension from VWAP. The result is a structured decision score, not a guarantee.
"""


def build_trade_plan(row: dict, score: int, action: str, confidence: str, risk: dict) -> str:
    return f"""AI TRADE PLAN — {row.get('ticker')}

Recommended Action:
{action}

Confidence:
{confidence}

Entry Zone:
${row.get('entry')}

Stop:
${row.get('stop')}

Targets:
Target 1: ${row.get('target1')}
Target 2: ${row.get('target2')}

Risk / Reward:
{risk.get('risk_reward')}

VWAP Extension:
{risk.get('extension_pct')}%

Execution Guidance:
- Do not chase if price is extended.
- Prefer entries near VWAP / EMA support.
- If score is below 70, wait for more confirmation.
- If price loses VWAP, reduce confidence.
- Use this for paper-trading support, not financial advice.
"""
