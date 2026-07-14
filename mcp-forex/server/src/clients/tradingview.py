"""TradingView Technical Analysis wrapper for Forex."""

from tradingview_ta import TA_Handler, Interval

INTERVAL_MAP = {
    "5m": Interval.INTERVAL_5_MINUTES,
    "15m": Interval.INTERVAL_15_MINUTES,
    "1h": Interval.INTERVAL_1_HOUR,
    "4h": Interval.INTERVAL_4_HOURS,
    "1d": Interval.INTERVAL_1_DAY,
    "1w": Interval.INTERVAL_1_WEEK,
}


def get_analysis(symbol: str, timeframe: str = "1h") -> dict:
    """
    Get full technical analysis for a forex pair.

    Args:
        symbol: Forex pair without slash, e.g. "EURUSD"
        timeframe: "5m", "15m", "1h", "4h", "1d", "1w"

    Returns:
        Dict with price, indicators, recommendations.
    """
    interval = INTERVAL_MAP.get(timeframe)
    if not interval:
        return {"error": f"Invalid timeframe '{timeframe}'. Use: {list(INTERVAL_MAP.keys())}"}

    try:
        handler = TA_Handler(
            symbol=symbol,
            screener="forex",
            exchange="FX_IDC",
            interval=interval,
        )
        analysis = handler.get_analysis()
    except Exception as e:
        return {"error": f"TradingView error: {str(e)}"}

    indicators = analysis.indicators
    summary = analysis.summary

    # Determine strength
    buy_count = summary.get("BUY", 0)
    sell_count = summary.get("SELL", 0)
    max_signals = max(buy_count, sell_count)
    if max_signals >= 10:
        strength = "STRONG"
    elif max_signals >= 6:
        strength = "MEDIUM"
    else:
        strength = "WEAK"

    # EMA trend
    ema_8 = indicators.get("EMA8")
    ema_21 = indicators.get("EMA21")
    ema_50 = indicators.get("EMA50")
    if ema_8 and ema_21 and ema_50:
        if ema_8 > ema_21 > ema_50:
            ema_trend = "BULLISH"
        elif ema_8 < ema_21 < ema_50:
            ema_trend = "BEARISH"
        else:
            ema_trend = "FLAT"
    else:
        ema_trend = "UNKNOWN"

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "price": {
            "open": indicators.get("open"),
            "high": indicators.get("high"),
            "low": indicators.get("low"),
            "close": indicators.get("close"),
        },
        "indicators": {
            "rsi_14": round(indicators.get("RSI", 0), 2),
            "macd_histogram": round(indicators.get("MACD.macd", 0) - indicators.get("MACD.signal", 0), 6),
            "macd_signal": round(indicators.get("MACD.signal", 0), 6),
            "adx_14": round(indicators.get("ADX", 0), 2),
            "atr_14": round(indicators.get("ATR", 0), 6),
            "ema_8": ema_8,
            "ema_21": ema_21,
            "ema_50": ema_50,
            "ema_200": indicators.get("EMA200"),
            "bb_upper": indicators.get("BB.upper"),
            "bb_lower": indicators.get("BB.lower"),
            "stoch_k": round(indicators.get("Stoch.K", 0), 2),
            "stoch_d": round(indicators.get("Stoch.D", 0), 2),
            "cci_20": round(indicators.get("CCI20", 0), 2),
            "volume": indicators.get("volume"),
        },
        "moving_averages": {
            "recommendation": summary.get("RECOMMENDATION", "NEUTRAL"),
            "buy_count": buy_count,
            "sell_count": sell_count,
            "neutral_count": summary.get("NEUTRAL", 0),
        },
        "recommendation": summary.get("RECOMMENDATION", "NEUTRAL"),
        "strength": strength,
        "ema_trend": ema_trend,
    }
