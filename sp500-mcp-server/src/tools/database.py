"""
SP500 Database Tools — Trade logging and performance tracking
Uses same PostgreSQL but with sp500_ prefixed tables
"""
import json
import os
import psycopg2
import psycopg2.extras
import pytz
from datetime import datetime, timedelta, timezone, time as dtime

DATABASE_URL = os.getenv("DATABASE_URL", "")
USER_ID = os.getenv("USER_ID", "5f7b54c4-3bb5-487e-897e-e273112a914b")
NY_TZ = pytz.timezone("America/New_York")


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

    @mcp.tool()
    async def sp500_check_trading_allowed() -> str:
        """
        Gate real para nuevas entradas SP500 — llamar antes de evaluar cualquier
        setup nuevo. Aplica kill_switch, auto_trading_enabled, max_daily_loss_pct,
        max_consecutive_losses, y el tope de 1 trade por dia (calendario ET).

        min_structure_score / min_sweep_distance_points se devuelven como
        umbrales (no se evaluan aqui — no hay un setup concreto que comparar
        en este tool) para que el trigger de entrada los aplique contra el
        spring/upthrust detectado.

        Si can_trade=false, no abrir posiciones nuevas — leer blocked_reasons.
        """
        from src.clients.database import get_settings
        from src.clients import mt5_bridge

        settings = get_settings(force_refresh=True)
        now_utc = datetime.now(timezone.utc)
        today_et = now_utc.astimezone(NY_TZ).date()
        day_start_et = NY_TZ.localize(datetime.combine(today_et, dtime.min))
        day_start_utc = day_start_et.astimezone(timezone.utc)
        day_end_utc = day_start_utc + timedelta(days=1)

        checks = {}
        blocked_reasons = []

        kill_switch = bool(settings.get("kill_switch"))
        checks["kill_switch_off"] = {
            "pass": not kill_switch,
            "detail": "Kill switch OFF" if not kill_switch else "Kill switch ON — todo bloqueado",
        }
        if kill_switch:
            blocked_reasons.append("Kill switch activo")

        auto_enabled = bool(settings.get("auto_trading_enabled", True))
        checks["auto_trading_enabled"] = {
            "pass": auto_enabled,
            "detail": "Auto trading ON" if auto_enabled else "auto_trading_enabled = false",
        }
        if not auto_enabled:
            blocked_reasons.append("auto_trading_enabled = false")

        # 1 trade/dia (calendario ET) — cuenta cualquier trade abierto hoy,
        # abierto o cerrado, no solo los cerrados.
        trades_today = _execute_one(
            "SELECT COUNT(*) as cnt FROM sp500_trades WHERE user_id = %s AND opened_at >= %s AND opened_at < %s",
            (USER_ID, day_start_utc, day_end_utc)
        )
        count_today = trades_today["cnt"] if trades_today else 0
        daily_cap_ok = count_today < 1
        checks["daily_trade_cap_ok"] = {
            "pass": daily_cap_ok,
            "detail": f"Trades hoy (ET): {count_today}/1",
        }
        if not daily_cap_ok:
            blocked_reasons.append("Tope diario alcanzado — ya se abrio 1 trade hoy")

        # Daily loss limit
        account = await mt5_bridge.get_account_info()
        balance = float(account.get("balance", 0)) if "error" not in account else 0
        max_loss_pct = float(settings.get("max_daily_loss_pct", 5.0))
        max_loss_usd = balance * max_loss_pct / 100
        daily_pnl_row = _execute_one(
            """SELECT COALESCE(SUM(pnl_usd), 0) as total FROM sp500_trades
            WHERE user_id = %s AND status = 'closed' AND closed_at >= %s AND closed_at < %s""",
            (USER_ID, day_start_utc, day_end_utc)
        )
        daily_pnl = float(daily_pnl_row["total"]) if daily_pnl_row else 0
        loss_ok = balance <= 0 or daily_pnl > -max_loss_usd
        checks["daily_loss_ok"] = {
            "pass": loss_ok,
            "detail": f"PnL hoy: ${daily_pnl:.2f} (limite: -${max_loss_usd:.2f})",
        }
        if not loss_ok:
            blocked_reasons.append(f"Limite de perdida diaria alcanzado (${daily_pnl:.2f})")

        # Consecutive losses
        max_con_losses = int(settings.get("max_consecutive_losses", 5))
        recent = _execute(
            "SELECT pnl_usd FROM sp500_trades WHERE user_id = %s AND status = 'closed' ORDER BY closed_at DESC LIMIT %s",
            (USER_ID, max(max_con_losses * 2, 10))
        )
        consecutive_losses = 0
        for r in recent:
            if r["pnl_usd"] is not None and float(r["pnl_usd"]) < 0:
                consecutive_losses += 1
            else:
                break
        con_ok = consecutive_losses < max_con_losses
        checks["consecutive_losses_ok"] = {
            "pass": con_ok,
            "detail": f"Perdidas consecutivas: {consecutive_losses} (max: {max_con_losses})",
        }
        if not con_ok:
            blocked_reasons.append(f"Racha de {consecutive_losses} perdidas consecutivas alcanzo el maximo")

        can_trade = len(blocked_reasons) == 0

        return json.dumps({
            "can_trade": can_trade,
            "timestamp": now_utc.isoformat(),
            "trading_day_et": today_et.isoformat(),
            "checks": checks,
            "thresholds": {
                "min_structure_score": settings.get("min_structure_score"),
                "min_sweep_distance_points": settings.get("min_sweep_distance_points"),
            },
            "blocked_reasons": blocked_reasons,
        })

    @mcp.tool()
    async def sp500_get_settings() -> str:
        """
        Returns all SP500 trading configuration from the database.
        Includes risk parameters, killzone times, targets, and system flags.
        Call this at the start of each session to know your operating parameters.
        """
        from src.clients.database import get_settings
        settings = get_settings(force_refresh=True)

        return json.dumps({
            "symbol": settings["symbol"],
            "point_value_per_lot": settings["point_value"],
            "lot_range": {
                "min": settings["min_lot"],
                "max": settings["max_lot"]
            },
            "risk": {
                "max_risk_per_trade_pct": settings["max_risk_per_trade_pct"],
                "max_daily_loss_pct": settings["max_daily_loss_pct"],
                "max_consecutive_losses": settings["max_consecutive_losses"],
                "min_rr_ratio": settings["min_rr_ratio"],
                "max_open_positions": settings["max_open_positions"]
            },
            "killzones": {
                "am_start": settings["am_killzone_start"],
                "am_end": settings["am_killzone_end"],
                "pm_start": settings["pm_killzone_start"],
                "pm_end": settings["pm_killzone_end"],
                "premarket_start": settings["premarket_start"],
                "regular_session": f"{settings['regular_session_start']}-{settings['regular_session_end']}"
            },
            "news_buffer_minutes": settings["news_buffer_minutes"],
            "targets": {
                "daily_target_pct": settings["daily_target_pct"],
                "daily_target_points": settings["daily_target_points"]
            },
            "filters": {
                "min_structure_score": settings["min_structure_score"],
                "min_sweep_distance_points": settings["min_sweep_distance_points"]
            },
            "system": {
                "kill_switch": settings["kill_switch"],
                "auto_trading_enabled": settings["auto_trading_enabled"]
            }
        })
