"""
SP500 Risk Calculator — Position sizing in Points (not Pips)
For US500Cash on XM: $1 per point per 1.0 lot
Config read from sp500_settings table
"""
import json
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
        MIN_LOT = settings["min_lot"]
        MAX_LOT = settings["max_lot"]

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

        # Clamp to min/max
        lot_size = max(MIN_LOT, min(MAX_LOT, raw_lot_size))
        # Round to 2 decimals (XM lot step for indices)
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
            "lot_clamped": lot_size != round(raw_lot_size, 2),
            "min_lot": MIN_LOT,
            "max_lot": MAX_LOT,
            "actual_risk_usd": round(actual_risk_usd, 2),
            "actual_risk_percent": round(actual_risk_pct, 2)
        })

    @mcp.tool()
    async def sp500_get_optimal_sl_tp(side: str) -> str:
        """
        Calculate optimal SL/TP levels based on ATR and structure for SP500.
        SL: 1.0-1.5x ATR(14) on M5, placed beyond structure.
        TP: Minimum 1.5:1 R:R, targeting next liquidity level.
        
        Args:
            side: BUY or SELL
        """
        # Get M5 candles for ATR calculation
        data = await mt5_bridge.get_candles("M5", 50)
        candles = data.get("candles", [])

        if len(candles) < 15:
            return json.dumps({"error": "Insufficient data for ATR calculation"})

        highs = [float(c["high"]) for c in candles]
        lows = [float(c["low"]) for c in candles]
        closes = [float(c["close"]) for c in candles]
        current_price = closes[-1]

        # ATR(14) calculation
        true_ranges = []
        for i in range(1, min(15, len(candles))):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            true_ranges.append(tr)

        atr = sum(true_ranges) / len(true_ranges) if true_ranges else 10.0

        # SL: 1.2x ATR (gives room for noise)
        sl_points = round(atr * 1.2, 1)

        # TP: minimum 1.5:1 R:R, ideally 2:1
        tp_points_min = round(sl_points * 1.5, 1)
        tp_points_ideal = round(sl_points * 2.0, 1)

        # Calculate actual price levels
        if side.upper() == "BUY":
            sl_price = round(current_price - sl_points, 2)
            tp_price_min = round(current_price + tp_points_min, 2)
            tp_price_ideal = round(current_price + tp_points_ideal, 2)
        else:
            sl_price = round(current_price + sl_points, 2)
            tp_price_min = round(current_price - tp_points_min, 2)
            tp_price_ideal = round(current_price - tp_points_ideal, 2)

        return json.dumps({
            "side": side.upper(),
            "current_price": round(current_price, 2),
            "atr_m5_14": round(atr, 2),
            "sl_points": sl_points,
            "sl_price": sl_price,
            "tp_points_min": tp_points_min,
            "tp_price_min": tp_price_min,
            "tp_points_ideal": tp_points_ideal,
            "tp_price_ideal": tp_price_ideal,
            "rr_min": "1.5:1",
            "rr_ideal": "2:1",
            "note": "Place SL beyond nearest structure (swing high/low). Adjust TP to next liquidity level."
        })
