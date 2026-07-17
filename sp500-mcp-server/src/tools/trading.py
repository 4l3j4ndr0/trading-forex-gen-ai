"""
SP500 Trading Tools — Position management for US500Cash
Uses the same MT5 Bridge but with index-specific logic
"""
import json
from src.clients import mt5_bridge


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
        """
        result = await mt5_bridge.get_account_info()
        return json.dumps(result)
