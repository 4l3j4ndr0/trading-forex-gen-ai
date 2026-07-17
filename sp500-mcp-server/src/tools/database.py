"""
SP500 Database Tools — Trade logging and performance tracking
Uses same PostgreSQL but with sp500_ prefixed tables
"""
import json
import os
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone

DATABASE_URL = os.getenv("DATABASE_URL", "")
USER_ID = os.getenv("USER_ID", "5f7b54c4-3bb5-487e-897e-e273112a914b")


def _get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def _execute(query: str, params: tuple = ()) -> list:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if cur.description:
                return cur.fetchall()
            conn.commit()
            return []


def _execute_one(query: str, params: tuple = ()):
    rows = _execute(query, params)
    return rows[0] if rows else None


def register_database_tools(mcp):

    @mcp.tool()
    async def sp500_register_trade(
        ticket: int,
        side: str,
        lot_size: float,
        entry_price: float,
        sl_price: float,
        tp_price: float,
        sl_points: float,
        tp_points: float,
        risk_usd: float,
        comment: str = "",
        basket_id: str = ""
    ) -> str:
        """
        Register a new SP500 trade in the database.
        
        Args:
            ticket: MT5 ticket number
            side: BUY or SELL
            lot_size: Position size
            entry_price: Entry price
            sl_price: Stop loss price
            tp_price: Take profit price
            sl_points: SL distance in points
            tp_points: TP distance in points
            risk_usd: USD amount at risk
            comment: Trade justification
            basket_id: Basket identifier (SP500-YYYYMMDD-NNN)
        """
        now = datetime.now(timezone.utc)

        _execute("""
            INSERT INTO sp500_trades (
                user_id, ticket, side, lot_size, entry_price,
                sl_price, tp_price, sl_points, tp_points,
                risk_usd, comment, basket_id, status, opened_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'open', %s)
            ON CONFLICT (ticket) DO UPDATE SET
                basket_id = EXCLUDED.basket_id,
                comment = EXCLUDED.comment
        """, (
            USER_ID, ticket, side.upper(), lot_size, entry_price,
            sl_price, tp_price, sl_points, tp_points,
            risk_usd, comment, basket_id, now
        ))

        return json.dumps({"status": "registered", "ticket": ticket, "basket_id": basket_id})

    @mcp.tool()
    async def sp500_update_trade(
        ticket: int,
        exit_price: float,
        pnl_points: float,
        pnl_usd: float,
        close_reason: str
    ) -> str:
        """
        Update a closed SP500 trade with exit details.
        
        Args:
            ticket: MT5 ticket number
            exit_price: Exit price
            pnl_points: Profit/loss in points
            pnl_usd: Profit/loss in USD
            close_reason: Why closed (sl_hit, tp_hit, manual, hedge_unlock, structure_invalidated)
        """
        now = datetime.now(timezone.utc)

        _execute("""
            UPDATE sp500_trades
            SET exit_price = %s, pnl_points = %s, pnl_usd = %s,
                close_reason = %s, status = 'closed', closed_at = %s
            WHERE ticket = %s AND user_id = %s
        """, (exit_price, pnl_points, pnl_usd, close_reason, now, ticket, USER_ID))

        return json.dumps({"status": "updated", "ticket": ticket, "pnl_usd": pnl_usd})

    @mcp.tool()
    async def sp500_get_performance(period: str = "today") -> str:
        """
        Get SP500 trading performance stats.
        
        Args:
            period: 'today', 'week', 'month', 'all'
        """
        if period == "today":
            date_filter = "AND DATE(closed_at) = CURRENT_DATE"
        elif period == "week":
            date_filter = "AND closed_at >= CURRENT_DATE - INTERVAL '7 days'"
        elif period == "month":
            date_filter = "AND closed_at >= CURRENT_DATE - INTERVAL '30 days'"
        else:
            date_filter = ""

        stats = _execute_one(f"""
            SELECT
                COUNT(*) as total_trades,
                COUNT(CASE WHEN pnl_usd > 0 THEN 1 END) as wins,
                COUNT(CASE WHEN pnl_usd < 0 THEN 1 END) as losses,
                COALESCE(SUM(pnl_usd), 0) as total_pnl,
                COALESCE(AVG(pnl_usd), 0) as avg_pnl,
                COALESCE(MAX(pnl_usd), 0) as best_trade,
                COALESCE(MIN(pnl_usd), 0) as worst_trade,
                COALESCE(AVG(CASE WHEN pnl_usd > 0 THEN pnl_usd END), 0) as avg_win,
                COALESCE(AVG(CASE WHEN pnl_usd < 0 THEN ABS(pnl_usd) END), 0) as avg_loss
            FROM sp500_trades
            WHERE user_id = %s AND status = 'closed' {date_filter}
        """, (USER_ID,))

        if not stats or stats["total_trades"] == 0:
            return json.dumps({"period": period, "total_trades": 0, "message": "No closed trades"})

        total = int(stats["total_trades"])
        wins = int(stats["wins"])
        losses = int(stats["losses"])
        win_rate = (wins / total * 100) if total > 0 else 0
        avg_win = float(stats["avg_win"])
        avg_loss = float(stats["avg_loss"])
        profit_factor = (avg_win * wins) / (avg_loss * losses) if losses > 0 and avg_loss > 0 else 999

        return json.dumps({
            "period": period,
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 1),
            "total_pnl": round(float(stats["total_pnl"]), 2),
            "avg_pnl": round(float(stats["avg_pnl"]), 2),
            "best_trade": round(float(stats["best_trade"]), 2),
            "worst_trade": round(float(stats["worst_trade"]), 2),
            "profit_factor": round(profit_factor, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2)
        })

    @mcp.tool()
    async def sp500_log_decision(
        decision: str,
        trades_opened: int = 0,
        trades_closed: int = 0,
        floating_pnl: float = 0
    ) -> str:
        """
        Log the agent's decision for this cycle.
        
        Args:
            decision: Text summary of what was decided and why
            trades_opened: Number of trades opened this cycle
            trades_closed: Number of trades closed this cycle
            floating_pnl: Current floating P&L
        """
        now = datetime.now(timezone.utc)

        _execute("""
            INSERT INTO sp500_logs (user_id, decision, trades_opened, trades_closed, floating_pnl, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (USER_ID, decision, trades_opened, trades_closed, floating_pnl, now))

        return json.dumps({"status": "logged", "time": now.strftime("%H:%M UTC")})
