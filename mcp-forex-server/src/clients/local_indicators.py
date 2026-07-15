"""Local indicators — replaces TradingView dependency using broker candles."""

from src.clients.mt5_bridge import bridge


def _calculate_rsi(closes: list[float], period: int = 14) -> float:
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
    if len(closes) < period:
        return []
    multiplier = 2 / (period + 1)
    ema = [sum(closes[:period]) / period]
    for price in closes[period:]:
        ema.append((price - ema[-1]) * multiplier + ema[-1])
    return ema


def _calculate_sma(values: list[float], period: int) -> float:
    if len(values) < period:
        return 0.0
    return sum(values[-period:]) / period


def _calculate_macd(closes: list[float]) -> dict:
    ema12 = _calculate_ema(closes, 12)
    ema26 = _calculate_ema(closes, 26)
    if not ema12 or not ema26:
        return {"line": 0, "signal": 0, "histogram": 0}
    offset = len(ema12) - len(ema26)
    macd_line = [ema12[offset + i] - ema26[i] for i in range(len(ema26))]
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


def _calculate_adx(candles: list[dict], period: int = 14) -> dict:
    """Calculate ADX, +DI, -DI from candle data."""
    if len(candles) < period + 2:
        return {"adx": 0, "plus_di": 0, "minus_di": 0}

    plus_dm_list = []
    minus_dm_list = []
    tr_list = []

    for i in range(1, len(candles)):
        high = candles[i]["high"]
        low = candles[i]["low"]
        prev_high = candles[i - 1]["high"]
        prev_low = candles[i - 1]["low"]
        prev_close = candles[i - 1]["close"]

        # True Range
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_list.append(tr)

        # Directional Movement
        plus_dm = high - prev_high if (high - prev_high) > (prev_low - low) and (high - prev_high) > 0 else 0
        minus_dm = prev_low - low if (prev_low - low) > (high - prev_high) and (prev_low - low) > 0 else 0
        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)

    if len(tr_list) < period:
        return {"adx": 0, "plus_di": 0, "minus_di": 0}

    # Smoothed TR, +DM, -DM (Wilder's smoothing)
    atr = sum(tr_list[:period]) / period
    smooth_plus_dm = sum(plus_dm_list[:period]) / period
    smooth_minus_dm = sum(minus_dm_list[:period]) / period

    dx_list = []

    for i in range(period, len(tr_list)):
        atr = (atr * (period - 1) + tr_list[i]) / period
        smooth_plus_dm = (smooth_plus_dm * (period - 1) + plus_dm_list[i]) / period
        smooth_minus_dm = (smooth_minus_dm * (period - 1) + minus_dm_list[i]) / period

        plus_di = (smooth_plus_dm / atr * 100) if atr > 0 else 0
        minus_di = (smooth_minus_dm / atr * 100) if atr > 0 else 0

        di_sum = plus_di + minus_di
        dx = abs(plus_di - minus_di) / di_sum * 100 if di_sum > 0 else 0
        dx_list.append(dx)

    if len(dx_list) < period:
        adx = sum(dx_list) / len(dx_list) if dx_list else 0
    else:
        adx = sum(dx_list[:period]) / period
        for i in range(period, len(dx_list)):
            adx = (adx * (period - 1) + dx_list[i]) / period

    # Final +DI and -DI
    plus_di = (smooth_plus_dm / atr * 100) if atr > 0 else 0
    minus_di = (smooth_minus_dm / atr * 100) if atr > 0 else 0

    return {
        "adx": round(adx, 2),
        "plus_di": round(plus_di, 2),
        "minus_di": round(minus_di, 2),
    }


def _calculate_atr(candles: list[dict], period: int = 14) -> float:
    if len(candles) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(candles)):
        h = candles[i]["high"]
        l = candles[i]["low"]
        pc = candles[i - 1]["close"]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    atr = sum(trs[:period]) / period
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period
    return atr


def _calculate_stochastic(candles: list[dict], k_period: int = 14, d_period: int = 3) -> dict:
    if len(candles) < k_period:
        return {"k": 50, "d": 50}
    k_values = []
    for i in range(k_period - 1, len(candles)):
        window = candles[i - k_period + 1:i + 1]
        highest = max(c["high"] for c in window)
        lowest = min(c["low"] for c in window)
        current_close = candles[i]["close"]
        if highest - lowest > 0:
            k = ((current_close - lowest) / (highest - lowest)) * 100
        else:
            k = 50
        k_values.append(k)
    d = sum(k_values[-d_period:]) / d_period if len(k_values) >= d_period else k_values[-1]
    return {"k": round(k_values[-1], 2), "d": round(d, 2)}


def _generate_recommendation(rsi: float, macd: dict, adx_data: dict, ema_trend: str, stoch: dict) -> tuple[str, str]:
    """
    Generate BUY/SELL/NEUTRAL recommendation based on multiple indicators.
    Returns (recommendation, strength).
    """
    buy_signals = 0
    sell_signals = 0

    # 1. RSI
    if rsi > 55:
        buy_signals += 1
    elif rsi < 45:
        sell_signals += 1

    # 2. MACD histogram
    if macd["histogram"] > 0:
        buy_signals += 1
    elif macd["histogram"] < 0:
        sell_signals += 1

    # 3. MACD line vs signal
    if macd["line"] > macd["signal"]:
        buy_signals += 1
    elif macd["line"] < macd["signal"]:
        sell_signals += 1

    # 4. EMA trend
    if ema_trend == "BULLISH":
        buy_signals += 1
    elif ema_trend == "BEARISH":
        sell_signals += 1

    # 5. ADX direction (+DI vs -DI)
    if adx_data["plus_di"] > adx_data["minus_di"]:
        buy_signals += 1
    elif adx_data["minus_di"] > adx_data["plus_di"]:
        sell_signals += 1

    # 6. Stochastic
    if stoch["k"] > 50 and stoch["k"] > stoch["d"]:
        buy_signals += 1
    elif stoch["k"] < 50 and stoch["k"] < stoch["d"]:
        sell_signals += 1

    # Determine recommendation
    if buy_signals >= 5:
        rec = "STRONG_BUY"
    elif buy_signals >= 4:
        rec = "BUY"
    elif sell_signals >= 5:
        rec = "STRONG_SELL"
    elif sell_signals >= 4:
        rec = "SELL"
    else:
        rec = "NEUTRAL"

    # Strength
    max_signals = max(buy_signals, sell_signals)
    if max_signals >= 5:
        strength = "STRONG"
    elif max_signals >= 4:
        strength = "MEDIUM"
    else:
        strength = "WEAK"

    return rec, strength


def get_full_analysis(symbol: str, timeframe: str = "H1", count: int = 200) -> dict:
    """
    Full technical analysis using broker candles — replaces TradingView.

    Returns same structure as the old TradingView-based analysis.
    """
    candle_result = bridge.get_candles(symbol, timeframe, count)

    if isinstance(candle_result, dict) and "error" in candle_result:
        return candle_result

    candles = candle_result.get("candles", []) if isinstance(candle_result, dict) else candle_result

    if len(candles) < 50:
        return {"error": f"Not enough candles ({len(candles)}). Need at least 50."}

    closes = [c["close"] for c in candles]

    # Calculate all indicators
    rsi = _calculate_rsi(closes, 14)
    macd = _calculate_macd(closes)
    adx_data = _calculate_adx(candles, 14)
    atr = _calculate_atr(candles, 14)
    stoch = _calculate_stochastic(candles, 14, 3)

    ema10 = _calculate_ema(closes, 10)
    ema20 = _calculate_ema(closes, 20)
    ema50 = _calculate_ema(closes, 50)
    ema100 = _calculate_ema(closes, 100)
    ema200 = _calculate_ema(closes, 200)

    # EMA trend
    if ema10 and ema20 and ema50:
        if ema10[-1] > ema20[-1] > ema50[-1]:
            ema_trend = "BULLISH"
        elif ema10[-1] < ema20[-1] < ema50[-1]:
            ema_trend = "BEARISH"
        else:
            ema_trend = "FLAT"
    else:
        ema_trend = "UNKNOWN"

    # Recommendation
    rec, strength = _generate_recommendation(rsi, macd, adx_data, ema_trend, stoch)

    pip_size = 0.01 if "JPY" in symbol else 0.0001
    current = candles[-1]

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "price": {
            "open": current["open"],
            "high": current["high"],
            "low": current["low"],
            "close": current["close"],
        },
        "indicators": {
            "rsi_14": rsi,
            "macd_histogram": macd["histogram"],
            "macd_signal": macd["signal"],
            "adx_14": adx_data["adx"],
            "adx_plus_di": adx_data["plus_di"],
            "adx_minus_di": adx_data["minus_di"],
            "atr_14": round(atr, 6),
            "atr_pips": round(atr / pip_size, 1),
            "ema_10": round(ema10[-1], 6) if ema10 else None,
            "ema_20": round(ema20[-1], 6) if ema20 else None,
            "ema_50": round(ema50[-1], 6) if ema50 else None,
            "ema_100": round(ema100[-1], 6) if ema100 else None,
            "ema_200": round(ema200[-1], 6) if ema200 else None,
            "stoch_k": stoch["k"],
            "stoch_d": stoch["d"],
        },
        "recommendation": rec,
        "strength": strength,
        "ema_trend": ema_trend,
    }
