"""Trading tools — Binance Futures order execution with safety checks."""

import json
from datetime import datetime, timedelta, timezone

from src.core.database import db
from src.core.safety import SafetyGuard
from src.clients.binance import binance


def register_trading_tools(mcp):
    """Register all trading execution tools."""

    @mcp.tool()
    def open_position(symbol: str, side: str, lot_size: float = 0.01) -> str:
        """
        Open a position on Binance Futures with safety validation.

        Args:
            symbol: 'BTCUSDT' or 'ETHUSDT'
            side: 'BUY' (long) or 'SELL' (short)
            lot_size: Position size in USD-equivalent (default 0.01)

        Returns:
            Order confirmation with trade_id, entry price, and close_by time.
        """
        check = SafetyGuard.can_open_position(symbol, lot_size)
        if not check.allowed:
            return json.dumps({"error": check.reason})

        sym_info = binance.get_symbol_info(symbol)
        if "error" in sym_info:
            return json.dumps(sym_info)

        current_price = binance.get_price(symbol)
        precision = sym_info.get("quantity_precision", 3)
        quantity = round(lot_size / current_price, precision)

        if quantity < sym_info.get("min_qty", 0):
            quantity = sym_info["min_qty"]

        order = binance.open_market_order(symbol, side, quantity)
        if "error" in order:
            return json.dumps(order)

        entry_price = order["avg_price"] if order["avg_price"] > 0 else current_price

        trade_id = db.insert_trade(
            symbol=symbol,
            side=side.upper(),
            lot_size=lot_size,
            entry_price=entry_price,
            quantity=quantity,
            binance_order_id=order["order_id"],
        )

        close_by = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        return json.dumps({
            "success": True,
            "trade_id": trade_id,
            "symbol": symbol,
            "side": side.upper(),
            "entry_price": entry_price,
            "quantity": quantity,
            "lot_size": lot_size,
            "binance_order_id": order["order_id"],
            "close_by": close_by,
        })

    @mcp.tool()
    def close_position(trade_id: str) -> str:
        """
        Close a specific open trade.

        Args:
            trade_id: UUID of the trade from the database.

        Returns:
            Close confirmation with exit price, PnL, and holding time.
        """
        open_trades = db.get_open_trades()
        trade = next((t for t in open_trades if t["id"] == trade_id), None)

        if not trade:
            return json.dumps({"error": f"Trade '{trade_id}' not found or already closed"})

        close_side = "SELL" if trade["side"] == "BUY" else "BUY"
        order = binance.close_market_order(trade["symbol"], close_side, trade["quantity"])
        if "error" in order:
            return json.dumps(order)

        exit_price = order["avg_price"] if order["avg_price"] > 0 else binance.get_price(trade["symbol"])

        if trade["side"] == "BUY":
            pnl_usd = (exit_price - trade["entry_price"]) * trade["quantity"]
        else:
            pnl_usd = (trade["entry_price"] - exit_price) * trade["quantity"]

        db.close_trade(
            trade_id=trade_id,
            exit_price=exit_price,
            pnl_usd=round(pnl_usd, 4),
            binance_close_order_id=order.get("order_id"),
        )

        age_min = (datetime.now(timezone.utc) - datetime.fromisoformat(trade["opened_at"])).total_seconds() / 60

        return json.dumps({
            "success": True,
            "trade_id": trade_id,
            "symbol": trade["symbol"],
            "side": trade["side"],
            "entry_price": trade["entry_price"],
            "exit_price": exit_price,
            "pnl_usd": round(pnl_usd, 4),
            "holding_minutes": round(age_min, 1),
        })

    @mcp.tool()
    def close_all_positions(symbol: str = None) -> str:
        """
        Close all open positions (or filter by symbol).

        Args:
            symbol: Optional — only close positions for this symbol.

        Returns:
            Summary: count closed, total PnL.
        """
        open_trades = db.get_open_trades()
        if symbol:
            open_trades = [t for t in open_trades if t["symbol"] == symbol]

        if not open_trades:
            return json.dumps({"message": "No open positions to close", "closed_count": 0})

        results = []
        total_pnl = 0.0

        for trade in open_trades:
            result = json.loads(close_position(trade["id"]))
            results.append(result)
            if result.get("pnl_usd"):
                total_pnl += result["pnl_usd"]

        return json.dumps({
            "closed_count": len(results),
            "total_pnl_usd": round(total_pnl, 4),
            "details": results,
        })
