"""
SP500 Market Structure — SMC Analysis on M5/M15
Optimized for the fast-paced NY open dynamics
Detects: BOS, CHoCH, FVG (Breakaway Gaps), Order Blocks
"""
import json
import numpy as np
from src.clients import mt5_bridge


def _detect_swing_points(highs: list, lows: list, strength: int = 3) -> tuple:
    """Detect swing highs and lows with given strength"""
    swing_highs = []
    swing_lows = []

    for i in range(strength, len(highs) - strength):
        # Swing high: higher than N candles on each side
        if all(highs[i] >= highs[i-j] for j in range(1, strength+1)) and \
           all(highs[i] >= highs[i+j] for j in range(1, strength+1)):
            swing_highs.append({"index": i, "price": highs[i]})

        # Swing low: lower than N candles on each side
        if all(lows[i] <= lows[i-j] for j in range(1, strength+1)) and \
           all(lows[i] <= lows[i+j] for j in range(1, strength+1)):
            swing_lows.append({"index": i, "price": lows[i]})

    return swing_highs, swing_lows


def _detect_bos_choch(swing_highs: list, swing_lows: list, current_price: float) -> dict:
    """
    Detect Break of Structure (BOS) and Change of Character (CHoCH)
    BOS = continuation (HH in uptrend, LL in downtrend)
    CHoCH = reversal (LL in uptrend, HH in downtrend)
    """
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return {"structure": "UNDEFINED", "last_event": None}

    # Determine trend from last 4 swing points
    last_highs = swing_highs[-3:]
    last_lows = swing_lows[-3:]

    # Check if making Higher Highs + Higher Lows (bullish)
    hh = all(last_highs[i]["price"] > last_highs[i-1]["price"] for i in range(1, len(last_highs)))
    hl = all(last_lows[i]["price"] > last_lows[i-1]["price"] for i in range(1, len(last_lows)))

    # Check if making Lower Lows + Lower Highs (bearish)
    ll = all(last_lows[i]["price"] < last_lows[i-1]["price"] for i in range(1, len(last_lows)))
    lh = all(last_highs[i]["price"] < last_highs[i-1]["price"] for i in range(1, len(last_highs)))

    if hh and hl:
        structure = "BULLISH"
    elif ll and lh:
        structure = "BEARISH"
    else:
        structure = "RANGING"

    # Detect last event
    last_event = None
    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        # Last swing high vs previous
        sh_current = swing_highs[-1]
        sh_prev = swing_highs[-2]
        sl_current = swing_lows[-1]
        sl_prev = swing_lows[-2]

        # BOS bullish: price broke above previous swing high
        if current_price > sh_prev["price"] and structure == "BULLISH":
            last_event = {"type": "BOS", "direction": "BULLISH", "level": sh_prev["price"], "candles_ago": len(swing_highs) - swing_highs.index(sh_prev)}

        # BOS bearish: price broke below previous swing low
        elif current_price < sl_prev["price"] and structure == "BEARISH":
            last_event = {"type": "BOS", "direction": "BEARISH", "level": sl_prev["price"], "candles_ago": len(swing_lows) - swing_lows.index(sl_prev)}

        # CHoCH bullish: was making LL but now broke a swing high
        elif structure != "BULLISH" and current_price > sh_prev["price"]:
            last_event = {"type": "CHoCH", "direction": "BULLISH", "level": sh_prev["price"]}

        # CHoCH bearish: was making HH but now broke a swing low
        elif structure != "BEARISH" and current_price < sl_prev["price"]:
            last_event = {"type": "CHoCH", "direction": "BEARISH", "level": sl_prev["price"]}

    return {"structure": structure, "last_event": last_event}


def _detect_fvgs(opens: list, highs: list, lows: list, closes: list, current_price: float) -> list:
    """
    Detect Fair Value Gaps (3-candle imbalance)
    In SP500, breakaway FVGs after liquidity sweeps are high-probability
    """
    fvgs = []
    for i in range(2, len(highs)):
        # Bullish FVG: candle[i] low > candle[i-2] high (gap up)
        if lows[i] > highs[i-2]:
            gap_size = lows[i] - highs[i-2]
            if gap_size >= 2.0:  # Minimum 2 points for SP500
                mitigated = current_price <= lows[i]  # Price came back into FVG
                fvgs.append({
                    "type": "BULLISH_FVG",
                    "top": round(lows[i], 2),
                    "bottom": round(highs[i-2], 2),
                    "size_points": round(gap_size, 2),
                    "candles_ago": len(highs) - 1 - i,
                    "mitigated": mitigated
                })

        # Bearish FVG: candle[i] high < candle[i-2] low (gap down)
        if highs[i] < lows[i-2]:
            gap_size = lows[i-2] - highs[i]
            if gap_size >= 2.0:
                mitigated = current_price >= highs[i]
                fvgs.append({
                    "type": "BEARISH_FVG",
                    "top": round(lows[i-2], 2),
                    "bottom": round(highs[i], 2),
                    "size_points": round(gap_size, 2),
                    "candles_ago": len(highs) - 1 - i,
                    "mitigated": mitigated
                })

    # Return most recent unmitigated FVGs (max 5)
    unmitigated = [f for f in fvgs if not f["mitigated"]]
    return sorted(unmitigated, key=lambda x: x["candles_ago"])[:5]


def _detect_order_blocks(opens: list, highs: list, lows: list, closes: list, swing_highs: list, swing_lows: list) -> list:
    """
    Detect Order Blocks — last opposite candle before a BOS
    In SP500, OBs at session opens are institutional footprints
    """
    obs = []

    # Bullish OB: last bearish candle before a swing low that held
    for sl in swing_lows[-5:]:
        idx = sl["index"]
        # Look back for last bearish candle before the swing low
        for j in range(idx, max(idx - 5, 0), -1):
            if closes[j] < opens[j]:  # Bearish candle
                obs.append({
                    "type": "BULLISH_OB",
                    "top": round(highs[j], 2),
                    "bottom": round(lows[j], 2),
                    "candles_ago": len(highs) - 1 - j,
                    "associated_swing": round(sl["price"], 2)
                })
                break

    # Bearish OB: last bullish candle before a swing high
    for sh in swing_highs[-5:]:
        idx = sh["index"]
        for j in range(idx, max(idx - 5, 0), -1):
            if closes[j] > opens[j]:  # Bullish candle
                obs.append({
                    "type": "BEARISH_OB",
                    "top": round(highs[j], 2),
                    "bottom": round(lows[j], 2),
                    "candles_ago": len(highs) - 1 - j,
                    "associated_swing": round(sh["price"], 2)
                })
                break

    return obs[-6:]  # Max 6 OBs


def register_structure_tools(mcp):

    @mcp.tool()
    async def sp500_market_structure(timeframe: str = "M5", lookback: int = 100) -> str:
        """
        Full SMC structural analysis for US500Cash.
        Detects BOS, CHoCH, FVGs, and Order Blocks on the specified timeframe.
        Default M5 for entry precision. Use M15 for higher timeframe confirmation.
        
        Args:
            timeframe: M5 (default, entry), M15 (confirmation), H1 (bias)
            lookback: Number of candles to analyze (default 100)
        """
        data = await mt5_bridge.get_candles(timeframe, lookback)
        candles = data.get("candles", [])

        if len(candles) < 20:
            return json.dumps({"error": f"Insufficient data: {len(candles)} candles"})

        opens = [float(c["open"]) for c in candles]
        highs = [float(c["high"]) for c in candles]
        lows = [float(c["low"]) for c in candles]
        closes = [float(c["close"]) for c in candles]
        current_price = closes[-1]

        # Swing detection (strength=3 for M5, =2 for H1)
        strength = 3 if timeframe == "M5" else 2
        swing_highs, swing_lows = _detect_swing_points(highs, lows, strength)

        # Structure + BOS/CHoCH
        structure_result = _detect_bos_choch(swing_highs, swing_lows, current_price)

        # FVGs
        fvgs = _detect_fvgs(opens, highs, lows, closes, current_price)

        # Order Blocks
        order_blocks = _detect_order_blocks(opens, highs, lows, closes, swing_highs, swing_lows)

        # Momentum: last 5 candles average body size
        recent_bodies = [abs(closes[i] - opens[i]) for i in range(-5, 0)]
        avg_body = np.mean(recent_bodies)
        momentum = "STRONG" if avg_body > 3.0 else "MODERATE" if avg_body > 1.5 else "WEAK"

        return json.dumps({
            "symbol": "US500Cash",
            "timeframe": timeframe,
            "candles_analyzed": len(candles),
            "current_price": round(current_price, 2),
            "structure": structure_result["structure"],
            "last_event": structure_result["last_event"],
            "swing_highs": [{"price": round(s["price"], 2), "candles_ago": len(candles) - 1 - s["index"]} for s in swing_highs[-4:]],
            "swing_lows": [{"price": round(s["price"], 2), "candles_ago": len(candles) - 1 - s["index"]} for s in swing_lows[-4:]],
            "fvgs_unmitigated": fvgs,
            "order_blocks": order_blocks,
            "momentum": momentum,
            "avg_body_points": round(avg_body, 2)
        })

    @mcp.tool()
    async def sp500_multi_timeframe() -> str:
        """
        Multi-timeframe structural alignment for SP500.
        Checks H1 (bias) + M15 (confirmation) + M5 (entry trigger).
        Returns alignment score -3 to +3.
        """
        results = {}
        for tf in ["H1", "M15", "M5"]:
            count = 100 if tf == "M5" else 80
            data = await mt5_bridge.get_candles(tf, count)
            candles = data.get("candles", [])

            if len(candles) < 20:
                results[tf] = {"structure": "NO_DATA", "score": 0}
                continue

            highs = [float(c["high"]) for c in candles]
            lows = [float(c["low"]) for c in candles]
            closes = [float(c["close"]) for c in candles]
            current_price = closes[-1]

            strength = 2 if tf == "H1" else 3
            swing_highs, swing_lows = _detect_swing_points(highs, lows, strength)
            structure = _detect_bos_choch(swing_highs, swing_lows, current_price)

            score = 0
            if structure["structure"] == "BULLISH":
                score = 1
            elif structure["structure"] == "BEARISH":
                score = -1

            results[tf] = {
                "structure": structure["structure"],
                "last_event": structure["last_event"],
                "score": score
            }

        total_score = sum(r["score"] for r in results.values())

        if total_score >= 2:
            alignment = "STRONG_BULLISH"
        elif total_score == 1:
            alignment = "WEAK_BULLISH"
        elif total_score == 0:
            alignment = "NEUTRAL"
        elif total_score == -1:
            alignment = "WEAK_BEARISH"
        else:
            alignment = "STRONG_BEARISH"

        return json.dumps({
            "symbol": "US500Cash",
            "alignment": alignment,
            "total_score": total_score,
            "timeframes": results,
            "trade_direction": "BUY" if total_score >= 2 else "SELL" if total_score <= -2 else "NO_TRADE"
        })
