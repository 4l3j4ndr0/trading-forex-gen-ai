"""
SP500 Trading Tools — Position management for US500Cash
Uses the same MT5 Bridge but with index-specific logic
"""
import json
import os
from datetime import datetime, timedelta, timezone, time as dtime

import psycopg2
import psycopg2.extras
import pytz

from src.clients import mt5_bridge
from src.clients.database import get_settings

DATABASE_URL = os.getenv("DATABASE_URL", "")
USER_ID = os.getenv("USER_ID", "5f7b54c4-3bb5-487e-897e-e273112a914b")
NY_TZ = pytz.timezone("America/New_York")


def _trades_opened_today_et() -> int:
    """Count sp500_trades opened during the current ET calendar day."""
    now_utc = datetime.now(timezone.utc)
    today_et = now_utc.astimezone(NY_TZ).date()
    day_start_utc = NY_TZ.localize(datetime.combine(today_et, dtime.min)).astimezone(timezone.utc)
    day_end_utc = day_start_utc + timedelta(days=1)
    with psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) as cnt FROM sp500_trades WHERE user_id = %s AND opened_at >= %s AND opened_at < %s",
                (USER_ID, day_start_utc, day_end_utc),
            )
            row = cur.fetchone()
    return row["cnt"] if row else 0


def register_trading_tools(mcp):

    @mcp.tool()
    async def sp500_open_position(side: str, lot_size: float, sl_points: float = 0, tp_points: float = 0, comment: str = "") -> str:
        """
        Open a position on US500Cash.

        Args:
            side: BUY or SELL
            lot_size: Position size (calculated by sp500_calculate_risk)
            sl_points: Stop loss in points from entry
            tp_points: Take profit in points from entry
            comment: Trade justification (include SMC reasoning)
        """
        if side.upper() not in ("BUY", "SELL"):
            return json.dumps({"error": "Side must be BUY or SELL"})

        if lot_size <= 0:
            return json.dumps({"error": "Lot size must be positive. Use sp500_calculate_risk() first."})

        # Hard block in code, not just prompt-advisory — this system has zero
        # operational track record so far, don't rely on the LLM alone to
        # respect kill_switch/auto_trading_enabled.
        settings = get_settings(force_refresh=True)
        if settings.get("kill_switch"):
            return json.dumps({"error": "BLOCKED: kill_switch is active in sp500_settings"})
        if not settings.get("auto_trading_enabled", True):
            return json.dumps({"error": "BLOCKED: auto_trading_enabled is false in sp500_settings"})

        # Hard cap: 1 trade per ET calendar day — central to the once-daily
        # redesign, enforced here too (not just advisory via
        # sp500_check_trading_allowed) for the same zero-trust reason.
        trades_today = _trades_opened_today_et()
        if trades_today >= 1:
            return json.dumps({"error": f"BLOCKED: tope diario alcanzado ({trades_today} trade(s) ya abiertos hoy, ET)"})

        result = await mt5_bridge.open_position(
            side=side.upper(),
            lot_size=lot_size,
            sl_points=sl_points,
            tp_points=tp_points,
            comment=f"[SP500] {comment}"
        )
        return json.dumps(result)

    @mcp.tool()
    async def sp500_close_position(ticket: int, reason: str = "") -> str:
        """
        Close a specific SP500 position by ticket number.
        
        Args:
            ticket: MT5 position ticket
            reason: Why closing (e.g., 'structure_invalidated', 'target_reached', 'hedge_unlock')
        """
        result = await mt5_bridge.close_position(ticket, reason)
        return json.dumps(result)

    @mcp.tool()
    async def sp500_modify_position(ticket: int, sl_price: float = 0, tp_price: float = 0) -> str:
        """
        Modify SL/TP of an open SP500 position.
        Use for trailing stop or moving SL to breakeven.
        
        Args:
            ticket: MT5 position ticket
            sl_price: New SL price (0 = don't change)
            tp_price: New TP price (0 = don't change)
        """
        result = await mt5_bridge.modify_position(ticket, sl=sl_price, tp=tp_price)
        return json.dumps(result)

    @mcp.tool()
    async def sp500_get_positions() -> str:
        """
        Get all open SP500 positions with P&L details.
        Only returns US500Cash positions.
        """
        result = await mt5_bridge.get_positions("US500Cash")
        positions = result.get("positions", [])

        total_pnl = sum(float(p.get("profit", 0)) for p in positions)
        total_lots = sum(float(p.get("lot_size", 0)) for p in positions)

        buy_legs = [p for p in positions if p.get("side", "").upper() == "BUY"]
        sell_legs = [p for p in positions if p.get("side", "").upper() == "SELL"]

        is_hedged = bool(buy_legs and sell_legs)
        net_lots = sum(float(p.get("lot_size", 0)) for p in buy_legs) - sum(float(p.get("lot_size", 0)) for p in sell_legs)

        return json.dumps({
            "symbol": "US500Cash",
            "total_positions": len(positions),
            "total_pnl": round(total_pnl, 2),
            "total_lots": round(total_lots, 2),
            "net_lots": round(net_lots, 2),
            "is_hedged": is_hedged,
            "buy_legs": len(buy_legs),
            "sell_legs": len(sell_legs),
            "positions": positions
        })

    @mcp.tool()
    async def sp500_get_account() -> str:
        """
        Get account info: balance, equity, margin, free margin.

        Note on trade_mode: this is the ACCOUNT type flag (0=DEMO, 1=CONTEST,
        2=REAL) — it is NOT a "trading disabled" signal. A demo account
        (trade_mode=0) trades normally. Don't infer trading is blocked from
        this field; a rejected order's real reason comes from the error
        message returned by sp500_open_position, never from trade_mode.
        """
        result = await mt5_bridge.get_account_info()
        if "error" not in result and "trade_mode" in result:
            result["account_type"] = {0: "DEMO", 1: "CONTEST", 2: "REAL"}.get(
                result["trade_mode"], f"UNKNOWN({result['trade_mode']})"
            )
        return json.dumps(result)
