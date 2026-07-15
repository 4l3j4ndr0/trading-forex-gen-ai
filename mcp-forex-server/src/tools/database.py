"""Database tools — CRUD for trades, settings, logs, and performance."""

import os
import json
from datetime import datetime, timezone, timedelta

from src.core.db import execute, execute_one, execute_insert

USER_ID = os.getenv("USER_ID", "")


def _get_settings() -> dict:
    """Get trading settings for the current user."""
    row = execute_one("SELECT * FROM trading_settings WHERE user_id = %s", (USER_ID,))
    return row or {}


def register_database_tools(mcp):
    """Register all database tools."""

    @mcp.tool()
    def register_trade(
        ticket: int,
        symbol: str,
        side: str,
        lot_size: float,
        entry_price: float,
        sl_price: float,
        tp_price: float,
        sl_pips: float,
        tp_pips: float,
        risk_usd: float,
        comment: str = "",
        basket_id: str = None,
    ) -> str:
        """
        Register a new trade in the database.

        Args:
            ticket: MT5 ticket number
            symbol: Forex pair (EURUSD, etc)
            side: BUY or SELL
            lot_size: Position size in lots
            entry_price: Entry price
            sl_price: Stop Loss price
            tp_price: Take Profit price
            sl_pips: Stop loss in pips
            tp_pips: Take profit in pips
            risk_usd: Risk amount in USD
            comment: AI reasoning for the trade
            basket_id: Optional basket identifier to group hedged positions (e.g. 'EURUSD-20260714-001')

        Returns:
            Trade ID confirmation.
        """
        rr_ratio = round(tp_pips / sl_pips, 2) if sl_pips > 0 else 0

        # Get pair_id
        pair = execute_one("SELECT id FROM pairs WHERE symbol = %s", (symbol,))
        pair_id = pair["id"] if pair else 1

        row = execute_insert(
            """INSERT INTO trades (user_id, pair_id, ticket, side, lot_size, entry_price, sl_price, tp_price,
                sl_pips, tp_pips, risk_usd, rr_ratio, comment, basket_id, status, opened_at, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'open', NOW(), NOW())
            ON CONFLICT (ticket) DO UPDATE SET
                basket_id = COALESCE(EXCLUDED.basket_id, trades.basket_id),
                comment = COALESCE(EXCLUDED.comment, trades.comment),
                updated_at = NOW()
            RETURNING id""",
            (USER_ID, pair_id, ticket, side.upper(), lot_size, entry_price, sl_price, tp_price,
             sl_pips, tp_pips, risk_usd, rr_ratio, comment, basket_id)
        )

        return json.dumps({"trade_id": str(row["id"]), "basket_id": basket_id, "registered": True})

    @mcp.tool()
    def update_trade(
        trade_id: str,
        exit_price: float,
        pnl_pips: float,
        pnl_usd: float,
        close_reason: str = "manual",
    ) -> str:
        """
        Close/update a trade with exit data.

        Args:
            trade_id: UUID of the trade
            exit_price: Exit price
            pnl_pips: Profit/loss in pips
            pnl_usd: Profit/loss in USD
            close_reason: 'tp_hit', 'sl_hit', 'expired', 'manual', 'target_reached'

        Returns:
            Confirmation with holding time.
        """
        trade = execute_one("SELECT opened_at FROM trades WHERE id = %s AND user_id = %s", (trade_id, USER_ID))
        if not trade:
            return json.dumps({"error": f"Trade '{trade_id}' not found"})

        opened_at = trade["opened_at"]
        holding_minutes = (datetime.now(timezone.utc) - opened_at).total_seconds() / 60

        execute(
            """UPDATE trades SET exit_price = %s, pnl_pips = %s, pnl_usd = %s,
                close_reason = %s, status = 'closed', closed_at = NOW(),
                holding_minutes = %s, updated_at = NOW()
            WHERE id = %s""",
            (exit_price, pnl_pips, pnl_usd, close_reason, round(holding_minutes, 1), trade_id)
        )

        return json.dumps({"updated": True, "holding_minutes": round(holding_minutes, 1)})

    @mcp.tool()
    def get_trade_history(period: str = "today", symbol: str = None) -> str:
        """
        Get closed trade history with stats.

        Args:
            period: 'today', 'yesterday', '7d', '30d', 'all'
            symbol: Optional — filter by pair

        Returns:
            List of trades and aggregate statistics.
        """
        now = datetime.now(timezone.utc)
        if period == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "yesterday":
            start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            now = start + timedelta(days=1)
        elif period == "7d":
            start = now - timedelta(days=7)
        elif period == "30d":
            start = now - timedelta(days=30)
        else:
            start = datetime(2000, 1, 1, tzinfo=timezone.utc)

        query = """SELECT t.id, p.symbol, t.side, t.lot_size, t.entry_price, t.exit_price,
                    t.pnl_pips, t.pnl_usd, t.rr_ratio, t.holding_minutes, t.close_reason, t.closed_at
                FROM trades t JOIN pairs p ON t.pair_id = p.id
                WHERE t.user_id = %s AND t.status = 'closed' AND t.closed_at >= %s AND t.closed_at <= %s"""
        params = [USER_ID, start, now]

        if symbol:
            query += " AND p.symbol = %s"
            params.append(symbol)

        query += " ORDER BY t.closed_at DESC LIMIT 50"
        rows = execute(query, tuple(params))

        trades = []
        for r in rows:
            trades.append({
                "trade_id": str(r["id"]),
                "symbol": r["symbol"],
                "side": r["side"],
                "lot_size": float(r["lot_size"]) if r["lot_size"] else 0,
                "pnl_pips": float(r["pnl_pips"]) if r["pnl_pips"] else 0,
                "pnl_usd": float(r["pnl_usd"]) if r["pnl_usd"] else 0,
                "rr_ratio": float(r["rr_ratio"]) if r["rr_ratio"] else 0,
                "holding_minutes": float(r["holding_minutes"]) if r["holding_minutes"] else 0,
                "close_reason": r["close_reason"],
            })

        total_pnl = sum(t["pnl_usd"] for t in trades)
        wins = [t for t in trades if t["pnl_usd"] > 0]
        losses = [t for t in trades if t["pnl_usd"] <= 0]

        return json.dumps({
            "period": period,
            "symbol": symbol,
            "count": len(trades),
            "trades": trades,
            "stats": {
                "total_pnl_usd": round(total_pnl, 4),
                "wins": len(wins),
                "losses": len(losses),
                "win_rate": round(len(wins) / max(len(trades), 1) * 100, 1),
            },
        })

    @mcp.tool()
    def get_daily_pnl(date: str = None) -> str:
        """
        Get PnL summary for a specific day.

        Args:
            date: Date in YYYY-MM-DD format. Default: today.

        Returns:
            Realized PnL, trade count, best/worst trade.
        """
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        else:
            target_date = datetime.now(timezone.utc).date()

        rows = execute(
            "SELECT pnl_usd FROM trades WHERE user_id = %s AND status = 'closed' AND closed_at::date = %s",
            (USER_ID, target_date)
        )

        pnls = [float(r["pnl_usd"]) for r in rows if r["pnl_usd"] is not None]
        open_count = execute_one(
            "SELECT COUNT(*) as cnt FROM trades WHERE user_id = %s AND status = 'open'", (USER_ID,)
        )

        return json.dumps({
            "date": str(target_date),
            "realized_pnl": round(sum(pnls), 4),
            "trades_closed": len(pnls),
            "trades_open": open_count["cnt"] if open_count else 0,
            "best_trade": round(max(pnls), 4) if pnls else 0,
            "worst_trade": round(min(pnls), 4) if pnls else 0,
        })

    @mcp.tool()
    def get_performance_stats(period: str = "30d") -> str:
        """
        Get aggregate performance statistics.

        Args:
            period: '7d', '30d', '90d', 'all'

        Returns:
            Win rate, profit factor, avg PnL, max drawdown, consecutive stats.
        """
        now = datetime.now(timezone.utc)
        if period == "7d":
            start = now - timedelta(days=7)
        elif period == "30d":
            start = now - timedelta(days=30)
        elif period == "90d":
            start = now - timedelta(days=90)
        else:
            start = datetime(2000, 1, 1, tzinfo=timezone.utc)

        rows = execute(
            "SELECT pnl_usd FROM trades WHERE user_id = %s AND status = 'closed' AND closed_at >= %s ORDER BY closed_at ASC",
            (USER_ID, start)
        )

        if not rows:
            return json.dumps({"period": period, "total_trades": 0, "message": "No trades in this period"})

        pnls = [float(r["pnl_usd"]) for r in rows if r["pnl_usd"] is not None]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        # Max consecutive
        max_con_wins = max_con_losses = current_wins = current_losses = 0
        for p in pnls:
            if p > 0:
                current_wins += 1
                current_losses = 0
                max_con_wins = max(max_con_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_con_losses = max(max_con_losses, current_losses)

        # Max drawdown
        peak = max_dd = cumulative = 0.0
        for p in pnls:
            cumulative += p
            peak = max(peak, cumulative)
            max_dd = max(max_dd, peak - cumulative)

        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        pf = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0

        return json.dumps({
            "period": period,
            "total_trades": len(pnls),
            "win_rate": round(len(wins) / max(len(pnls), 1) * 100, 1),
            "profit_factor": pf,
            "total_pnl_usd": round(sum(pnls), 4),
            "avg_pnl_per_trade": round(sum(pnls) / len(pnls), 4),
            "max_consecutive_wins": max_con_wins,
            "max_consecutive_losses": max_con_losses,
            "current_consecutive_losses": current_losses,
            "max_drawdown_usd": round(max_dd, 4),
        })

    @mcp.tool()
    def log_hourly_decision(
        trades_opened: int = 0,
        trades_closed: int = 0,
        trades_skipped: int = 0,
        pnl_this_hour: float = 0.0,
        symbols_analyzed: str = None,
        market_context: str = None,
        decision_summary: str = None,
    ) -> str:
        """
        Log the agent's hourly decision for auditing.

        Args:
            trades_opened: Number of trades opened this cycle
            trades_closed: Number of trades closed this cycle
            trades_skipped: Opportunities skipped (no trade)
            pnl_this_hour: Realized PnL this hour
            symbols_analyzed: JSON string of pairs analyzed
            market_context: Brief market description
            decision_summary: What the agent decided and why

        Returns:
            Log ID and timestamp.
        """
        now = datetime.now(timezone.utc)
        hour = now.hour

        # Cumulative PnL today
        daily_rows = execute(
            "SELECT COALESCE(SUM(pnl_usd), 0) as total FROM trades WHERE user_id = %s AND status = 'closed' AND closed_at::date = %s",
            (USER_ID, now.date())
        )
        cumulative = float(daily_rows[0]["total"]) if daily_rows else 0

        # Open positions
        open_count = execute_one("SELECT COUNT(*) as cnt FROM trades WHERE user_id = %s AND status = 'open'", (USER_ID,))

        # Session
        sessions = []
        if 7 <= hour < 16:
            sessions.append("london")
        if 12 <= hour < 21:
            sessions.append("new_york")
        session = "overlap" if len(sessions) == 2 else (sessions[0] if sessions else "off_hours")

        row = execute_insert(
            """INSERT INTO hourly_logs (user_id, timestamp, utc_hour, session, open_positions,
                trades_opened, trades_closed, trades_skipped, pnl_this_hour,
                cumulative_pnl_today, symbols_analyzed, market_context, decision_summary, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING id""",
            (USER_ID, now, hour, session, open_count["cnt"] if open_count else 0,
             trades_opened, trades_closed, trades_skipped, pnl_this_hour,
             cumulative, symbols_analyzed, market_context, decision_summary)
        )

        return json.dumps({"logged": True, "log_id": str(row["id"]), "timestamp": now.isoformat(), "session": session})

    @mcp.tool()
    def get_daily_target_progress() -> str:
        """
        Get hour-by-hour progress toward the daily target.

        Returns:
            Target USD, progress by hour, current percentage.
        """
        today = datetime.now(timezone.utc).date()
        s = _get_settings()
        target_pct = float(s.get("daily_target_pct", 1.0))

        # Get balance from bridge
        from src.clients.mt5_bridge import bridge
        account = bridge.get_account()
        balance = account.get("balance", 10000) if "error" not in account else 10000
        target_usd = balance * target_pct / 100

        # Hourly logs for today
        logs = execute(
            "SELECT utc_hour, cumulative_pnl_today, trades_opened + trades_closed as trades FROM hourly_logs WHERE user_id = %s AND timestamp::date = %s ORDER BY utc_hour",
            (USER_ID, today)
        )

        # Current PnL
        daily_rows = execute(
            "SELECT COALESCE(SUM(pnl_usd), 0) as total FROM trades WHERE user_id = %s AND status = 'closed' AND closed_at::date = %s",
            (USER_ID, today)
        )
        current_pnl = float(daily_rows[0]["total"]) if daily_rows else 0

        progress = []
        for log in logs:
            progress.append({
                "hour": log["utc_hour"],
                "pnl_cumulative": float(log["cumulative_pnl_today"]) if log["cumulative_pnl_today"] else 0,
                "trades": log["trades"],
            })

        current_pct = round(current_pnl / target_usd * 100, 1) if target_usd > 0 else 0

        return json.dumps({
            "date": str(today),
            "target_pct": target_pct,
            "target_usd": round(target_usd, 2),
            "current_pnl": round(current_pnl, 4),
            "progress_pct": current_pct,
            "target_reached": current_pct >= 100,
            "progress": progress,
        })
