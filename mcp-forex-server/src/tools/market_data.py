"""Market Data tools — candles, indicators, fibonacci, market structure (SMC)."""

import json
from typing import Optional

from src.clients.mt5_bridge import bridge


def _calculate_rsi(closes: list[float], period: int = 14) -> float:
    """Calculate RSI from close prices."""
    if len(closes) < period + 1:
        return 50.0

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def _calculate_ema(closes: list[float], period: int) -> list[float]:
    """Calculate EMA series."""
    if len(closes) < period:
        return []
    multiplier = 2 / (period + 1)
    ema = [sum(closes[:period]) / period]
    for price in closes[period:]:
        ema.append((price - ema[-1]) * multiplier + ema[-1])
    return ema


def _calculate_macd(closes: list[float]) -> dict:
    """Calculate MACD (12, 26, 9)."""
    ema12 = _calculate_ema(closes, 12)
    ema26 = _calculate_ema(closes, 26)

    if not ema12 or not ema26:
        return {"line": 0, "signal": 0, "histogram": 0}

    # Align lengths
    offset = len(ema12) - len(ema26)
    macd_line = [ema12[offset + i] - ema26[i] for i in range(len(ema26))]

    # Signal line (EMA 9 of MACD)
    if len(macd_line) < 9:
        signal = macd_line[-1] if macd_line else 0
    else:
        signal_ema = _calculate_ema(macd_line, 9)
        signal = signal_ema[-1] if signal_ema else 0

    current_macd = macd_line[-1] if macd_line else 0
    return {
        "line": round(current_macd, 6),
        "signal": round(signal, 6),
        "histogram": round(current_macd - signal, 6),
    }


def _calculate_bollinger(closes: list[float], period: int = 20, std_mult: float = 2.0) -> dict:
    """Calculate Bollinger Bands."""
    if len(closes) < period:
        return {"upper": 0, "middle": 0, "lower": 0}

    recent = closes[-period:]
    middle = sum(recent) / period
    std = (sum((x - middle) ** 2 for x in recent) / period) ** 0.5
    return {
        "upper": round(middle + std_mult * std, 6),
        "middle": round(middle, 6),
        "lower": round(middle - std_mult * std, 6),
    }


def _calculate_atr_from_candles(candles: list[dict], period: int = 14) -> float:
    """Calculate ATR from candle data."""
    if len(candles) < period + 1:
        return 0.0

    trs = []
    for i in range(1, len(candles)):
        h = candles[i]["high"]
        l = candles[i]["low"]
        pc = candles[i - 1]["close"]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)

    if len(trs) < period:
        return sum(trs) / len(trs) if trs else 0

    atr = sum(trs[:period]) / period
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period
    return atr


def _find_swing_points(candles: list[dict], lookback: int = 5) -> tuple[list, list]:
    """Find swing highs and lows."""
    swing_highs = []
    swing_lows = []

    for i in range(lookback, len(candles) - lookback):
        high = candles[i]["high"]
        low = candles[i]["low"]

        is_high = all(high >= candles[i + j]["high"] for j in range(-lookback, lookback + 1) if j != 0)
        is_low = all(low <= candles[i + j]["low"] for j in range(-lookback, lookback + 1) if j != 0)

        if is_high:
            swing_highs.append({"price": high, "index": i, "candles_ago": len(candles) - 1 - i})
        if is_low:
            swing_lows.append({"price": low, "index": i, "candles_ago": len(candles) - 1 - i})

    return swing_highs, swing_lows


def register_market_data_tools(mcp):
    """Register all market data tools."""

    @mcp.tool()
    def get_candles(symbol: str, timeframe: str = "H1", count: int = 100) -> str:
        """
        Get raw OHLCV candles from the broker.

        Args:
            symbol: Forex pair (EURUSD, GBPUSD, etc.)
            timeframe: M5, M15, H1, H4, D1
            count: Number of candles (max 500)

        Returns:
            Array of candles with open, high, low, close, volume, time.
        """
        count = min(count, 500)
        result = bridge.get_candles(symbol, timeframe, count)

        if isinstance(result, dict) and "error" in result:
            return json.dumps(result)

        candles = result.get("candles", []) if isinstance(result, dict) else result
        return json.dumps({
            "symbol": symbol,
            "timeframe": timeframe,
            "count": len(candles),
            "candles": candles[-count:],
        })

    @mcp.tool()
    def get_indicator_atr(symbol: str, timeframe: str = "H1", period: int = 14) -> str:
        """
        Get ATR (Average True Range) from the broker.

        Args:
            symbol: Forex pair
            timeframe: M5, M15, H1, H4, D1
            period: ATR period (default 14)

        Returns:
            ATR value in price and pips.
        """
        result = bridge.get_atr(symbol, timeframe, period)
        if "error" in result:
            return json.dumps(result)
        return json.dumps(result)

    @mcp.tool()
    def get_spread_live(symbol: str) -> str:
        """
        Get live spread for a symbol.

        Args:
            symbol: Forex pair

        Returns:
            Spread in pips, bid, ask.
        """
        result = bridge.get_spread(symbol)
        if "error" in result:
            return json.dumps(result)
        return json.dumps(result)

    @mcp.tool()
    def get_market_data(symbol: str, timeframe: str = "H1", count: int = 100) -> str:
        """
        Get candles + calculated indicators in one call. Best tool for strategy analysis.

        Args:
            symbol: Forex pair (EURUSD, GBPUSD, etc.)
            timeframe: M5, M15, H1, H4, D1
            count: Number of candles for calculation (max 200)

        Returns:
            Latest candles + RSI, EMA(10/20/50), MACD, Bollinger Bands, ATR, spread, current price.
        """
        count = min(count, 200)
        candle_result = bridge.get_candles(symbol, timeframe, count)

        if isinstance(candle_result, dict) and "error" in candle_result:
            return json.dumps(candle_result)

        candles = candle_result.get("candles", []) if isinstance(candle_result, dict) else candle_result

        if len(candles) < 26:
            return json.dumps({"error": f"Not enough candles ({len(candles)}). Need at least 26."})

        closes = [c["close"] for c in candles]

        # Calculate indicators
        rsi = _calculate_rsi(closes, 14)
        ema10 = _calculate_ema(closes, 10)
        ema20 = _calculate_ema(closes, 20)
        ema50 = _calculate_ema(closes, 50)
        macd = _calculate_macd(closes)
        bollinger = _calculate_bollinger(closes, 20)
        atr = _calculate_atr_from_candles(candles, 14)

        # Spread
        spread_result = bridge.get_spread(symbol)
        spread_pips = spread_result.get("spread_pips", 0) if "error" not in spread_result else 0

        # Determine pip size
        pip_size = 0.01 if "JPY" in symbol else 0.0001

        current = candles[-1]
        return json.dumps({
            "symbol": symbol,
            "timeframe": timeframe,
            "candles_count": len(candles),
            "last_5_candles": candles[-5:],
            "current_price": {
                "open": current["open"],
                "high": current["high"],
                "low": current["low"],
                "close": current["close"],
            },
            "indicators": {
                "rsi_14": rsi,
                "ema_10": round(ema10[-1], 6) if ema10 else None,
                "ema_20": round(ema20[-1], 6) if ema20 else None,
                "ema_50": round(ema50[-1], 6) if ema50 else None,
                "macd": macd,
                "bollinger": bollinger,
                "atr_14": round(atr, 6),
                "atr_pips": round(atr / pip_size, 1),
            },
            "spread_pips": spread_pips,
            "ema_alignment": "BULLISH" if ema10 and ema20 and ema50 and ema10[-1] > ema20[-1] > ema50[-1] else
                             "BEARISH" if ema10 and ema20 and ema50 and ema10[-1] < ema20[-1] < ema50[-1] else "MIXED",
        })

    @mcp.tool()
    def get_fibonacci_levels(symbol: str, timeframe: str = "H4", lookback: int = 100) -> str:
        """
        Calculate Fibonacci retracement and extension levels from recent swing high/low.

        Args:
            symbol: Forex pair
            timeframe: H1, H4, D1 recommended
            lookback: Candles to analyze for swing detection (default 100)

        Returns:
            Swing high/low, retracement levels (23.6-78.6%), extension levels (127.2-161.8%), and current price position.
        """
        candle_result = bridge.get_candles(symbol, timeframe, min(lookback, 200))

        if isinstance(candle_result, dict) and "error" in candle_result:
            return json.dumps(candle_result)

        candles = candle_result.get("candles", []) if isinstance(candle_result, dict) else candle_result

        if len(candles) < 20:
            return json.dumps({"error": "Not enough candles for Fibonacci calculation"})

        # Find significant swing high and low
        swing_highs, swing_lows = _find_swing_points(candles, lookback=5)

        if not swing_highs or not swing_lows:
            # Fallback: use absolute high/low of the range
            high = max(c["high"] for c in candles)
            low = min(c["low"] for c in candles)
            high_idx = next(i for i, c in enumerate(candles) if c["high"] == high)
            low_idx = next(i for i, c in enumerate(candles) if c["low"] == low)
        else:
            # Use most recent significant swing points
            sh = sorted(swing_highs, key=lambda x: x["index"], reverse=True)[0]
            sl = sorted(swing_lows, key=lambda x: x["index"], reverse=True)[0]
            high = sh["price"]
            low = sl["price"]
            high_idx = sh["index"]
            low_idx = sl["index"]

        # Determine trend direction (which came first)
        if high_idx < low_idx:
            trend = "DOWNTREND"
            # Retracements go from low back up toward high
            diff = high - low
            retracements = {
                "0.0% (low)": round(low, 6),
                "23.6%": round(low + diff * 0.236, 6),
                "38.2%": round(low + diff * 0.382, 6),
                "50.0%": round(low + diff * 0.500, 6),
                "61.8%": round(low + diff * 0.618, 6),
                "78.6%": round(low + diff * 0.786, 6),
                "100.0% (high)": round(high, 6),
            }
            extensions = {
                "127.2%": round(high - diff * 1.272, 6),
                "161.8%": round(high - diff * 1.618, 6),
                "200.0%": round(high - diff * 2.000, 6),
            }
        else:
            trend = "UPTREND"
            # Retracements go from high back down toward low
            diff = high - low
            retracements = {
                "100.0% (high)": round(high, 6),
                "78.6%": round(high - diff * 0.236, 6),
                "61.8%": round(high - diff * 0.382, 6),
                "50.0%": round(high - diff * 0.500, 6),
                "38.2%": round(high - diff * 0.618, 6),
                "23.6%": round(high - diff * 0.786, 6),
                "0.0% (low)": round(low, 6),
            }
            extensions = {
                "127.2%": round(low + diff * 1.272, 6),
                "161.8%": round(low + diff * 1.618, 6),
                "200.0%": round(low + diff * 2.000, 6),
            }

        current_price = candles[-1]["close"]
        position_pct = round((current_price - low) / diff * 100, 1) if diff > 0 else 50

        return json.dumps({
            "symbol": symbol,
            "timeframe": timeframe,
            "trend": trend,
            "swing_high": {"price": round(high, 6), "candles_ago": len(candles) - 1 - high_idx},
            "swing_low": {"price": round(low, 6), "candles_ago": len(candles) - 1 - low_idx},
            "range_pips": round(diff / (0.01 if "JPY" in symbol else 0.0001), 1),
            "retracements": retracements,
            "extensions": extensions,
            "current_price": round(current_price, 6),
            "position_in_range_pct": position_pct,
        })

    @mcp.tool()
    def get_market_structure(symbol: str, timeframe: str = "H1", lookback: int = 100) -> str:
        """
        Smart Money Concepts (SMC) analysis: swing structure, BOS, Order Blocks, FVGs, liquidity zones.

        Args:
            symbol: Forex pair
            timeframe: M15, H1, H4 recommended
            lookback: Candles to analyze (default 100)

        Returns:
            Market structure: trend, BOS/CHoCH, order blocks, fair value gaps, liquidity levels, and trade bias.
        """
        candle_result = bridge.get_candles(symbol, timeframe, min(lookback, 200))

        if isinstance(candle_result, dict) and "error" in candle_result:
            return json.dumps(candle_result)

        candles = candle_result.get("candles", []) if isinstance(candle_result, dict) else candle_result

        if len(candles) < 30:
            return json.dumps({"error": "Not enough candles for structure analysis"})

        # ─── 1. Swing Structure ────────────────────────────────────
        # Use strength=2 for M15/M5 (faster detection), 3 for H1+
        swing_strength = 2 if timeframe in ("M5", "M15") else 3
        swing_highs, swing_lows = _find_swing_points(candles, lookback=swing_strength)

        # ─── 2. Determine Trend & BOS ─────────────────────────────
        trend = "RANGING"
        bos = None
        choch = None

        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            # Higher highs + higher lows = bullish
            recent_highs = sorted(swing_highs, key=lambda x: x["index"], reverse=True)[:3]
            recent_lows = sorted(swing_lows, key=lambda x: x["index"], reverse=True)[:3]

            if len(recent_highs) >= 2 and len(recent_lows) >= 2:
                hh = recent_highs[0]["price"] > recent_highs[1]["price"]
                hl = recent_lows[0]["price"] > recent_lows[1]["price"]
                lh = recent_highs[0]["price"] < recent_highs[1]["price"]
                ll = recent_lows[0]["price"] < recent_lows[1]["price"]

                if hh and hl:
                    trend = "BULLISH"
                elif lh and ll:
                    trend = "BEARISH"

                # BOS: check if ANY candle in the lookback broke previous swing
                # (not just current price — captures historical breaks)
                last_price = candles[-1]["close"]
                if trend == "BULLISH" and len(recent_highs) >= 2:
                    prev_high = recent_highs[1]["price"]
                    # Check if any recent candle broke above prev_high
                    for j in range(max(0, recent_highs[1]["index"]), len(candles)):
                        if candles[j]["high"] > prev_high:
                            candles_ago = len(candles) - 1 - j
                            bos = {"type": "bullish", "level": round(prev_high, 6), "candles_ago": candles_ago, "confirmed": last_price > prev_high}
                            break
                elif trend == "BEARISH" and len(recent_lows) >= 2:
                    prev_low = recent_lows[1]["price"]
                    # Check if any recent candle broke below prev_low
                    for j in range(max(0, recent_lows[1]["index"]), len(candles)):
                        if candles[j]["low"] < prev_low:
                            candles_ago = len(candles) - 1 - j
                            bos = {"type": "bearish", "level": round(prev_low, 6), "candles_ago": candles_ago, "confirmed": last_price < prev_low}
                            break

                # CHoCH: first sign of reversal (structure shift)
                # Bullish CHoCH: was bearish (LH+LL) but price broke last swing high
                if trend == "BEARISH" or (lh and ll):
                    prev_high_level = recent_highs[1]["price"]
                    for j in range(max(0, recent_highs[1]["index"]), len(candles)):
                        if candles[j]["high"] > prev_high_level:
                            candles_ago = len(candles) - 1 - j
                            choch = {"type": "bullish_choch", "level": round(prev_high_level, 6), "candles_ago": candles_ago}
                            break
                # Bearish CHoCH: was bullish (HH+HL) but price broke last swing low
                elif trend == "BULLISH" or (hh and hl):
                    prev_low_level = recent_lows[1]["price"]
                    for j in range(max(0, recent_lows[1]["index"]), len(candles)):
                        if candles[j]["low"] < prev_low_level:
                            candles_ago = len(candles) - 1 - j
                            choch = {"type": "bearish_choch", "level": round(prev_low_level, 6), "candles_ago": candles_ago}
                            break

        # ─── 3. Order Blocks ──────────────────────────────────────
        order_blocks = []
        for i in range(2, len(candles) - 1):
            body_prev = abs(candles[i - 1]["close"] - candles[i - 1]["open"])
            body_curr = abs(candles[i]["close"] - candles[i]["open"])

            # Strong move after a consolidation candle = potential OB
            if body_curr > body_prev * 2 and body_curr > 0:
                # Bullish OB: bearish candle before strong bullish move
                if candles[i]["close"] > candles[i]["open"] and candles[i - 1]["close"] < candles[i - 1]["open"]:
                    ob = {
                        "type": "bullish_ob",
                        "high": round(candles[i - 1]["high"], 6),
                        "low": round(candles[i - 1]["low"], 6),
                        "candles_ago": len(candles) - 1 - (i - 1),
                        "mitigated": candles[-1]["low"] < candles[i - 1]["low"],
                    }
                    order_blocks.append(ob)
                # Bearish OB: bullish candle before strong bearish move
                elif candles[i]["close"] < candles[i]["open"] and candles[i - 1]["close"] > candles[i - 1]["open"]:
                    ob = {
                        "type": "bearish_ob",
                        "high": round(candles[i - 1]["high"], 6),
                        "low": round(candles[i - 1]["low"], 6),
                        "candles_ago": len(candles) - 1 - (i - 1),
                        "mitigated": candles[-1]["high"] > candles[i - 1]["high"],
                    }
                    order_blocks.append(ob)

        # Keep only recent unmitigated
        order_blocks = [ob for ob in order_blocks if not ob["mitigated"]][-5:]

        # ─── 4. Fair Value Gaps (FVG) ─────────────────────────────
        fvgs = []
        for i in range(2, len(candles)):
            # Bullish FVG: candle[i] low > candle[i-2] high (gap up)
            if candles[i]["low"] > candles[i - 2]["high"]:
                fvg = {
                    "type": "bullish_fvg",
                    "top": round(candles[i]["low"], 6),
                    "bottom": round(candles[i - 2]["high"], 6),
                    "candles_ago": len(candles) - 1 - i,
                    "filled": candles[-1]["low"] <= candles[i - 2]["high"],
                }
                fvgs.append(fvg)
            # Bearish FVG: candle[i] high < candle[i-2] low (gap down)
            elif candles[i]["high"] < candles[i - 2]["low"]:
                fvg = {
                    "type": "bearish_fvg",
                    "top": round(candles[i - 2]["low"], 6),
                    "bottom": round(candles[i]["high"], 6),
                    "candles_ago": len(candles) - 1 - i,
                    "filled": candles[-1]["high"] >= candles[i - 2]["low"],
                }
                fvgs.append(fvg)

        # Keep unfilled recent
        fvgs = [f for f in fvgs if not f["filled"]][-5:]

        # ─── 5. Liquidity Zones ───────────────────────────────────
        # Equal highs/lows (where stop losses accumulate)
        buy_side_liq = []  # Above price — stop losses of shorts
        sell_side_liq = []  # Below price — stop losses of longs

        tolerance = _calculate_atr_from_candles(candles, 14) * 0.3 if candles else 0

        for sh in swing_highs[-8:]:
            buy_side_liq.append(round(sh["price"], 6))
        for sl in swing_lows[-8:]:
            sell_side_liq.append(round(sl["price"], 6))

        # Deduplicate close levels
        buy_side_liq = sorted(set(round(p, 5) for p in buy_side_liq), reverse=True)[:4]
        sell_side_liq = sorted(set(round(p, 5) for p in sell_side_liq))[:4]

        # ─── 6. Bias ─────────────────────────────────────────────
        current_price = candles[-1]["close"]
        bias = "NEUTRAL"
        reasoning = []

        if trend == "BULLISH":
            bias = "BUY"
            reasoning.append(f"Bullish structure (HH+HL)")
        elif trend == "BEARISH":
            bias = "SELL"
            reasoning.append(f"Bearish structure (LH+LL)")

        if bos:
            reasoning.append(f"BOS {bos['type']} confirmed at {bos['level']}")

        bullish_obs = [ob for ob in order_blocks if ob["type"] == "bullish_ob"]
        bearish_obs = [ob for ob in order_blocks if ob["type"] == "bearish_ob"]

        if bullish_obs and bias == "BUY":
            nearest = min(bullish_obs, key=lambda x: x["candles_ago"])
            reasoning.append(f"Unmitigated bullish OB at {nearest['low']}-{nearest['high']}")
        if bearish_obs and bias == "SELL":
            nearest = min(bearish_obs, key=lambda x: x["candles_ago"])
            reasoning.append(f"Unmitigated bearish OB at {nearest['low']}-{nearest['high']}")

        unfilled_bullish_fvgs = [f for f in fvgs if f["type"] == "bullish_fvg"]
        unfilled_bearish_fvgs = [f for f in fvgs if f["type"] == "bearish_fvg"]
        if unfilled_bearish_fvgs and bias == "SELL":
            reasoning.append(f"Unfilled bearish FVG above")
        if unfilled_bullish_fvgs and bias == "BUY":
            reasoning.append(f"Unfilled bullish FVG below")

        return json.dumps({
            "symbol": symbol,
            "timeframe": timeframe,
            "trend": trend,
            "structure": {
                "last_swing_high": {"price": round(swing_highs[-1]["price"], 6), "candles_ago": swing_highs[-1]["candles_ago"]} if swing_highs else None,
                "last_swing_low": {"price": round(swing_lows[-1]["price"], 6), "candles_ago": swing_lows[-1]["candles_ago"]} if swing_lows else None,
                "bos": bos,
                "choch": choch,
            },
            "order_blocks": order_blocks,
            "fair_value_gaps": fvgs,
            "liquidity": {
                "buy_side": buy_side_liq,
                "sell_side": sell_side_liq,
            },
            "bias": bias,
            "reasoning": ". ".join(reasoning) if reasoning else "No clear directional bias",
            "current_price": round(current_price, 6),
        })
