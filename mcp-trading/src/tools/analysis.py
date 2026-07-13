"""Analysis tools — TradingView real-time technical analysis."""

import json
from tradingview_ta import TA_Handler, Interval

INTERVAL_MAP = {
    "5m": Interval.INTERVAL_5_MINUTES,
    "15m": Interval.INTERVAL_15_MINUTES,
    "1h": Interval.INTERVAL_1_HOUR,
    "4h": Interval.INTERVAL_4_HOURS,
    "1d": Interval.INTERVAL_1_DAY,
    "1w": Interval.INTERVAL_1_WEEK,
}


def _get_analysis(symbol: str, timeframe: str) -> dict:
    """Internal: fetch TradingView analysis for a symbol/timeframe."""
    interval = INTERVAL_MAP.get(timeframe)
    if not interval:
        return {"error": f"Invalid timeframe '{timeframe}'. Valid: {list(INTERVAL_MAP.keys())}"}

    try:
        handler = TA_Handler(
            symbol=symbol, screener="crypto", exchange="BINANCE", interval=interval
        )
        a = handler.get_analysis()
        ind = a.indicators

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "recommendation": a.summary["RECOMMENDATION"],
            "buy_signals": a.summary["BUY"],
            "sell_signals": a.summary["SELL"],
            "neutral_signals": a.summary["NEUTRAL"],
            "price": {
                "close": ind.get("close"),
                "open": ind.get("open"),
                "high": ind.get("high"),
                "low": ind.get("low"),
                "change_pct": ind.get("change"),
            },
            "oscillators": {
                "rsi_14": ind.get("RSI"),
                "stoch_k": ind.get("Stoch.K"),
                "stoch_d": ind.get("Stoch.D"),
                "cci_20": ind.get("CCI20"),
                "adx_14": ind.get("ADX"),
                "adx_plus_di": ind.get("ADX+DI"),
                "adx_minus_di": ind.get("ADX-DI"),
                "macd_line": ind.get("MACD.macd"),
                "macd_signal": ind.get("MACD.signal"),
                "momentum": ind.get("Mom"),
                "williams_r": ind.get("W.R"),
                "awesome_oscillator": ind.get("AO"),
            },
            "moving_averages": {
                "ema_10": ind.get("EMA10"),
                "ema_20": ind.get("EMA20"),
                "ema_50": ind.get("EMA50"),
                "ema_100": ind.get("EMA100"),
                "ema_200": ind.get("EMA200"),
                "sma_20": ind.get("SMA20"),
                "sma_50": ind.get("SMA50"),
                "sma_200": ind.get("SMA200"),
            },
            "volatility": {
                "bb_upper": ind.get("BB.upper"),
                "bb_lower": ind.get("BB.lower"),
                "atr_14": ind.get("ATR"),
            },
            "volume": ind.get("volume"),
        }
    except Exception as e:
        return {"error": str(e)}


def register_analysis_tools(mcp):
    """Register all analysis tools on the MCP server."""

    @mcp.tool()
    def coin_analysis(symbol: str, timeframe: str = "1h") -> str:
        """
        Get full technical analysis for a crypto pair from TradingView (real-time).

        Args:
            symbol: Trading pair, e.g. 'BTCUSDT', 'ETHUSDT'
            timeframe: '5m', '15m', '1h', '4h', '1d', '1w'

        Returns:
            Complete analysis: recommendation, oscillators, MAs, volatility, volume.
        """
        return json.dumps(_get_analysis(symbol, timeframe))

    @mcp.tool()
    def multi_timeframe_analysis(symbol: str) -> str:
        """
        Get multi-timeframe analysis (1D → 4H → 1H) for trend alignment.

        Args:
            symbol: Trading pair, e.g. 'BTCUSDT'

        Returns:
            Recommendation and key indicators per timeframe for top-down analysis.
        """
        results = {}
        for tf in ["1d", "4h", "1h"]:
            data = _get_analysis(symbol, tf)
            if "error" in data:
                results[tf] = data
            else:
                results[tf] = {
                    "recommendation": data["recommendation"],
                    "buy": data["buy_signals"],
                    "sell": data["sell_signals"],
                    "rsi": round(data["oscillators"]["rsi_14"] or 0, 2),
                    "macd": round(data["oscillators"]["macd_line"] or 0, 2),
                    "adx": round(data["oscillators"]["adx_14"] or 0, 2),
                    "ema_20": data["moving_averages"]["ema_20"],
                    "ema_50": data["moving_averages"]["ema_50"],
                    "close": data["price"]["close"],
                }
        return json.dumps({"symbol": symbol, "timeframes": results})

    @mcp.tool()
    def get_market_status() -> str:
        """
        Get current market overview — price and signal for all allowed symbols.

        Returns:
            Price, recommendation, and RSI for each configured trading pair.
        """
        from src.core.config import safety

        results = {}
        for symbol in safety.allowed_symbols:
            data = _get_analysis(symbol, "1h")
            if "error" in data:
                results[symbol] = data
            else:
                results[symbol] = {
                    "price": data["price"]["close"],
                    "recommendation": data["recommendation"],
                    "rsi": round(data["oscillators"]["rsi_14"] or 0, 2),
                    "adx": round(data["oscillators"]["adx_14"] or 0, 2),
                }
        return json.dumps(results)
