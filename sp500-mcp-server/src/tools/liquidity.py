"""
SP500 Liquidity Sweeps — Institutional reference levels
Detects sweeps of PDH/PDL, Asia High/Low, London High/Low
This is the PRIMARY tool for bias determination in SP500
"""
import json
import numpy as np
from datetime import datetime, timezone, timedelta
from src.clients import mt5_bridge


def _find_session_range(candles: list, start_hour: int, end_hour: int, date: datetime) -> dict:
    """Find high/low within a specific UTC hour range for a given date"""
    session_candles = []
    for c in candles:
        # candle time format from bridge: "2026-07-16 13:30:00"
        try:
            ct = datetime.strptime(c["time"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except (ValueError, KeyError):
            continue
        if ct.date() == date.date() and start_hour <= ct.hour < end_hour:
            session_candles.append(c)

    if not session_candles:
        return {"high": None, "low": None, "candle_count": 0}

    high = max(float(c["high"]) for c in session_candles)
    low = min(float(c["low"]) for c in session_candles)
    return {"high": high, "low": low, "candle_count": len(session_candles)}


def register_liquidity_tools(mcp):

    @mcp.tool()
    async def sp500_get_liquidity_levels() -> str:
        """
        Returns key institutional liquidity levels for SP500:
        - Previous Day High/Low (PDH/PDL)
        - Asia session High/Low (00:00-08:00 UTC)
        - London session High/Low (08:00-13:00 UTC)
        - Current day developing High/Low
        These are the levels institutions sweep before making directional moves.
        """
        # Get M5 candles — enough for ~2 days
        data = await mt5_bridge.get_candles("M5", 576)  # 576 * 5min = 48 hours
        candles = data.get("candles", [])

        if not candles:
            return json.dumps({"error": "No candle data available"})

        now = datetime.now(timezone.utc)
        today = now.date()
        yesterday = today - timedelta(days=1)

        # If it's Monday, yesterday = Friday
        if today.weekday() == 0:
            yesterday = today - timedelta(days=3)

        # Previous Day High/Low
        pd_candles = [c for c in candles if _parse_candle_date(c) == yesterday]
        if pd_candles:
            pdh = max(float(c["high"]) for c in pd_candles)
            pdl = min(float(c["low"]) for c in pd_candles)
        else:
            pdh, pdl = None, None

        # Asia session (00:00-08:00 UTC today)
        asia = _find_session_range(candles, 0, 8, now)

        # London session (08:00-13:00 UTC today)
        london = _find_session_range(candles, 8, 13, now)

        # Current NY session developing (13:00+ UTC today)
        ny = _find_session_range(candles, 13, 24, now)

        # Current price (last candle close)
        current_price = float(candles[-1]["close"]) if candles else None

        # Detect sweeps
        sweeps = []
        if current_price and pdh and current_price > pdh:
            sweeps.append({"level": "PDH", "price": pdh, "swept": True, "direction": "above"})
        if current_price and pdl and current_price < pdl:
            sweeps.append({"level": "PDL", "price": pdl, "swept": True, "direction": "below"})
        if current_price and asia["high"] and current_price > asia["high"]:
            sweeps.append({"level": "ASIA_HIGH", "price": asia["high"], "swept": True, "direction": "above"})
        if current_price and asia["low"] and current_price < asia["low"]:
            sweeps.append({"level": "ASIA_LOW", "price": asia["low"], "swept": True, "direction": "below"})
        if current_price and london["high"] and current_price > london["high"]:
            sweeps.append({"level": "LONDON_HIGH", "price": london["high"], "swept": True, "direction": "above"})
        if current_price and london["low"] and current_price < london["low"]:
            sweeps.append({"level": "LONDON_LOW", "price": london["low"], "swept": True, "direction": "below"})

        # Determine bias from sweeps
        if any(s["level"] in ("PDH", "LONDON_HIGH", "ASIA_HIGH") and s["direction"] == "above" for s in sweeps):
            # Swept highs — could be bullish continuation OR bearish reversal trap
            bias_from_sweeps = "SWEPT_HIGHS_CHECK_STRUCTURE"
        elif any(s["level"] in ("PDL", "LONDON_LOW", "ASIA_LOW") and s["direction"] == "below" for s in sweeps):
            bias_from_sweeps = "SWEPT_LOWS_CHECK_STRUCTURE"
        else:
            bias_from_sweeps = "NO_SWEEP_YET"

        return json.dumps({
            "current_price": current_price,
            "previous_day": {"high": pdh, "low": pdl, "range_points": round(pdh - pdl, 2) if pdh and pdl else None},
            "asia_session": {"high": asia["high"], "low": asia["low"], "range_points": round(asia["high"] - asia["low"], 2) if asia["high"] and asia["low"] else None},
            "london_session": {"high": london["high"], "low": london["low"], "range_points": round(london["high"] - london["low"], 2) if london["high"] and london["low"] else None},
            "ny_session": {"high": ny["high"], "low": ny["low"], "developing": True},
            "sweeps_detected": sweeps,
            "bias_from_sweeps": bias_from_sweeps,
            "note": "After a sweep, look for CHoCH on M5 to confirm reversal. If no CHoCH, it's continuation."
        })

    @mcp.tool()
    async def sp500_get_key_levels(lookback_days: int = 5) -> str:
        """
        Returns weekly key levels: swing highs/lows from last N days,
        round numbers (every 50 points), and VWAP-equivalent zones.
        """
        data = await mt5_bridge.get_candles("H1", lookback_days * 24)
        candles = data.get("candles", [])

        if not candles:
            return json.dumps({"error": "No data"})

        highs = [float(c["high"]) for c in candles]
        lows = [float(c["low"]) for c in candles]
        closes = [float(c["close"]) for c in candles]

        current_price = closes[-1]
        week_high = max(highs)
        week_low = min(lows)

        # Find swing highs/lows (local extremes)
        swing_highs = []
        swing_lows = []
        for i in range(2, len(highs) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                swing_highs.append(round(highs[i], 2))
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                swing_lows.append(round(lows[i], 2))

        # Round numbers (nearest 50-point levels above and below)
        base = int(current_price / 50) * 50
        round_numbers = [base - 100, base - 50, base, base + 50, base + 100]

        # Premium/Discount zones
        mid_range = (week_high + week_low) / 2
        premium_zone = mid_range + (week_high - mid_range) * 0.5  # Above 75% of range
        discount_zone = week_low + (mid_range - week_low) * 0.5   # Below 25% of range

        position = "PREMIUM" if current_price > premium_zone else "DISCOUNT" if current_price < discount_zone else "EQUILIBRIUM"

        return json.dumps({
            "current_price": round(current_price, 2),
            "week_range": {"high": round(week_high, 2), "low": round(week_low, 2), "range_points": round(week_high - week_low, 2)},
            "swing_highs": sorted(set(swing_highs), reverse=True)[:5],
            "swing_lows": sorted(set(swing_lows))[:5],
            "round_numbers": round_numbers,
            "premium_discount": {
                "position": position,
                "premium_above": round(premium_zone, 2),
                "discount_below": round(discount_zone, 2),
                "equilibrium": round(mid_range, 2)
            }
        })


def _parse_candle_date(candle: dict):
    """Extract date from candle time string"""
    try:
        return datetime.strptime(candle["time"], "%Y-%m-%d %H:%M:%S").date()
    except (ValueError, KeyError):
        return None
