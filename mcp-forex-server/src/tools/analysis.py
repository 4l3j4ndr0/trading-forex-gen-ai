"""Analysis tools — TradingView TA for Forex."""

import json
from datetime import datetime, timezone

from src.clients.tradingview import get_analysis


def register_analysis_tools(mcp):
    """Register all analysis tools."""

    @mcp.tool()
    def forex_analysis(symbol: str, timeframe: str = "1h") -> str:
        """
        Full technical analysis of a forex pair on a specific timeframe.

        Args:
            symbol: Forex pair — EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, EURGBP
            timeframe: '5m', '15m', '1h', '4h', '1d', '1w'

        Returns:
            Price, indicators (RSI, MACD, ADX, ATR, EMAs, Bollinger),
            recommendation (BUY/SELL/NEUTRAL), and signal strength.
        """
        result = get_analysis(symbol, timeframe)
        if "error" in result:
            return json.dumps(result)

        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        return json.dumps(result)

    @mcp.tool()
    def forex_multi_timeframe(symbol: str) -> str:
        """
        Top-down multi-timeframe analysis: D1 → H4 → H1.
        Determines trend alignment and gives a score from -3 to +3.

        Args:
            symbol: Forex pair — EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, EURGBP

        Returns:
            Analysis for each timeframe, alignment score, and trading recommendation.
        """
        timeframes = {"D1": "1d", "H4": "4h", "H1": "1h"}
        results = {}
        score = 0

        for tf_name, tf_code in timeframes.items():
            analysis = get_analysis(symbol, tf_code)
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
    def forex_market_scan(pairs: str = None, min_adx: float = 25.0) -> str:
        """
        Scan multiple forex pairs and rank trading opportunities.

        Args:
            pairs: Comma-separated pairs to scan. Default: all allowed pairs.
            min_adx: Minimum ADX threshold for trend strength (default 25).

        Returns:
            Ranked opportunities with alignment score, and pairs to skip.
        """
        default_pairs = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "EURGBP"]
        scan_pairs = pairs.split(",") if pairs else default_pairs

        opportunities = []
        no_trade = []

        for pair in scan_pairs:
            pair = pair.strip().upper()

            # Quick H1 analysis for filtering
            h1 = get_analysis(pair, "1h")
            if "error" in h1:
                no_trade.append({"symbol": pair, "reason": h1["error"]})
                continue

            adx = h1["indicators"]["adx_14"]
            rsi = h1["indicators"]["rsi_14"]

            # Multi-timeframe for alignment
            tf_data = {}
            score = 0
            for tf_name, tf_code in [("D1", "1d"), ("H4", "4h"), ("H1", "1h")]:
                a = get_analysis(pair, tf_code)
                if "error" not in a:
                    rec = a["recommendation"]
                    if rec in ("BUY", "STRONG_BUY"):
                        score += 1
                    elif rec in ("SELL", "STRONG_SELL"):
                        score -= 1

            # Filter
            if adx < min_adx or abs(score) < 2:
                no_trade.append({
                    "symbol": pair,
                    "reason": f"ADX={adx:.1f}" if adx < min_adx else f"Score={score}",
                })
                continue

            opportunities.append({
                "symbol": pair,
                "recommendation": "BUY" if score > 0 else "SELL",
                "strength": h1["strength"],
                "adx": adx,
                "rsi": rsi,
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

        Returns:
            Active sessions, optimal pairs for current hour, warnings.
        """
        now = datetime.now(timezone.utc)
        hour = now.hour

        sessions = []
        if 0 <= hour < 9:
            sessions.append("tokyo")
        if 7 <= hour < 16:
            sessions.append("london")
        if 12 <= hour < 21:
            sessions.append("new_york")

        overlap = "london" in sessions and "new_york" in sessions

        # Optimal pairs by session
        session_pairs = {
            "tokyo": ["USDJPY", "AUDUSD"],
            "london": ["EURUSD", "GBPUSD", "EURGBP", "USDCAD"],
            "new_york": ["EURUSD", "GBPUSD", "USDJPY", "USDCAD"],
        }

        optimal = set()
        for s in sessions:
            optimal.update(session_pairs.get(s, []))

        all_pairs = {"EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "EURGBP"}
        avoid = all_pairs - optimal

        # Volatility
        if overlap:
            volatility = "HIGH"
        elif "london" in sessions or "new_york" in sessions:
            volatility = "MEDIUM"
        else:
            volatility = "LOW"

        # Session end warning
        warnings = []
        if "new_york" in sessions and hour >= 20:
            warnings.append("NY session ending soon. Avoid new positions.")
        if "london" in sessions and hour >= 15:
            warnings.append("London session ending soon.")
        if not sessions:
            warnings.append("No major session active. Low liquidity expected.")

        return json.dumps({
            "timestamp": now.isoformat(),
            "utc_hour": hour,
            "active_sessions": sessions,
            "overlap": overlap,
            "volatility_level": volatility,
            "optimal_pairs": sorted(optimal),
            "avoid_pairs": sorted(avoid),
            "warnings": warnings,
        })
