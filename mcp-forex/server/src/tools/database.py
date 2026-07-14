"""Database tools — CRUD for trades, settings, logs, and performance."""

import json
from datetime import datetime, timezone, timedelta

from src.core.db import execute, execute_one, execute_insert


def register_database_tools(mcp):
    """Register all database tools."""

    @mcp.tool()
    def get_trading_settings(category: str = None) -> str:
        """
        Get all trading settings or filter by category.

        Args:
            category: Optional filter — 'risk', 'sizing', 'session', 'pairs', 'target', 'filters', 'system'

        Returns:
            All settings grouped by category.
        """
        if category:
            rows = execute(
                "SELECT key, value, description, category FROM trading_settings WHERE category = %s ORDER BY key",
                (category,)
            )
        else:
            rows = execute("SELECT key, value, description, category FROM trading_settings ORDER BY category, key")

        # Group by category
        grouped = {}
        for r in rows:
            cat = r["category"]
            if cat not in grouped:
                grouped[cat] = {}
            # Try to cast value to number
            val = r["value"]
            try:
                if "." in val:
                    val = float(val)
                else:
                    val = int(val)
            except (ValueError, TypeError):
                if val == "true":
                    val = True
                elif val == "false":
                    val = False
            grouped[cat][r["key"]] = val

        return json.dumps({"settings": grouped})

    @mcp.tool()
    def update_trading_setting(key: str, value: str) -> str:
        """
        Update a specific trading setting.

        Args:
            key: Setting key (e.g. 'max_lot_size', 'kill_switch', 'allowed_pairs')
            value: New value as string

        Returns:
            Confirmation with old and new value.
        """
        current = execute_one("SELECT value, category FROM trading_settings WHERE key = %s", (key,))
        if not current:
            return json.dumps({"error": f"Setting '{key}' not found"})

        execute(
            "UPDATE trading_settings SET value = %s, updated_at = NOW() WHERE key = %s",
            (value, key)
        )

        return json.dumps({
            "updated": True,
            "key": key,
            "old_value": current["value"],
            "new_value": value,
            "category": current["category"],
        })

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
    ) -> str:
        """
        Register a new trade in the database.

        Args:
            ticket: MT5 ticket number
            symbol: Forex pair (EURUSD, etc)
            side: BUY or SELL
            lot_size: Position size in lots
            entry_price: Entry price
            sl_price: Stop loss price
            tp_price: Take profit price
            sl_pips: Stop loss in pips
            tp_pips: Take profit in pips
            risk_usd: Risk amount in USD
            comment: AI reasoning for the trade

        Returns:
            Trade ID confirmation.
        """
        rr_ratio = round(tp_pips / sl_pips, 2) if sl_pips > 0 else 0

        row = execute_insert(
            """INSERT INTO trades (ticket, symbol, side, lot_size, entry_price, sl_price, tp_price,
                sl_pips, tp_pips, risk_usd, rr_ratio, comment, status, opened_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'open', NOW())
            RETURNING id""",
            (ticket, symbol, side.upper(), lot_size, entry_price, sl_price, tp_price,
             sl_pips, tp_pips, risk_usd, rr_ratio, comment)
        )

        return json.dumps({"trade_id": str(row["id"]), "registered": True})

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
        trade = execute_one("SELECT opened_at FROM trades WHERE id = %s", (trade_id,))
        if not trade:
            return json.dumps({"error": f"Trade '{trade_id}' not found"})

        opened_at = trade["opened_at"]
        holding_minutes = (datetime.now(timezone.utc) - opened_at).total_seconds() / 60

        execute(
            """UPDATE trades SET exit_price = %s, pnl_pips = %s, pnl_usd = %s,
                close_reason = %s, status = 'closed', closed_at = NOW(),
                holding_minutes = %s
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

        query = """SELECT id, symbol, side, lot_size, entry_price, exit_price,
                    pnl_pips, pnl_usd, rr_ratio, holding_minutes, close_reason, closed_at
                FROM trades WHERE status = 'closed' AND closed_at >= %s AND closed_at <= %s"""
        params = [start, now]

        if symbol:
            query += " AND symbol = %s"
            params.append(symbol)

        query += " ORDER BY closed_at DESC"
        rows = execute(query, tuple(params))

        # Serialize
        trades = []
        for r in rows:
            trades.append({
                "trade_id": str(r["id"]),
                "symbol": r["symbol"],
                "side": r["side"],
                "lot_size": float(r["lot_size"]),
                "pnl_pips": float(r["pnl_pips"]) if r["pnl_pips"] else 0,
                "pnl_usd": float(r["pnl_usd"]) if r["pnl_usd"] else 0,
                "rr_ratio": float(r["rr_ratio"]) if r["rr_ratio"] else 0,
                "holding_minutes": float(r["holding_minutes"]) if r["holding_minutes"] else 0,
                "close_reason": r["close_reason"],
            })

        # Stats
        total_pnl = sum(t["pnl_usd"] for t in trades)
        wins = [t for t in trades if t["pnl_usd"] > 0]
        losses = [t for t in trades if t["pnl_usd"] <= 0]
        avg_win = sum(t["pnl_usd"] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t["pnl_usd"] for t in losses) / len(losses) if losses else 0
        profit_factor = abs(sum(t["pnl_usd"] for t in wins) / sum(t["pnl_usd"] for t in losses)) if losses and sum(t["pnl_usd"] for t in losses) != 0 else 0

        return json.dumps({
            "period": period,
            "symbol": symbol,
            "count": len(trades),
            "trades": trades[:50],  # Limit response size
            "stats": {
                "total_pnl_usd": round(total_pnl, 4),
                "wins": len(wins),
                "losses": len(losses),
                "win_rate": round(len(wins) / max(len(trades), 1) * 100, 1),
                "avg_winner": round(avg_win, 4),
                "avg_loser": round(avg_loss, 4),
                "profit_factor": round(profit_factor, 2),
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
            """SELECT pnl_usd FROM trades
            WHERE status = 'closed' AND closed_at::date = %s""",
            (target_date,)
        )

        pnls = [float(r["pnl_usd"]) for r in rows if r["pnl_usd"] is not None]
        open_count = execute_one(
            "SELECT COUNT(*) as cnt FROM trades WHERE status = 'open'", ()
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
            """SELECT pnl_usd, pnl_pips, rr_ratio, closed_at
            FROM trades WHERE status = 'closed' AND closed_at >= %s
            ORDER BY closed_at ASC""",
            (start,)
        )

        if not rows:
            return json.dumps({"period": period, "total_trades": 0, "message": "No trades in this period"})

        pnls = [float(r["pnl_usd"]) for r in rows if r["pnl_usd"] is not None]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        # Max consecutive
        max_con_wins = 0
        max_con_losses = 0
        current_wins = 0
        current_losses = 0
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
        peak = 0
        max_dd = 0
        cumulative = 0
        for p in pnls:
            cumulative += p
            peak = max(peak, cumulative)
            dd = peak - cumulative
            max_dd = max(max_dd, dd)

        # Profit factor
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
            "avg_winner": round(sum(wins) / len(wins), 4) if wins else 0,
            "avg_loser": round(sum(losses) / len(losses), 4) if losses else 0,
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

        # Get daily cumulative PnL
        daily_rows = execute(
            "SELECT COALESCE(SUM(pnl_usd), 0) as total FROM trades WHERE status = 'closed' AND closed_at::date = %s",
            (now.date(),)
        )
        cumulative = float(daily_rows[0]["total"]) if daily_rows else 0

        # Open positions count
        open_count = execute_one("SELECT COUNT(*) as cnt FROM trades WHERE status = 'open'", ())

        # Determine session
        hour = now.hour
        sessions = []
        if 7 <= hour < 16:
            sessions.append("london")
        if 12 <= hour < 21:
            sessions.append("new_york")
        session = "overlap" if len(sessions) == 2 else (sessions[0] if sessions else "off_hours")

        row = execute_insert(
            """INSERT INTO hourly_logs (timestamp, utc_hour, session, open_positions,
                trades_opened, trades_closed, trades_skipped, pnl_this_hour,
                cumulative_pnl_today, symbols_analyzed, market_context, decision_summary)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id""",
            (now, hour, session, open_count["cnt"] if open_count else 0,
             trades_opened, trades_closed, trades_skipped, pnl_this_hour,
             cumulative, symbols_analyzed, market_context, decision_summary)
        )

        return json.dumps({
            "logged": True,
            "log_id": str(row["id"]),
            "timestamp": now.isoformat(),
            "session": session,
        })

    @mcp.tool()
    def get_daily_target_progress() -> str:
        """
        Get hour-by-hour progress toward the daily target.

        Returns:
            Target USD, progress by hour, current percentage.
        """
        today = datetime.now(timezone.utc).date()

        # Get target pct from settings
        setting = execute_one("SELECT value FROM trading_settings WHERE key = 'daily_target_pct'", ())
        target_pct = float(setting["value"]) if setting else 1.0

        # Get hourly logs for today
        logs = execute(
            """SELECT utc_hour, cumulative_pnl_today, trades_opened + trades_closed as trades
            FROM hourly_logs WHERE timestamp::date = %s ORDER BY utc_hour""",
            (today,)
        )

        # Get current PnL
        daily_rows = execute(
            "SELECT COALESCE(SUM(pnl_usd), 0) as total FROM trades WHERE status = 'closed' AND closed_at::date = %s",
            (today,)
        )
        current_pnl = float(daily_rows[0]["total"]) if daily_rows else 0

        # We don't have balance from MT5 yet, use a placeholder
        # In production this comes from get_account_info()
        balance_setting = execute_one("SELECT value FROM trading_settings WHERE key = 'min_balance_usd'", ())
        estimated_balance = float(balance_setting["value"]) if balance_setting else 10000
        target_usd = estimated_balance * target_pct / 100

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
