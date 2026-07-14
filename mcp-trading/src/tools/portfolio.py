"""Portfolio tools — positions, history, performance, and logging."""

import json
from datetime import datetime, timezone

from src.core.database import db
from src.clients.binance import binance


def register_portfolio_tools(mcp):
    """Register all portfolio management tools."""

    @mcp.tool()
    def get_open_positions() -> str:
        """
        Get all open positions with live PnL from Binance.

        Returns:
            List of open trades with entry, current price, unrealized PnL, and age.
        """
        trades = db.get_open_trades()
        now = datetime.now(timezone.utc)
        positions = []

        for t in trades:
            try:
                current_price = binance.get_price(t["symbol"])
            except Exception:
                current_price = t["entry_price"]

            if t["side"] == "BUY":
                pnl = (current_price - t["entry_price"]) * t["quantity"]
            else:
                pnl = (t["entry_price"] - current_price) * t["quantity"]

            age_min = (now - datetime.fromisoformat(t["opened_at"])).total_seconds() / 60

            positions.append({
                "trade_id": t["id"],
                "symbol": t["symbol"],
                "side": t["side"],
                "entry_price": t["entry_price"],
                "current_price": current_price,
                "quantity": t["quantity"],
                "pnl_usd": round(pnl, 4),
                "age_minutes": round(age_min, 1),
                "close_by": t["close_by"],
                "decision_reason": t["decision_reason"],
                "expired": age_min >= 55,
            })

        return json.dumps({"open_count": len(positions), "positions": positions})

    @mcp.tool()
    def get_account_balance() -> str:
        """
        Get Binance Futures account balance.

        Returns:
            Total balance, available margin, unrealized PnL.
        """
        return json.dumps(binance.get_balance())

    @mcp.tool()
    def trade_history(period: str = "today", symbol: str = None) -> str:
        """
        Get closed trade history for a period.

        Args:
            period: 'today', 'yesterday', '7d', '30d'
            symbol: Optional — filter by symbol.

        Returns:
            Trades list with aggregate stats (win_rate, total PnL).
        """
        trades = db.get_trade_history(period, symbol)
        total_pnl = sum(t["pnl_usd"] or 0 for t in trades)
        wins = sum(1 for t in trades if (t["pnl_usd"] or 0) > 0)

        return json.dumps({
            "period": period,
            "symbol": symbol,
            "count": len(trades),
            "trades": trades,
            "stats": {
                "wins": wins,
                "losses": len(trades) - wins,
                "win_rate": round(wins / max(len(trades), 1) * 100, 1),
                "total_pnl_usd": round(total_pnl, 4),
                "avg_pnl_usd": round(total_pnl / max(len(trades), 1), 4),
            },
        })

    @mcp.tool()
    def performance_stats() -> str:
        """
        Get performance statistics: today, this week, and all-time.

        Returns:
            Win rate, PnL, best/worst trades, consecutive losses.
        """
        return json.dumps(db.get_performance_stats())

    @mcp.tool()
    def log_hourly_decision(
        trades_opened: int = 0,
        trades_closed: int = 0,
        trades_skipped: int = 0,
        pnl_this_hour: float = None,
        symbols_analyzed: str = None,
        market_context: str = None,
    ) -> str:
        """
        Log the agent's hourly decision for auditing.

        Args:
            trades_opened: Trades opened this cycle
            trades_closed: Trades closed this cycle
            trades_skipped: Opportunities skipped
            pnl_this_hour: Realized PnL this hour
            symbols_analyzed: JSON summary of analysis
            market_context: Brief market description
        """
        balance = binance.get_balance()
        open_trades = db.get_open_trades()

        db.insert_hourly_log(
            balance_usd=balance.get("total_balance"),
            equity_usd=balance.get("total_margin_balance"),
            open_positions=len(open_trades),
            trades_opened=trades_opened,
            trades_closed=trades_closed,
            trades_skipped=trades_skipped,
            pnl_this_hour=pnl_this_hour,
            cumulative_pnl=db.get_daily_pnl(),
            symbols_analyzed=symbols_analyzed,
            market_context=market_context,
        )
        return json.dumps({"logged": True, "timestamp": datetime.now(timezone.utc).isoformat()})
