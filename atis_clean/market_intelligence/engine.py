from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Dict


def market_dashboard() -> dict:
    return {
        "regime": "Risk-On Watch",
        "market_health": 78,
        "sp500": {"ticker": "SPY", "trend": "Constructive", "score": 76},
        "nasdaq": {"ticker": "QQQ", "trend": "Leadership", "score": 82},
        "vix": {"value": 14.8, "signal": "Calm"},
        "dollar": {"ticker": "DXY", "signal": "Neutral to Soft"},
        "yields": {"signal": "Stable"},
        "breadth": {"signal": "Positive but selective"},
        "updated": datetime.now().strftime("%I:%M:%S %p"),
    }


def economic_calendar() -> List[dict]:
    today = datetime.now()
    return [
        {
            "date": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
            "event": "Jobless Claims",
            "importance": "Medium",
            "markets": "Stocks, Dollar, Bonds",
            "impact": "Can affect morning volatility.",
        },
        {
            "date": (today + timedelta(days=3)).strftime("%Y-%m-%d"),
            "event": "ISM / PMI Data",
            "importance": "High",
            "markets": "Stocks, Dollar, Metals",
            "impact": "Growth data can shift risk appetite.",
        },
        {
            "date": (today + timedelta(days=7)).strftime("%Y-%m-%d"),
            "event": "CPI Inflation",
            "importance": "High",
            "markets": "Metals, Dollar, Yields, Stocks",
            "impact": "High impact for silver/gold and rate expectations.",
        },
        {
            "date": (today + timedelta(days=14)).strftime("%Y-%m-%d"),
            "event": "FOMC / Fed Communication",
            "importance": "High",
            "markets": "Everything",
            "impact": "Can trigger large moves in stocks, metals, bonds, and USD.",
        },
    ]


def metals_intelligence() -> List[dict]:
    return [
        {"metal": "Silver", "bias": "Bullish Watch", "drivers": "Dollar softness, industrial demand, miner leverage", "symbols": "SLV, SILJ, HL, AG, CDE"},
        {"metal": "Gold", "bias": "Constructive", "drivers": "Real yields, central bank demand, risk hedging", "symbols": "GLD, GDX, GDXJ"},
        {"metal": "Copper", "bias": "Cyclical Watch", "drivers": "Global growth, electrification, China demand", "symbols": "FCX, COPX"},
        {"metal": "Uranium", "bias": "Long-term Structural", "drivers": "Nuclear energy demand, supply deficits", "symbols": "URNM"},
    ]


def news_categories() -> List[dict]:
    return [
        {"category": "Breaking News", "status": "Monitor", "note": "High-impact headlines can override technical setups."},
        {"category": "Earnings", "status": "Important", "note": "Avoid blind entries into earnings volatility."},
        {"category": "Analyst Changes", "status": "Watch", "note": "Upgrades/downgrades can drive premarket momentum."},
        {"category": "Commodities", "status": "Important", "note": "Metals and energy moves affect miners and ETFs."},
        {"category": "Macroeconomics", "status": "High Impact", "note": "Fed, inflation, and dollar moves matter most for metals."},
        {"category": "AI & Technology", "status": "Leadership", "note": "Tech strength supports risk-on scanner setups."},
    ]


def market_health_label(score: int) -> str:
    if score >= 80:
        return "Bullish"
    if score >= 65:
        return "Constructive"
    if score >= 50:
        return "Mixed"
    return "Defensive"


def ai_market_briefing() -> str:
    dash = market_dashboard()
    metals = metals_intelligence()
    calendar = economic_calendar()
    score = dash["market_health"]
    high_events = [e for e in calendar if e["importance"] == "High"]

    return f"""AI MARKET BRIEFING

Market Regime:
{dash['regime']}

Market Health:
{score}/100 — {market_health_label(score)}

Risk Sentiment:
{dash['breadth']['signal']}

Dollar:
{dash['dollar']['signal']}

Volatility:
VIX {dash['vix']['value']} — {dash['vix']['signal']}

Metals:
Silver: {metals[0]['bias']}
Gold: {metals[1]['bias']}
Copper: {metals[2]['bias']}
Uranium: {metals[3]['bias']}

High Impact Events Ahead:
{len(high_events)}

ATIS Interpretation:
The market backdrop is constructive but still selective. Scanner setups should be filtered by volume, VWAP, trend alignment, and upcoming macro events. Metals remain important to monitor because dollar/yield shifts can quickly change miner strength.
"""


def dashboard_report() -> str:
    dash = market_dashboard()
    return f"""MARKET INTELLIGENCE DASHBOARD

Updated:
{dash['updated']}

Overall Market Health:
{dash['market_health']}/100 — {market_health_label(dash['market_health'])}

Regime:
{dash['regime']}

Index Context:
S&P 500: {dash['sp500']['trend']} | Score {dash['sp500']['score']}
Nasdaq: {dash['nasdaq']['trend']} | Score {dash['nasdaq']['score']}

Volatility:
VIX {dash['vix']['value']} — {dash['vix']['signal']}

Dollar:
{dash['dollar']['signal']}

Yields:
{dash['yields']['signal']}

Breadth:
{dash['breadth']['signal']}
"""


def metals_report() -> str:
    lines = ["METALS INTELLIGENCE", ""]
    for item in metals_intelligence():
        lines.append(f"{item['metal']}: {item['bias']}")
        lines.append(f"Drivers: {item['drivers']}")
        lines.append(f"Symbols: {item['symbols']}")
        lines.append("")
    return "\n".join(lines)


def calendar_report() -> str:
    lines = ["ECONOMIC CALENDAR", ""]
    for event in economic_calendar():
        lines.append(f"{event['date']} — {event['event']}")
        lines.append(f"Importance: {event['importance']}")
        lines.append(f"Markets: {event['markets']}")
        lines.append(f"Impact: {event['impact']}")
        lines.append("")
    return "\n".join(lines)


def news_report() -> str:
    lines = ["NEWS INTELLIGENCE CATEGORIES", ""]
    for item in news_categories():
        lines.append(f"{item['category']} — {item['status']}")
        lines.append(item["note"])
        lines.append("")
    return "\n".join(lines)
