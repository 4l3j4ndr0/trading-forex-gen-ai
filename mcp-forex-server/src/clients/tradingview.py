"""TradingView Technical Analysis wrapper for Forex."""

import time
from tradingview_ta import TA_Handler, Interval

INTERVAL_MAP = {
    "5m": Interval.INTERVAL_5_MINUTES,
    "15m": Interval.INTERVAL_15_MINUTES,
    "1h": Interval.INTERVAL_1_HOUR,
    "4h": Interval.INTERVAL_4_HOURS,
    "1d": Interval.INTERVAL_1_DAY,
    "1w": Interval.INTERVAL_1_WEEK,
}

# Rate limiting — max 1 request per 1.5 seconds
_last_request_time = 0.0
_MIN_INTERVAL = 1.5  # seconds between requests
_MAX_RETRIES = 2


def _rate_limit():
    """Ensure minimum interval between TradingView requests."""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_request_time = time.time()


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

    last_error = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            _rate_limit()
            handler = TA_Handler(
                symbol=symbol,
                screener="forex",
                exchange="FX_IDC",
                interval=interval,
            )
            analysis = handler.get_analysis()
            break
        except Exception as e:
            last_error = str(e)
            if attempt < _MAX_RETRIES:
                time.sleep(2 * (attempt + 1))  # backoff: 2s, 4s
            continue
    else:
        return {"error": f"TradingView error after {_MAX_RETRIES + 1} attempts: {last_error}"}

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
    ema_10 = indicators.get("EMA10")
    ema_20 = indicators.get("EMA20")
    ema_50 = indicators.get("EMA50")
    ema_200 = indicators.get("EMA200")
    if ema_10 and ema_20 and ema_50:
        if ema_10 > ema_20 > ema_50:
            ema_trend = "BULLISH"
        elif ema_10 < ema_20 < ema_50:
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
            "macd_histogram": round((indicators.get("MACD.macd", 0) or 0) - (indicators.get("MACD.signal", 0) or 0), 6),
            "macd_signal": round(indicators.get("MACD.signal", 0) or 0, 6),
            "adx_14": round(indicators.get("ADX", 0) or 0, 2),
            "adx_plus_di": round(indicators.get("ADX+DI", 0) or 0, 2),
            "adx_minus_di": round(indicators.get("ADX-DI", 0) or 0, 2),
            "ema_10": ema_10,
            "ema_20": ema_20,
            "ema_50": ema_50,
            "ema_100": indicators.get("EMA100"),
            "ema_200": ema_200,
            "sma_20": indicators.get("SMA20"),
            "sma_50": indicators.get("SMA50"),
            "sma_200": indicators.get("SMA200"),
            "bb_upper": indicators.get("BB.upper"),
            "bb_lower": indicators.get("BB.lower"),
            "stoch_k": round(indicators.get("Stoch.K", 0) or 0, 2),
            "stoch_d": round(indicators.get("Stoch.D", 0) or 0, 2),
            "cci_20": round(indicators.get("CCI20", 0) or 0, 2),
            "ao": indicators.get("AO"),
            "momentum": indicators.get("Mom"),
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
