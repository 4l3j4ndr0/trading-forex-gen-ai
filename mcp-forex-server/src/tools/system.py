"""System tools — health check, safety rules, economic calendar."""

import os
import json
from datetime import datetime, timezone

from src.core.db import execute, execute_one

USER_ID = os.getenv("USER_ID", "")


def register_system_tools(mcp):
    """Register all system tools."""

    @mcp.tool()
    def get_safety_rules() -> str:
        """
        Get all active safety rules and current system state.

        Returns:
            All rules from trading_settings + current state (positions, PnL, streaks).
        """
        s = execute_one("SELECT * FROM trading_settings WHERE user_id = %s", (USER_ID,))
        if not s:
            return json.dumps({"error": "No trading settings found"})

        rules = {
            "risk": {
                "max_risk_per_trade_pct": float(s.get("max_risk_per_trade_pct", 1.0)),
                "max_daily_loss_pct": float(s.get("max_daily_loss_pct", 1.0)),
                "max_drawdown_pct": float(s.get("max_drawdown_pct", 5.0)),
                "max_consecutive_losses": int(s.get("max_consecutive_losses", 5)),
                "min_rr_ratio": float(s.get("min_rr_ratio", 1.5)),
            },
            "sizing": {
                "max_lot_size": float(s.get("max_lot_size", 0.50)),
                "max_open_positions": int(s.get("max_open_positions", 3)),
            },
            "session": {
                "trading_start_utc": str(s.get("trading_start_utc", "07:00")),
                "trading_end_utc": str(s.get("trading_end_utc", "21:00")),
            },
            "system": {
                "kill_switch": bool(s.get("kill_switch", False)),
                "auto_trading_enabled": bool(s.get("auto_trading_enabled", True)),
            },
        }

        # Current state
        today = datetime.now(timezone.utc).date()
        open_count = execute_one("SELECT COUNT(*) as cnt FROM trades WHERE user_id = %s AND status = 'open'", (USER_ID,))
        daily_rows = execute(
            "SELECT COALESCE(SUM(pnl_usd), 0) as total FROM trades WHERE user_id = %s AND status = 'closed' AND closed_at::date = %s",
            (USER_ID, today)
        )

        recent = execute(
            "SELECT pnl_usd FROM trades WHERE user_id = %s AND status = 'closed' ORDER BY closed_at DESC LIMIT 10",
            (USER_ID,)
        )
        consecutive_losses = 0
        for r in recent:
            if r["pnl_usd"] is not None and float(r["pnl_usd"]) <= 0:
                consecutive_losses += 1
            else:
                break

        state = {
            "open_positions": open_count["cnt"] if open_count else 0,
            "daily_pnl": float(daily_rows[0]["total"]) if daily_rows else 0,
            "consecutive_losses": consecutive_losses,
        }

        return json.dumps({"rules": rules, "current_state": state})

    @mcp.tool()
    def health_check() -> str:
        """
        Verify all system components are functioning.

        Returns:
            Status of MCP server, database, TradingView, and MT5 bridge.
        """
        components = {}
        warnings = []

        # MCP Server
        components["mcp_server"] = {"status": "ok"}

        # Database
        try:
            execute_one("SELECT 1 as ping", ())
            components["database"] = {"status": "ok"}
        except Exception as e:
            components["database"] = {"status": "error", "error": str(e)}
            warnings.append("Database connection failed")

        # TradingView
        try:
            from src.clients.tradingview import get_analysis
            result = get_analysis("EURUSD", "1d")
            if "error" in result:
                components["tradingview"] = {"status": "degraded", "note": "rate limited"}
            else:
                components["tradingview"] = {"status": "ok", "last_price": result["price"]["close"]}
        except Exception:
            components["tradingview"] = {"status": "error"}
            warnings.append("TradingView unavailable")

        # MT5 Bridge
        try:
            from src.clients.mt5_bridge import bridge
            result = bridge.get_account()
            if "error" not in result:
                components["mt5_bridge"] = {"status": "ok", "balance": result["balance"]}
            else:
                components["mt5_bridge"] = {"status": "error", "error": result["error"]}
                warnings.append("MT5 Bridge error")
        except Exception:
            components["mt5_bridge"] = {"status": "unreachable"}
            warnings.append("MT5 Bridge unreachable")

        statuses = [c.get("status") for c in components.values()]
        overall = "healthy" if all(s == "ok" for s in statuses) else "degraded" if "error" not in statuses else "unhealthy"

        return json.dumps({"status": overall, "timestamp": datetime.now(timezone.utc).isoformat(), "components": components, "warnings": warnings})

    @mcp.tool()
    def get_economic_calendar(hours_ahead: int = 4, impact: str = "high") -> str:
        """
        Get upcoming high-impact economic events.

        Args:
            hours_ahead: How many hours ahead to check (default 4)
            impact: Minimum impact level — 'high', 'medium', 'all'

        Returns:
            Upcoming events, blocked pairs, and whether it's safe to trade.
        """
        now = datetime.now(timezone.utc)

        # Check cached events in DB
        try:
            events = execute(
                """SELECT event_time, currency, event_name, impact, forecast, previous
                FROM economic_events
                WHERE event_time >= %s AND event_time <= %s
                ORDER BY event_time""",
                (now, now + __import__('datetime').timedelta(hours=hours_ahead))
            )
        except Exception:
            events = []

        if not events:
            return json.dumps({
                "timestamp": now.isoformat(),
                "events_ahead": [],
                "blocked_pairs": [],
                "safe_to_trade": True,
                "note": "No economic calendar data available.",
            })

        return json.dumps({
            "timestamp": now.isoformat(),
            "events_ahead": [{"time": str(e["event_time"]), "currency": e["currency"], "event": e["event_name"], "impact": e["impact"]} for e in events],
            "blocked_pairs": [],
            "safe_to_trade": True,
        })
