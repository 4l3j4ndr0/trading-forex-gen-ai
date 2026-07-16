"""News tools — Forex news from RSS feeds with sentiment analysis."""

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

import requests


# RSS feeds por moneda/región
RSS_FEEDS = {
    "forex_general": "https://www.investing.com/rss/news_301.rss",
    "economic": "https://www.investing.com/rss/news_1.rss",
    "forex_analysis": "https://www.investing.com/rss/news_302.rss",
}

# Keywords por moneda para filtrar noticias relevantes
CURRENCY_KEYWORDS = {
    "EUR": ["eur", "euro", "ecb", "eurozone", "lagarde", "europe", "german", "france", "inflation eu"],
    "USD": ["usd", "dollar", "fed", "fomc", "powell", "us economy", "treasury", "nonfarm", "nfp", "cpi us", "american"],
    "GBP": ["gbp", "pound", "sterling", "boe", "bank of england", "bailey", "uk economy", "british"],
    "JPY": ["jpy", "yen", "boj", "bank of japan", "ueda", "japan", "japanese"],
    "AUD": ["aud", "aussie", "rba", "reserve bank of australia", "australian"],
    "CAD": ["cad", "loonie", "boc", "bank of canada", "canadian", "oil price"],
    "NZD": ["nzd", "kiwi", "rbnz", "new zealand"],
    "CHF": ["chf", "franc", "snb", "swiss"],
}

# Keywords de alto impacto
HIGH_IMPACT_KEYWORDS = [
    "rate decision", "interest rate", "nfp", "non-farm", "nonfarm", "cpi",
    "gdp", "fomc", "ecb meeting", "boe meeting", "employment", "inflation",
    "retail sales", "pmi", "manufacturing", "trade balance", "central bank",
]

# Keywords de sentimiento
BULLISH_KEYWORDS = ["rise", "surge", "jump", "beat", "strong", "hawkish", "higher", "rally", "gain", "accelerat", "exceed", "above"]
BEARISH_KEYWORDS = ["fall", "drop", "decline", "miss", "weak", "dovish", "lower", "slump", "loss", "decelerat", "below", "disappoint"]


def _parse_rss(url: str, timeout: int = 10) -> list[dict]:
    """Parse RSS feed and return articles."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; ForexBot/1.0)",
        }
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return []

        root = ET.fromstring(resp.content)
        articles = []

        for item in root.findall(".//item"):
            title = item.findtext("title", "")
            description = item.findtext("description", "")
            pub_date = item.findtext("pubDate", "")
            link = item.findtext("link", "")

            # Parse date
            parsed_time = None
            if pub_date:
                try:
                    # RFC 822 format: "Mon, 14 Jul 2026 17:30:00 GMT"
                    parsed_time = datetime.strptime(pub_date.strip(), "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc)
                except (ValueError, IndexError):
                    try:
                        parsed_time = datetime.strptime(pub_date.strip()[:25], "%a, %d %b %Y %H:%M:%S").replace(tzinfo=timezone.utc)
                    except (ValueError, IndexError):
                        parsed_time = None  # Unknown date — will not block trading

            # Clean HTML from description
            clean_desc = re.sub(r"<[^>]+>", "", description).strip()
            clean_desc = re.sub(r"\s+", " ", clean_desc)[:300]

            articles.append({
                "title": title,
                "description": clean_desc,
                "time": parsed_time,
                "link": link,
            })

        return articles
    except Exception:
        return []


def _detect_sentiment(text: str) -> str:
    """Detect sentiment from text."""
    text_lower = text.lower()
    bullish_score = sum(1 for kw in BULLISH_KEYWORDS if kw in text_lower)
    bearish_score = sum(1 for kw in BEARISH_KEYWORDS if kw in text_lower)

    if bullish_score > bearish_score:
        return "bullish"
    elif bearish_score > bullish_score:
        return "bearish"
    return "neutral"


def _detect_impact(text: str) -> str:
    """Detect if news is high impact."""
    text_lower = text.lower()
    if any(kw in text_lower for kw in HIGH_IMPACT_KEYWORDS):
        return "high"
    return "medium"


def _get_affected_currency(text: str, currencies: list[str]) -> str | None:
    """Determine which currency is most affected."""
    text_lower = text.lower()
    scores = {}
    for curr in currencies:
        keywords = CURRENCY_KEYWORDS.get(curr, [])
        scores[curr] = sum(1 for kw in keywords if kw in text_lower)
    if scores:
        best = max(scores, key=scores.get)
        if scores[best] > 0:
            return best
    return None


def _time_ago(dt: datetime) -> str:
    """Human-readable time ago."""
    if not dt:
        return "unknown"
    diff = datetime.now(timezone.utc) - dt
    minutes = int(diff.total_seconds() / 60)
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    return f"{hours // 24}d ago"


def register_news_tools(mcp):
    """Register news tools."""

    @mcp.tool()
    def get_news_for_pair(symbol: str, hours_back: int = 8, impact: str = "all") -> str:
        """
        Get recent news for a Forex pair with sentiment analysis.

        Args:
            symbol: Forex pair (EURUSD, GBPUSD, USDJPY, etc.)
            hours_back: How many hours back to search (default 8, max 48)
            impact: Filter by impact level — 'high', 'medium', 'all'

        Returns:
            News articles with title, description, sentiment, impact,
            and overall bias for the pair.
        """
        hours_back = min(hours_back, 48)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)

        # Extract currencies from symbol
        base = symbol[:3].upper()
        quote = symbol[3:6].upper()
        currencies = [base, quote]

        # Fetch from multiple RSS feeds
        all_articles = []
        for feed_name, url in RSS_FEEDS.items():
            articles = _parse_rss(url)
            all_articles.extend(articles)

        # Filter by time
        recent = [a for a in all_articles if a["time"] and a["time"] >= cutoff]

        # Filter by currency relevance
        relevant = []
        for article in recent:
            full_text = f"{article['title']} {article['description']}".lower()
            base_keywords = CURRENCY_KEYWORDS.get(base, [])
            quote_keywords = CURRENCY_KEYWORDS.get(quote, [])

            is_relevant = (
                any(kw in full_text for kw in base_keywords) or
                any(kw in full_text for kw in quote_keywords)
            )
            if is_relevant:
                relevant.append(article)

        # Analyze each article
        news_items = []
        currency_sentiments = {base: [], quote: []}

        for article in relevant:
            full_text = f"{article['title']} {article['description']}"
            sentiment = _detect_sentiment(full_text)
            article_impact = _detect_impact(full_text)
            affected = _get_affected_currency(full_text, currencies)

            # Filter by impact if requested
            if impact == "high" and article_impact != "high":
                continue

            item = {
                "title": article["title"],
                "description": article["description"],
                "time": article["time"].isoformat() if article["time"] else None,
                "age": _time_ago(article["time"]),
                "sentiment": f"{sentiment}_{affected.lower()}" if affected else sentiment,
                "currency_affected": affected,
                "impact": article_impact,
            }
            news_items.append(item)

            # Track sentiment per currency
            if affected and affected in currency_sentiments:
                currency_sentiments[affected].append(sentiment)

        # Sort by time (most recent first)
        news_items.sort(key=lambda x: x["time"] or "", reverse=True)
        news_items = news_items[:15]  # Max 15 articles

        # Calculate overall sentiment per currency
        summary = {}
        for curr, sentiments in currency_sentiments.items():
            if sentiments:
                bullish = sentiments.count("bullish")
                bearish = sentiments.count("bearish")
                if bullish > bearish:
                    overall = "bullish"
                elif bearish > bullish:
                    overall = "bearish"
                else:
                    overall = "neutral"
                summary[curr] = {"sentiment": overall, "news_count": len(sentiments)}
            else:
                summary[curr] = {"sentiment": "neutral", "news_count": 0}

        # Determine pair bias
        base_sent = summary.get(base, {}).get("sentiment", "neutral")
        quote_sent = summary.get(quote, {}).get("sentiment", "neutral")

        if base_sent == "bullish" and quote_sent != "bullish":
            bias = "BUY"
        elif base_sent == "bearish" and quote_sent != "bearish":
            bias = "SELL"
        elif quote_sent == "bullish" and base_sent != "bullish":
            bias = "SELL"
        elif quote_sent == "bearish" and base_sent != "bearish":
            bias = "BUY"
        else:
            bias = "NEUTRAL"

        # Check if safe to trade (high impact news too close)
        safe_to_trade = True
        warning = None
        high_impact_items = [n for n in news_items if n["impact"] == "high"]
        if high_impact_items:
            for item in high_impact_items:
                if item["time"]:
                    try:
                        age_minutes = (datetime.now(timezone.utc) - datetime.fromisoformat(item["time"])).total_seconds() / 60
                        if 0 <= age_minutes < 30:
                            safe_to_trade = False
                            warning = f"High impact news {item['age']}: {item['title']}"
                            break
                    except (ValueError, TypeError):
                        continue  # Can't parse time — don't block

        return json.dumps({
            "symbol": symbol,
            "currencies": currencies,
            "hours_back": hours_back,
            "news_count": len(news_items),
            "news": news_items,
            "summary": summary,
            "bias": bias,
            "safe_to_trade": safe_to_trade,
            "warning": warning,
        })
