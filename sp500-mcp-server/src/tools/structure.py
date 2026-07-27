"""
SP500 Market Structure — Wyckoff + SMC Analysis
Detects: Accumulation/Distribution phases, Springs, Upthrusts, BOS, CHoCH, FVG, OBs
Fixes the CHoCH detection to be HISTORICAL (not ephemeral)
"""
import json
import numpy as np
from src.clients import mt5_bridge


def _detect_swing_points(highs: list, lows: list, strength: int = 2) -> tuple:
    """Detect swing highs and lows with given strength"""
    swing_highs = []
    swing_lows = []

    for i in range(strength, len(highs) - strength):
        if all(highs[i] >= highs[i-j] for j in range(1, strength+1)) and \
           all(highs[i] >= highs[i+j] for j in range(1, strength+1)):
            swing_highs.append({"index": i, "price": highs[i]})

        if all(lows[i] <= lows[i-j] for j in range(1, strength+1)) and \
           all(lows[i] <= lows[i+j] for j in range(1, strength+1)):
            swing_lows.append({"index": i, "price": lows[i]})

    return swing_highs, swing_lows


def _detect_bos_choch_historical(highs: list, lows: list, closes: list, swing_highs: list, swing_lows: list) -> dict:
    """
    Detect BOS/CHoCH by scanning candle history — NOT just current price.
    A break is confirmed when ANY candle closed beyond the level.
    This prevents the disappearing CHoCH bug.
    """
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return {"structure": "UNDEFINED", "last_event": None, "bos": None, "choch": None}

    # Determine trend from recent swings
    last_highs = swing_highs[-3:]
    last_lows = swing_lows[-3:]

    hh = all(last_highs[i]["price"] > last_highs[i-1]["price"] for i in range(1, len(last_highs)))
    hl = all(last_lows[i]["price"] > last_lows[i-1]["price"] for i in range(1, len(last_lows)))
    ll = all(last_lows[i]["price"] < last_lows[i-1]["price"] for i in range(1, len(last_lows)))
    lh = all(last_highs[i]["price"] < last_highs[i-1]["price"] for i in range(1, len(last_highs)))

    if hh and hl:
        structure = "BULLISH"
    elif ll and lh:
        structure = "BEARISH"
    else:
        structure = "RANGING"

    # Scan history for BOS/CHoCH events
    # Look at the last 2 swing highs and 2 swing lows
    bos = None
    choch = None
    
    total_candles = len(closes)
    
    # Check breaks of swing highs (bullish BOS or CHoCH)
    for sh in reversed(swing_highs[:-1]):  # All except the most recent
        level = sh["price"]
        sh_idx = sh["index"]
        
        # Scan candles AFTER this swing for a close above it
        for k in range(sh_idx + 1, total_candles):
            if closes[k] > level:
                candles_ago = total_candles - 1 - k
                # Was the structure bearish/ranging before this break? → CHoCH
                # Was it bullish? → BOS
                pre_structure = _get_pre_structure(swing_highs, swing_lows, sh_idx)
                
                event = {
                    "direction": "BULLISH",
                    "level": round(level, 2),
                    "break_candle": k,
                    "candles_ago": candles_ago,
                    "confirmed": True,
                }
                
                if pre_structure != "BULLISH":
                    if choch is None or k > choch.get("break_candle", 0):
                        choch = {**event, "type": "CHoCH"}
                else:
                    if bos is None or k > bos.get("break_candle", 0):
                        bos = {**event, "type": "BOS"}
                break  # Only first break matters for this swing
    
    # Check breaks of swing lows (bearish BOS or CHoCH)
    for sl in reversed(swing_lows[:-1]):
        level = sl["price"]
        sl_idx = sl["index"]
        
        for k in range(sl_idx + 1, total_candles):
            if closes[k] < level:
                candles_ago = total_candles - 1 - k
                pre_structure = _get_pre_structure(swing_highs, swing_lows, sl_idx)
                
                event = {
                    "direction": "BEARISH",
                    "level": round(level, 2),
                    "break_candle": k,
                    "candles_ago": candles_ago,
                    "confirmed": True,
                }
                
                if pre_structure != "BEARISH":
                    if choch is None or k > choch.get("break_candle", 0):
                        choch = {**event, "type": "CHoCH"}
                else:
                    if bos is None or k > bos.get("break_candle", 0):
                        bos = {**event, "type": "BOS"}
                break

    # Use the most recent event as last_event
    last_event = None
    if bos and choch:
        last_event = choch if choch["break_candle"] > bos["break_candle"] else bos
    elif choch:
        last_event = choch
    elif bos:
        last_event = bos

    # Clean up internal fields
    for obj in [bos, choch, last_event]:
        if obj and "break_candle" in obj:
            del obj["break_candle"]

    return {"structure": structure, "last_event": last_event, "bos": bos, "choch": choch}


def _get_pre_structure(swing_highs, swing_lows, before_idx):
    """Determine structure BEFORE a given index"""
    prev_highs = [sh for sh in swing_highs if sh["index"] < before_idx]
    prev_lows = [sl for sl in swing_lows if sl["index"] < before_idx]
    
    if len(prev_highs) < 2 or len(prev_lows) < 2:
        return "RANGING"
    
    h1, h2 = prev_highs[-2]["price"], prev_highs[-1]["price"]
    l1, l2 = prev_lows[-2]["price"], prev_lows[-1]["price"]
    
    if h2 > h1 and l2 > l1:
        return "BULLISH"
    elif h2 < h1 and l2 < l1:
        return "BEARISH"
    return "RANGING"


def _detect_wyckoff_phase(candles: list, swing_highs: list, swing_lows: list, current_price: float) -> dict:
    """
    Detect Wyckoff phase based on price behavior within the range.
    Spring/Upthrust detection is MULTI-CANDLE: looks for sweep + recovery sequence.
    
    Returns:
        phase: ACCUMULATION, MARKUP, DISTRIBUTION, MARKDOWN, RANGING
        spring: last false breakdown (sweep of lows with recovery)
        upthrust: last false breakout (sweep of highs with rejection)
    """
    if len(candles) < 20:
        return {"phase": "INSUFFICIENT_DATA", "spring": None, "upthrust": None}
    
    if not swing_highs or not swing_lows:
        return {"phase": "NO_STRUCTURE", "spring": None, "upthrust": None}
    
    # TR boundaries: from recent swings
    tr_high = max(sh["price"] for sh in swing_highs[-4:])
    tr_low = min(sl["price"] for sl in swing_lows[-4:])
    tr_range = tr_high - tr_low
    
    # Scan larger window for springs/upthrusts (last 50 candles or all available)
    scan_start = max(0, len(candles) - 50)
    
    # Spring detection (multi-candle):
    # 1. A candle breaks below TR low (the sweep)
    # 2. Within the next 10 candles, price closes BACK above TR low with a bullish candle
    spring = None
    for i in range(scan_start, len(candles) - 1):
        c = candles[i]
        low_i = float(c['low'])
        
        if low_i < tr_low:
            # Found a sweep below TR. Now look for recovery within next 10 candles
            sweep_low = low_i
            # Track deepest point in the sweep area
            for check in range(i, min(i + 10, len(candles))):
                check_low = float(candles[check]['low'])
                if check_low < sweep_low:
                    sweep_low = check_low
            
            for j in range(i, min(i + 10, len(candles))):
                cj = candles[j]
                close_j = float(cj['close'])
                open_j = float(cj['open'])
                
                if close_j > tr_low and close_j > open_j:  # Bullish recovery above TR
                    body = close_j - open_j
                    if body >= 3.0:  # Min displacement for SP500
                        spring = {
                            "detected": True,
                            "candles_ago": len(candles) - 1 - j,
                            "low_reached": round(sweep_low, 2),
                            "tr_low": round(tr_low, 2),
                            "penetration_points": round(tr_low - sweep_low, 2),
                            "recovery_close": round(close_j, 2),
                            "entry_zone": round(close_j, 2),
                            "sl_suggested": round(sweep_low - 3, 2),
                            "target_zone": round(tr_high, 2),
                        }
                        break
            if spring:
                break  # Use the first valid spring found
    
    # Upthrust detection (multi-candle):
    upthrust = None
    for i in range(scan_start, len(candles) - 1):
        c = candles[i]
        high_i = float(c['high'])
        
        if high_i > tr_high:
            sweep_high = high_i
            for check in range(i, min(i + 10, len(candles))):
                check_high = float(candles[check]['high'])
                if check_high > sweep_high:
                    sweep_high = check_high
            
            for j in range(i, min(i + 10, len(candles))):
                cj = candles[j]
                close_j = float(cj['close'])
                open_j = float(cj['open'])
                
                if close_j < tr_high and close_j < open_j:  # Bearish rejection below TR
                    body = open_j - close_j
                    if body >= 3.0:
                        upthrust = {
                            "detected": True,
                            "candles_ago": len(candles) - 1 - j,
                            "high_reached": round(sweep_high, 2),
                            "tr_high": round(tr_high, 2),
                            "penetration_points": round(sweep_high - tr_high, 2),
                            "rejection_close": round(close_j, 2),
                            "entry_zone": round(close_j, 2),
                            "sl_suggested": round(sweep_high + 3, 2),
                            "target_zone": round(tr_low, 2),
                        }
                        break
            if upthrust:
                break
    
    # Determine phase
    mid = (tr_high + tr_low) / 2
    
    if spring and not upthrust and current_price > mid:
        phase = "ACCUMULATION_SPRING"
    elif upthrust and not spring and current_price < mid:
        phase = "DISTRIBUTION_UPTHRUST"
    elif current_price > tr_high:
        phase = "MARKUP"
    elif current_price < tr_low:
        phase = "MARKDOWN"
    elif spring:
        phase = "ACCUMULATION"
    elif upthrust:
        phase = "DISTRIBUTION"
    else:
        phase = "RANGING"
    
    return {
        "phase": phase,
        "trading_range": {"high": round(tr_high, 2), "low": round(tr_low, 2), "size": round(tr_range, 2)},
        "spring": spring,
        "upthrust": upthrust,
        "price_position": "ABOVE_TR" if current_price > tr_high else "BELOW_TR" if current_price < tr_low else "PREMIUM" if current_price > mid else "DISCOUNT",
    }


def _detect_fvgs(opens: list, highs: list, lows: list, closes: list, current_price: float) -> list:
    """Detect Fair Value Gaps (3-candle imbalance) — minimum 2 points for SP500"""
    fvgs = []
    for i in range(2, len(highs)):
        if lows[i] > highs[i-2]:
            gap_size = lows[i] - highs[i-2]
            if gap_size >= 2.0:
                mitigated = current_price <= lows[i]
                fvgs.append({
                    "type": "BULLISH_FVG",
                    "top": round(lows[i], 2),
                    "bottom": round(highs[i-2], 2),
                    "size_points": round(gap_size, 2),
                    "candles_ago": len(highs) - 1 - i,
                    "mitigated": mitigated
                })
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

    unmitigated = [f for f in fvgs if not f["mitigated"]]
    return sorted(unmitigated, key=lambda x: x["candles_ago"])[:5]


def _detect_order_blocks(opens: list, highs: list, lows: list, closes: list, swing_highs: list, swing_lows: list) -> list:
    """Detect Order Blocks — last opposite candle before a structural break"""
    obs = []

    for sl in swing_lows[-5:]:
        idx = sl["index"]
        for j in range(idx, max(idx - 5, 0), -1):
            if closes[j] < opens[j]:
                obs.append({
                    "type": "BULLISH_OB",
                    "top": round(highs[j], 2),
                    "bottom": round(lows[j], 2),
                    "candles_ago": len(highs) - 1 - j,
                    "associated_swing": round(sl["price"], 2)
                })
                break

    for sh in swing_highs[-5:]:
        idx = sh["index"]
        for j in range(idx, max(idx - 5, 0), -1):
            if closes[j] > opens[j]:
                obs.append({
                    "type": "BEARISH_OB",
                    "top": round(highs[j], 2),
                    "bottom": round(lows[j], 2),
                    "candles_ago": len(highs) - 1 - j,
                    "associated_swing": round(sh["price"], 2)
                })
                break

    return obs[-6:]


def _calculate_effort_result(opens, highs, lows, closes, lookback=10):
    """
    Wyckoff's Law of Effort vs Result
    Effort = candle body size (proxy for volume)
    Result = price displacement
    Divergence = big bodies but little net movement = absorption
    """
    if len(closes) < lookback + 1:
        return {"harmony": "UNKNOWN", "effort": 0, "result": 0}
    
    recent = closes[-lookback:]
    recent_opens = opens[-lookback:]
    
    # Effort: sum of body sizes
    effort = sum(abs(recent[i] - recent_opens[i]) for i in range(len(recent)))
    
    # Result: net price change
    result = abs(closes[-1] - closes[-lookback])
    
    # Ratio: if effort is high but result is low → absorption (reversal coming)
    ratio = result / effort if effort > 0 else 0
    
    if ratio > 0.5:
        harmony = "HARMONIC"  # Normal trending — effort produces result
    elif ratio > 0.2:
        harmony = "MODERATE"  # Mixed
    else:
        harmony = "DIVERGENT"  # Big candles, small net movement = absorption/distribution
    
    # Direction of effort (are big candles bullish or bearish?)
    bull_effort = sum(max(0, recent[i] - recent_opens[i]) for i in range(len(recent)))
    bear_effort = sum(max(0, recent_opens[i] - recent[i]) for i in range(len(recent)))
    
    dominant_effort = "BULLISH" if bull_effort > bear_effort * 1.3 else "BEARISH" if bear_effort > bull_effort * 1.3 else "MIXED"
    
    return {
        "harmony": harmony,
        "effort_points": round(effort, 2),
        "result_points": round(result, 2),
        "ratio": round(ratio, 3),
        "dominant_effort": dominant_effort,
        "interpretation": _interpret_effort_result(harmony, dominant_effort)
    }


def _interpret_effort_result(harmony, dominant_effort):
    """Wyckoff interpretation of effort vs result"""
    if harmony == "DIVERGENT" and dominant_effort == "BEARISH":
        return "ABSORPTION: Heavy selling absorbed by professionals. Expect UP move."
    elif harmony == "DIVERGENT" and dominant_effort == "BULLISH":
        return "DISTRIBUTION: Heavy buying met with professional selling. Expect DOWN move."
    elif harmony == "HARMONIC" and dominant_effort == "BULLISH":
        return "MARKUP: Healthy bullish trend, demand exceeding supply."
    elif harmony == "HARMONIC" and dominant_effort == "BEARISH":
        return "MARKDOWN: Healthy bearish trend, supply exceeding demand."
    else:
        return "NEUTRAL: No clear Wyckoff signal from effort analysis."


def register_structure_tools(mcp):

    @mcp.tool()
    async def sp500_market_structure(timeframe: str = "M5", lookback: int = 100) -> str:
        """
        Full Wyckoff + SMC structural analysis for US500Cash.
        Detects: BOS, CHoCH (historical — doesn't disappear), FVGs, Order Blocks,
        Wyckoff phases (Accumulation/Distribution), Springs, Upthrusts,
        and Effort vs Result harmony.
        
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

        # Swing detection — strength=2 for all (fast detection on indices)
        strength = 2
        swing_highs, swing_lows = _detect_swing_points(highs, lows, strength)

        # Structure + BOS/CHoCH (HISTORICAL — scans candle closes, not just current price)
        structure_result = _detect_bos_choch_historical(highs, lows, closes, swing_highs, swing_lows)

        # Wyckoff Phase Detection
        wyckoff = _detect_wyckoff_phase(candles, swing_highs, swing_lows, current_price)

        # FVGs
        fvgs = _detect_fvgs(opens, highs, lows, closes, current_price)

        # Order Blocks
        order_blocks = _detect_order_blocks(opens, highs, lows, closes, swing_highs, swing_lows)

        # Effort vs Result (Wyckoff 3rd Law)
        effort_result = _calculate_effort_result(opens, highs, lows, closes, lookback=10)

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
            "bos": structure_result["bos"],
            "choch": structure_result["choch"],
            "last_event": structure_result["last_event"],
            "wyckoff": wyckoff,
            "effort_vs_result": effort_result,
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
        Multi-timeframe Wyckoff alignment for SP500.
        H1 (trend/phase) + M15 (confirmation) + M5 (entry trigger).
        Returns alignment score and Wyckoff phase on each timeframe.
        """
        results = {}
        for tf in ["H1", "M15", "M5"]:
            count = 100 if tf == "M5" else 80
            data = await mt5_bridge.get_candles(tf, count)
            candles = data.get("candles", [])

            if len(candles) < 20:
                results[tf] = {"structure": "NO_DATA", "wyckoff_phase": "UNKNOWN", "score": 0}
                continue

            opens = [float(c["open"]) for c in candles]
            highs = [float(c["high"]) for c in candles]
            lows = [float(c["low"]) for c in candles]
            closes = [float(c["close"]) for c in candles]
            current_price = closes[-1]

            swing_highs, swing_lows = _detect_swing_points(highs, lows, 2)
            structure = _detect_bos_choch_historical(highs, lows, closes, swing_highs, swing_lows)
            wyckoff = _detect_wyckoff_phase(candles, swing_highs, swing_lows, current_price)

            score = 0
            if structure["structure"] == "BULLISH":
                score = 1
            elif structure["structure"] == "BEARISH":
                score = -1
            
            # Wyckoff phase boosts
            if wyckoff["phase"] in ("ACCUMULATION_SPRING", "ACCUMULATION"):
                score += 0.5
            elif wyckoff["phase"] in ("DISTRIBUTION_UPTHRUST", "DISTRIBUTION"):
                score -= 0.5

            results[tf] = {
                "structure": structure["structure"],
                "last_event": structure["last_event"],
                "wyckoff_phase": wyckoff["phase"],
                "spring": wyckoff.get("spring"),
                "upthrust": wyckoff.get("upthrust"),
                "score": score
            }

        total_score = sum(r["score"] for r in results.values())

        if total_score >= 1.5:
            alignment = "STRONG_BULLISH"
        elif total_score > 0:
            alignment = "WEAK_BULLISH"
        elif total_score == 0:
            alignment = "NEUTRAL"
        elif total_score > -1.5:
            alignment = "WEAK_BEARISH"
        else:
            alignment = "STRONG_BEARISH"

        return json.dumps({
            "symbol": "US500Cash",
            "alignment": alignment,
            "total_score": total_score,
            "timeframes": results,
            "trade_direction": "BUY" if total_score >= 1.5 else "SELL" if total_score <= -1.5 else "WAIT"
        })
