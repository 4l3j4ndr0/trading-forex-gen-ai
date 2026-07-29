"""
Trade Quality Score — shared rubric used by BOTH the live get_trade_quality_score()
MCP tool (src/tools/smart.py) and the backtest engine (backtest/engine.py).

Single source of truth so the two can never silently diverge: the live agent
and the backtest are always scoring setups the exact same way. Live callers
fetch current data from the bridge (candles=None); the backtest passes
pre-sliced historical candle windows with no lookahead.

Rubric (AGENT_PROMPT_V2.md Paso 4):
  +1 H4 bias matches trade direction — MANDATORY, no trade without this
  +1 price inside an unmitigated H4/D1 Order Block or unfilled FVG (POI)
  +1 M15 BOS/CHoCH confirmed in trade direction, still fresh
  +1 H1 RSI divergence in favor
  +1 pair is in the optimal session for right now
"""

from datetime import datetime, timezone

import pytz

from src.clients.local_indicators import get_full_analysis
from src.clients.mt5_bridge import bridge
from src.tools.market_data import _analyze_market_structure

SESSION_PAIRS = {
    "sydney": {"AUDUSD", "NZDUSD"},
    "tokyo": {"USDJPY", "AUDUSD", "GBPJPY"},
    "london": {"EURUSD", "GBPUSD", "EURGBP", "USDCAD", "USDCHF"},
    "new_york": {"EURUSD", "GBPUSD", "USDJPY", "USDCAD", "GBPJPY"},
}
TOKYO_TZ = pytz.timezone("Asia/Tokyo")
LONDON_TZ = pytz.timezone("Europe/London")
NY_TZ = pytz.timezone("America/New_York")
SYDNEY_TZ = pytz.timezone("Australia/Sydney")

FRESH_M15_CANDLES = 8  # ~2 hours — how recent a BOS/CHoCH trigger must be to still count


def active_sessions(dt_utc: datetime) -> set[str]:
    from datetime import time as dt_time
    sessions = set()
    if dt_time(9, 0) <= dt_utc.astimezone(TOKYO_TZ).time() <= dt_time(18, 0):
        sessions.add("tokyo")
    if dt_time(8, 0) <= dt_utc.astimezone(LONDON_TZ).time() <= dt_time(17, 0):
        sessions.add("london")
    if dt_time(8, 0) <= dt_utc.astimezone(NY_TZ).time() <= dt_time(17, 0):
        sessions.add("new_york")
    if dt_time(7, 0) <= dt_utc.astimezone(SYDNEY_TZ).time() <= dt_time(16, 0):
        sessions.add("sydney")
    return sessions


def optimal_pairs_now(dt_utc: datetime) -> set[str]:
    optimal = set()
    for s in active_sessions(dt_utc):
        optimal |= SESSION_PAIRS.get(s, set())
    return optimal


def pip_size(symbol: str) -> float:
    return 0.01 if "JPY" in symbol else 0.0001


def near_poi(price: float, structure: dict, side: str, atr_price: float) -> bool:
    """Is price inside (or within ~0.3xATR of) an unmitigated OB / unfilled FVG
    matching the trade direction?"""
    if not structure:
        return False
    want_ob = "bullish_ob" if side == "BUY" else "bearish_ob"
    want_fvg = "bullish_fvg" if side == "BUY" else "bearish_fvg"
    buf = atr_price * 0.3
    for ob in structure.get("order_blocks", []):
        if ob["type"] == want_ob and (ob["low"] - buf) <= price <= (ob["high"] + buf):
            return True
    for fvg in structure.get("fair_value_gaps", []):
        if fvg["type"] == want_fvg and (fvg["bottom"] - buf) <= price <= (fvg["top"] + buf):
            return True
    return False


def multi_tf_score(analyses: dict[str, dict]) -> int:
    """Sum of D1+H4+H1 recommendation contributions, same as forex_multi_timeframe()."""
    score = 0
    for a in analyses.values():
        if not a:
            continue
        rec = a.get("recommendation")
        score += 1 if rec in ("BUY", "STRONG_BUY") else -1 if rec in ("SELL", "STRONG_SELL") else 0
    return score


def _structure_live(symbol: str, timeframe: str, lookback: int = 100) -> dict | None:
    result = bridge.get_candles(symbol, timeframe, min(lookback, 200))
    if isinstance(result, dict) and "error" in result:
        return None
    candles = result.get("candles", []) if isinstance(result, dict) else result
    structure = _analyze_market_structure(candles, symbol, timeframe)
    return None if "error" in structure else structure


def evaluate_setup(
    symbol: str,
    candles_by_tf: dict[str, list[dict]] = None,
    dt_utc: datetime = None,
    min_adx_entry: float = 15.0,
) -> dict:
    """
    Determine trade direction from H4 bias and compute the Trade Quality Score.

    Args:
        candles_by_tf: Optional {"D1": [...], "H4": [...], "H1": [...], "M15": [...]}
            pre-sliced candle windows for backtesting. When None, fetches live
            data from the bridge (same as the MCP tools do by default).
        dt_utc: Timestamp to evaluate session-optimality at. Defaults to now.
        min_adx_entry: ADX floor (normally read from trading_settings by the caller).

    Returns:
        {"no_setup": reason} if there's no valid H4 bias / direction to trade,
        otherwise {"side", "score", "breakdown", "align_score", "rsi_d1", "adx_h1",
        "current_price", "atr_price", "h1_structure"}.
    """
    dt_utc = dt_utc or datetime.now(timezone.utc)
    cbt = candles_by_tf or {}

    def full(tf):
        return get_full_analysis(symbol, tf, candles=cbt.get(tf))

    def structure(tf, lookback=100):
        if candles_by_tf is not None:
            sl = cbt.get(tf, [])
            if len(sl) < 30:
                return None
            result = _analyze_market_structure(sl, symbol, tf)
            return None if "error" in result else result
        return _structure_live(symbol, tf, lookback)

    h4_structure = structure("H4")
    if not h4_structure or h4_structure["bias"] not in ("BUY", "SELL"):
        return {"no_setup": "H4 sin bias claro (RANGING) — nunca operar contra/sin H4"}
    side = h4_structure["bias"]

    d1_analysis, h4_analysis, h1_analysis = full("D1"), full("H4"), full("H1")
    if not d1_analysis or not h1_analysis:
        return {"no_setup": "Datos D1/H1 no disponibles"}

    align_score = multi_tf_score({"D1": d1_analysis, "H4": h4_analysis, "H1": h1_analysis})
    if (side == "BUY" and align_score < 0) or (side == "SELL" and align_score > 0):
        return {"no_setup": f"H4 bias ({side}) contradice la alineacion D1+H4+H1 ({align_score})"}

    adx = h1_analysis["indicators"]["adx_14"]
    if adx < min_adx_entry and abs(align_score) < 1:
        return {"no_setup": f"ADX bajo ({adx:.1f}) sin alineacion de respaldo"}

    rsi_d1 = d1_analysis["indicators"]["rsi_14"]
    if side == "SELL" and rsi_d1 < 30:
        return {"no_setup": f"RSI D1 en sobreventa ({rsi_d1:.1f}) — regla absoluta, no SELL"}
    if side == "BUY" and rsi_d1 > 70:
        return {"no_setup": f"RSI D1 en sobrecompra ({rsi_d1:.1f}) — regla absoluta, no BUY"}

    d1_structure = structure("D1")
    m15_structure = structure("M15", lookback=100)
    if not m15_structure:
        return {"no_setup": "Datos M15 no disponibles"}

    current_price = m15_structure["current_price"]
    atr_price = h1_analysis["indicators"]["atr_14"]

    breakdown = {"h4_bias": True}  # mandatory, already guaranteed by construction
    if near_poi(current_price, h4_structure, side, atr_price) or near_poi(current_price, d1_structure or {}, side, atr_price):
        breakdown["poi"] = True
    m15_bos, m15_choch = m15_structure["structure"]["bos"], m15_structure["structure"]["choch"]
    want_bos = "bullish" if side == "BUY" else "bearish"
    want_choch = "bullish_choch" if side == "BUY" else "bearish_choch"
    if (m15_bos and m15_bos["type"] == want_bos and m15_bos["candles_ago"] <= FRESH_M15_CANDLES) or \
       (m15_choch and m15_choch["type"] == want_choch and m15_choch["candles_ago"] <= FRESH_M15_CANDLES):
        breakdown["m15_bos_choch"] = True
    if any(d.get("signal") == side for d in h1_analysis.get("divergences", [])):
        breakdown["rsi_divergence"] = True
    if symbol in optimal_pairs_now(dt_utc):
        breakdown["optimal_session"] = True

    score = len(breakdown)

    return {
        "side": side,
        "score": score,
        "breakdown": breakdown,
        "align_score": align_score,
        "rsi_d1": rsi_d1,
        "adx_h1": adx,
        "current_price": current_price,
        "atr_price": atr_price,
        "h1_analysis": h1_analysis,
        "h1_structure": structure("H1"),
    }
