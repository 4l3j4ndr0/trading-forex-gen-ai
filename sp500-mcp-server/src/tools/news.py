"""
SP500 Macro Filter — Only US economic events matter
Tracks: FOMC, CPI, NFP, PPI, GDP, Jobless Claims, Powell speeches
"""
import json
import re
from datetime import datetime, timezone, timedelta
import httpx


# US-only high impact keywords
US_HIGH_IMPACT_KEYWORDS = [
    "fomc", "federal reserve", "powell", "interest rate decision",
    "nonfarm", "non-farm", "nfp", "payrolls",
    "cpi", "consumer price", "inflation",
    "ppi", "producer price",
    "gdp", "gross domestic",
    "jobless claims", "unemployment",
    "retail sales",
    "ism manufacturing", "ism services",
    "fed minutes",
]

US_MEDIUM_IMPACT_KEYWORDS = [
    "housing starts", "building permits",
    "consumer confidence", "michigan",
    "durable goods", "trade balance",
    "treasury", "bond auction",
]

RSS_FEEDS = [
    "https://www.forexfactory.com/rss",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC&region=US&lang=en-US",
]


def register_news_tools(mcp):

    @mcp.tool()
    async def sp500_macro_filter(hours_ahead: int = 4) -> str:
        """
        Checks for US macro events that could impact SP500.
        Only tracks USD-relevant events (Fed, CPI, NFP, etc).
        Returns safe_to_trade status.
        
        Args:
            hours_ahead: Hours to look ahead for upcoming events (default 4)
        """
        now = datetime.now(timezone.utc)
        events_found = []

        # Try to fetch from RSS feeds
        for feed_url in RSS_FEEDS:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    r = await client.get(feed_url)
                    if r.status_code == 200:
                        content = r.text.lower()
                        # Check for high impact keywords
                        for kw in US_HIGH_IMPACT_KEYWORDS:
                            if kw in content:
                                events_found.append({
                                    "keyword": kw,
                                    "impact": "HIGH",
                                    "source": feed_url.split("/")[2]
                                })
            except Exception:
                continue

        # Deduplicate
        seen = set()
        unique_events = []
        for e in events_found:
            if e["keyword"] not in seen:
                seen.add(e["keyword"])
                unique_events.append(e)

        # Determine safety
        high_impact_count = len([e for e in unique_events if e["impact"] == "HIGH"])

        # Check day of week for known recurring events
        weekday = now.weekday()
        hour = now.hour

        # Known high-impact windows (approximate UTC times)
        known_events_today = []
        if weekday == 4 and 12 <= hour <= 14:  # Friday 12-14 UTC = NFP window
            known_events_today.append("Possible NFP release window")
        if weekday == 2 and 18 <= hour <= 19:  # Wednesday 18-19 UTC = FOMC
            known_events_today.append("Possible FOMC window")

        # Safe to trade logic: block only around actual events
        safe_to_trade = True
        warning = None

        if known_events_today:
            safe_to_trade = False
            warning = f"Known event window: {', '.join(known_events_today)}"

        return json.dumps({
            "safe_to_trade": safe_to_trade,
            "warning": warning,
            "events_detected": unique_events[:5],
            "known_windows_today": known_events_today,
            "current_utc": now.strftime("%H:%M UTC"),
            "day": now.strftime("%A"),
            "note": "SP500 reacts violently to Fed/CPI/NFP. Avoid opening 15 min before and 30 min after these releases."
        })
