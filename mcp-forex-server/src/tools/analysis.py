"""Analysis tools — using local indicators from broker candles (no TradingView dependency)."""

import json
from datetime import datetime, timezone

from src.clients.local_indicators import get_full_analysis
from src.tools.database import execute_one, USER_ID


def register_analysis_tools(mcp):
    """Register all analysis tools."""

    @mcp.tool()
    def forex_analysis(symbol: str, timeframe: str = "H1") -> str:
        """
        Full technical analysis of a forex pair on a specific timeframe.
        Uses real candles from MT5 broker — no external API dependency.

        Args:
            symbol: Forex pair — EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, EURGBP
            timeframe: M5, M15, H1, H4, D1

        Returns:
            Price, indicators (RSI, MACD, ADX, ATR, EMAs, Stochastic),
            recommendation (BUY/SELL/NEUTRAL), and signal strength.
        """
        result = get_full_analysis(symbol, timeframe, 200)
        if "error" in result:
            return json.dumps(result)

        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        return json.dumps(result)

    @mcp.tool()
    def forex_multi_timeframe(symbol: str) -> str:
        """
        Top-down multi-timeframe analysis: D1 → H4 → H1.
        Determines trend alignment and gives a score from -3 to +3.
        Uses real candles from MT5 broker — no external API dependency.

        Args:
            symbol: Forex pair — EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, EURGBP

        Returns:
            Analysis for each timeframe, alignment score, and trading recommendation.
        """
        timeframes = {"D1": "D1", "H4": "H4", "H1": "H1"}
        results = {}
        score = 0

        for tf_name, tf_code in timeframes.items():
            analysis = get_full_analysis(symbol, tf_code, 200)
            if "error" in analysis:
                results[tf_name] = {"error": analysis["error"]}
                continue

            rec = analysis["recommendation"]
            if rec in ("BUY", "STRONG_BUY"):
                tf_score = 1
            elif rec in ("SELL", "STRONG_SELL"):
                tf_score = -1
            else:
                tf_score = 0

            score += tf_score
            results[tf_name] = {
                "recommendation": rec,
                "strength": analysis["strength"],
                "ema_trend": analysis["ema_trend"],
                "adx": analysis["indicators"]["adx_14"],
                "rsi": analysis["indicators"]["rsi_14"],
                "atr_pips": analysis["indicators"]["atr_pips"],
                "stoch_k": analysis["indicators"]["stoch_k"],
                "score_contribution": tf_score,
            }

        # Alignment logic
        abs_score = abs(score)
        if abs_score >= 2:
            direction = "BULLISH" if score > 0 else "BEARISH"
            aligned = True
        else:
            direction = "NEUTRAL"
            aligned = False

        return json.dumps({
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "timeframes": results,
            "alignment": {
                "direction": direction,
                "score": score,
                "max_score": 3,
                "aligned": aligned,
            },
        })

    @mcp.tool()
    def forex_market_scan(pairs: str = None, min_adx: float = 0) -> str:
        """
        Scan multiple forex pairs and rank trading opportunities.
        Uses real candles from MT5 broker — no external API dependency.

        Args:
            pairs: Comma-separated pairs to scan. Default: all major pairs.
            min_adx: Minimum ADX threshold (0 = read from DB settings, default 20).

        Returns:
            Ranked opportunities with alignment score, and pairs to skip.
        """
        # Read min_adx from settings if not provided
        if min_adx <= 0:
            settings = execute_one(
                "SELECT min_adx_entry FROM trading_settings WHERE user_id = %s",
                (USER_ID,)
            )
            min_adx = float(settings["min_adx_entry"]) if settings and settings.get("min_adx_entry") else 20.0

        default_pairs = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "EURGBP"]
        scan_pairs = pairs.split(",") if pairs else default_pairs

        opportunities = []
        no_trade = []

        for pair in scan_pairs:
            pair = pair.strip().upper()

            # Multi-timeframe analysis
            score = 0
            h1_data = None

            for tf_code in ["D1", "H4", "H1"]:
                a = get_full_analysis(pair, tf_code, 200)
                if "error" in a:
                    continue

                rec = a["recommendation"]
                if rec in ("BUY", "STRONG_BUY"):
                    score += 1
                elif rec in ("SELL", "STRONG_SELL"):
                    score -= 1

                if tf_code == "H1":
                    h1_data = a

            if not h1_data:
                no_trade.append({"symbol": pair, "reason": "Failed to get H1 data"})
                continue

            adx = h1_data["indicators"]["adx_14"]
            rsi = h1_data["indicators"]["rsi_14"]

            # Filter — more permissive: let the agent's Quality Score decide
            # Only skip if BOTH ADX is very low AND score is 0
            if adx < min_adx and abs(score) < 1:
                no_trade.append({
                    "symbol": pair,
                    "reason": f"ADX={adx:.1f}, Score={score}",
                })
                continue

            opportunities.append({
                "symbol": pair,
                "recommendation": "BUY" if score > 0 else "SELL",
                "strength": h1_data["strength"],
                "adx": adx,
                "rsi": rsi,
                "ema_trend": h1_data["ema_trend"],
                "atr_pips": h1_data["indicators"]["atr_pips"],
                "alignment_score": score,
            })

        # Rank by |score| * adx
        opportunities.sort(key=lambda x: abs(x["alignment_score"]) * x["adx"], reverse=True)
        for i, opp in enumerate(opportunities):
            opp["rank"] = i + 1

        return json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "scanned": len(scan_pairs),
            "opportunities": opportunities,
            "no_trade": no_trade,
        })

    @mcp.tool()
    def get_session_info() -> str:
        """
        Get current trading session info: active session, optimal pairs, volatility.
        Uses pytz with real timezones to handle DST automatically year-round.

        Returns:
            Active sessions, optimal pairs for current hour, warnings.
        """
        import pytz
        from datetime import time as dt_time

        now_utc = datetime.now(timezone.utc)

        # Convert to each session's local time
        tokyo_tz = pytz.timezone("Asia/Tokyo")
        london_tz = pytz.timezone("Europe/London")
        ny_tz = pytz.timezone("America/New_York")
        sydney_tz = pytz.timezone("Australia/Sydney")

        now_tokyo = now_utc.astimezone(tokyo_tz).time()
        now_london = now_utc.astimezone(london_tz).time()
        now_ny = now_utc.astimezone(ny_tz).time()
        now_sydney = now_utc.astimezone(sydney_tz).time()

        # Session hours in LOCAL time (fixed, never change)
        # Tokyo: 09:00-18:00 JST
        # London: 08:00-17:00 GMT/BST
        # New York: 08:00-17:00 EST/EDT
        # Sydney: 07:00-16:00 AEST/AEDT

        sessions = []
        if dt_time(9, 0) <= now_tokyo <= dt_time(18, 0):
            sessions.append("tokyo")
        if dt_time(8, 0) <= now_london <= dt_time(17, 0):
            sessions.append("london")
        if dt_time(8, 0) <= now_ny <= dt_time(17, 0):
            sessions.append("new_york")
        if dt_time(7, 0) <= now_sydney <= dt_time(16, 0):
            sessions.append("sydney")

        overlap = "london" in sessions and "new_york" in sessions

        # Optimal pairs by session
        session_pairs = {
            "sydney": ["AUDUSD", "NZDUSD"],
            "tokyo": ["USDJPY", "AUDUSD", "GBPJPY"],
            "london": ["EURUSD", "GBPUSD", "EURGBP", "USDCAD", "USDCHF"],
            "new_york": ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "GBPJPY"],
        }

        optimal = set()
        for s in sessions:
            optimal.update(session_pairs.get(s, []))

        all_pairs = {"EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "EURGBP", "NZDUSD", "USDCHF", "GBPJPY"}
        avoid = all_pairs - optimal if optimal else set()

        # Volatility
        if overlap:
            volatility = "HIGH"
        elif "london" in sessions or "new_york" in sessions:
            volatility = "MEDIUM"
        elif sessions:
            volatility = "LOW"
        else:
            volatility = "VERY_LOW"

        # Session end warning
        warnings = []
        if "new_york" in sessions and now_ny >= dt_time(16, 0):
            warnings.append("NY session ending soon. Avoid new positions.")
        if "london" in sessions and now_london >= dt_time(16, 0):
            warnings.append("London session ending soon.")
        if not sessions:
            warnings.append("No major session active. Low liquidity expected.")

        # DST info for transparency
        london_offset = now_utc.astimezone(london_tz).strftime("%z")
        ny_offset = now_utc.astimezone(ny_tz).strftime("%z")

        return json.dumps({
            "timestamp": now_utc.isoformat(),
            "utc_hour": now_utc.hour,
            "active_sessions": sessions,
            "overlap": overlap,
            "volatility_level": volatility,
            "optimal_pairs": sorted(optimal),
            "avoid_pairs": sorted(avoid),
            "warnings": warnings,
            "dst_info": {
                "london": f"GMT{london_offset}",
                "new_york": f"ET{ny_offset}",
            },
        })
