"""
SP500 Risk Calculator — Position sizing in Points (not Pips)
For US500Cash on XM: $1 per point per 1.0 lot
Config read from sp500_settings table, lot constraints read live from the broker.
"""
import json
import math
from src.clients import mt5_bridge
from src.clients.database import get_settings


def register_risk_tools(mcp):

    @mcp.tool()
    async def sp500_calculate_risk(sl_points: float, risk_percent: float = 0) -> str:
        """
        Calculate position size for SP500 based on account balance and SL in points.

        Args:
            sl_points: Stop loss distance in points (e.g., 20 = 20 points)
            risk_percent: Percentage of balance to risk (0 = use default from settings)

        Formula: lot_size = risk_usd / (sl_points * point_value_per_lot)
        For XM US500Cash: 1 lot = $1/point, so risk $10 with 20pt SL = 0.50 lots
        """
        settings = get_settings()
        POINT_VALUE = settings["point_value"]

        # Lot constraints come from the live broker, not DB defaults — XM's
        # lot_step for US500Cash is 0.1, not the 0.01 the old code assumed,
        # so rounding to 2 decimals produced sizes the broker would reject.
        symbol_info = await mt5_bridge.get_symbol_info()
        if "error" in symbol_info:
            MIN_LOT = settings["min_lot"]
            MAX_LOT = settings["max_lot"]
            LOT_STEP = 0.01
        else:
            MIN_LOT = float(symbol_info.get("min_lot", settings["min_lot"]))
            MAX_LOT = float(symbol_info.get("max_lot", settings["max_lot"]))
            LOT_STEP = float(symbol_info.get("lot_step", 0.01)) or 0.01

        if risk_percent <= 0:
            risk_percent = settings["max_risk_per_trade_pct"]

        account = await mt5_bridge.get_account_info()
        balance = float(account.get("balance", 0))

        if balance <= 0:
            return json.dumps({"error": "Cannot calculate — balance is zero or negative"})

        if sl_points <= 0:
            return json.dumps({"error": "SL points must be positive"})

        risk_usd = balance * (risk_percent / 100.0)
        raw_lot_size = risk_usd / (sl_points * POINT_VALUE)

        # Floor to the nearest broker lot_step (not a plain round — rounding
        # up can silently exceed the requested risk, and a size that isn't a
        # step multiple gets rejected outright by MT5).
        stepped_lot = math.floor(raw_lot_size / LOT_STEP) * LOT_STEP
        lot_size = max(MIN_LOT, min(MAX_LOT, stepped_lot))
        lot_size = round(lot_size, 2)

        # Actual risk with clamped lot
        actual_risk_usd = lot_size * sl_points * POINT_VALUE
        actual_risk_pct = (actual_risk_usd / balance) * 100

        return json.dumps({
            "balance": round(balance, 2),
            "risk_percent_requested": risk_percent,
            "risk_usd": round(risk_usd, 2),
            "sl_points": sl_points,
            "point_value_per_lot": POINT_VALUE,
            "calculated_lot_size": lot_size,
            "lot_size_raw": round(raw_lot_size, 4),
            "lot_step": LOT_STEP,
            "lot_clamped": lot_size != round(raw_lot_size, 2),
            "min_lot": MIN_LOT,
            "max_lot": MAX_LOT,
            "actual_risk_usd": round(actual_risk_usd, 2),
            "actual_risk_percent": round(actual_risk_pct, 2)
        })

    @mcp.tool()
    async def sp500_get_symbol_info() -> str:
        """
        Live broker specs for US500Cash: lot_step, min/max lot, spread, digits.
        Use to sanity-check lot sizes before opening a position — the broker
        rejects orders whose volume isn't a multiple of lot_step.
        """
        result = await mt5_bridge.get_symbol_info()
        return json.dumps(result)

    @mcp.tool()
    async def sp500_get_optimal_sl_tp(side: str, structure_sl_points: float = 0) -> str:
        """
        Calculate SL/TP for the once-daily strategy, same formula validated by
        the backtest (sp500-mcp-server/backtest/): SL = MAX(structure_sl_points,
        1.0x ATR(14) H1) — the structure distance floored by an ATR buffer so a
        full-session hold isn't stopped out by ordinary M5 noise. TP = SL *
        min_rr_ratio (from sp500_settings).

        Args:
            side: BUY or SELL
            structure_sl_points: Distance in points from current price to the
                spring/upthrust invalidation point (from sp500_market_structure's
                wyckoff.spring/upthrust.sl_suggested) — pass 0 to use ATR alone.
        """
        settings = get_settings(force_refresh=True)
        min_rr = float(settings.get("min_rr_ratio", 1.5))

        # ATR(14) on H1 — matches the backtest, not M5 (this is a session-length
        # hold, not a scalp, so the SL buffer should reflect H1-scale noise).
        data = await mt5_bridge.get_candles("H1", 30)
        candles = data.get("candles", [])
        if len(candles) < 15:
            return json.dumps({"error": "Insufficient H1 data for ATR calculation"})

        highs = [float(c["high"]) for c in candles]
        lows = [float(c["low"]) for c in candles]
        closes = [float(c["close"]) for c in candles]
        current_price = closes[-1]

        true_ranges = []
        for i in range(1, min(15, len(candles))):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1])
            )
            true_ranges.append(tr)
        atr_h1 = sum(true_ranges) / len(true_ranges) if true_ranges else 10.0

        sl_points = round(max(structure_sl_points, atr_h1, 3.0), 1)
        tp_points = round(sl_points * min_rr, 1)

        if side.upper() == "BUY":
            sl_price = round(current_price - sl_points, 2)
            tp_price = round(current_price + tp_points, 2)
        else:
            sl_price = round(current_price + sl_points, 2)
            tp_price = round(current_price - tp_points, 2)

        return json.dumps({
            "side": side.upper(),
            "current_price": round(current_price, 2),
            "atr_h1_14": round(atr_h1, 2),
            "structure_sl_points": structure_sl_points,
            "sl_points": sl_points,
            "sl_price": sl_price,
            "tp_points": tp_points,
            "tp_price": tp_price,
            "rr_ratio": min_rr,
            "note": "sl_points = MAX(structure_sl_points, ATR(14) H1). Pass the spring/upthrust sl_suggested distance as structure_sl_points.",
        })
