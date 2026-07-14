"""System tools — health check, safety rules, economic calendar."""

import json
from datetime import datetime, timezone

from src.core.db import execute, execute_one


def register_system_tools(mcp):
    """Register all system tools."""

    @mcp.tool()
    def get_safety_rules() -> str:
        """
        Get all active safety rules and current system state.

        Returns:
            All rules from trading_settings + current state (positions, PnL, streaks).
        """
        rows = execute("SELECT key, value, category FROM trading_settings ORDER BY category, key")

        rules = {}
        for r in rows:
            cat = r["category"]
            if cat not in rules:
                rules[cat] = {}
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
            rules[cat][r["key"]] = val

        # Current state
        today = datetime.now(timezone.utc).date()

        open_count = execute_one("SELECT COUNT(*) as cnt FROM trades WHERE status = 'open'", ())
        daily_rows = execute(
            "SELECT COALESCE(SUM(pnl_usd), 0) as total FROM trades WHERE status = 'closed' AND closed_at::date = %s",
            (today,)
        )

        # Consecutive losses
        recent = execute(
            "SELECT pnl_usd FROM trades WHERE status = 'closed' ORDER BY closed_at DESC LIMIT 10"
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
            "can_trade": consecutive_losses < rules.get("risk", {}).get("max_consecutive_losses", 5)
                         and (float(daily_rows[0]["total"]) if daily_rows else 0) > -rules.get("risk", {}).get("max_daily_loss_pct", 1.0) * rules.get("system", {}).get("min_balance_usd", 500) / 100,
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
            result = execute_one("SELECT 1 as ping", ())
            tables = execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
            )
            trade_count = execute_one("SELECT COUNT(*) as cnt FROM trades", ())
            components["database"] = {
                "status": "ok",
                "tables": [t["tablename"] for t in tables],
                "total_trades": trade_count["cnt"] if trade_count else 0,
            }
        except Exception as e:
            components["database"] = {"status": "error", "error": str(e)}
            warnings.append("Database connection failed")

        # TradingView
        try:
            from src.clients.tradingview import get_analysis
            result = get_analysis("EURUSD", "1d")
            if "error" in result:
                components["tradingview"] = {"status": "degraded", "error": result["error"]}
                warnings.append("TradingView rate limited or unavailable")
            else:
                components["tradingview"] = {
                    "status": "ok",
                    "last_price": result["price"]["close"],
                }
        except Exception as e:
            components["tradingview"] = {"status": "error", "error": str(e)}
            warnings.append("TradingView unavailable")

        # MT5 Bridge (placeholder until bridge is deployed)
        components["mt5_bridge"] = {
            "status": "not_configured",
            "note": "MT5 bridge not yet deployed. Trading tools in mock mode.",
        }

        # Overall status
        statuses = [c.get("status") for c in components.values()]
        if all(s == "ok" for s in statuses):
            overall = "healthy"
        elif "error" in statuses:
            overall = "unhealthy"
        else:
            overall = "degraded"

        return json.dumps({
            "status": overall,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": components,
            "warnings": warnings,
        })

    @mcp.tool()
    def get_economic_calendar(hours_ahead: int = 4, impact: str = "high") -> str:
        """
        Get upcoming high-impact economic events that could affect trading.

        Args:
            hours_ahead: How many hours ahead to check (default 4)
            impact: Minimum impact level — 'high', 'medium', 'all'

        Returns:
            Upcoming events, blocked pairs, and whether it's safe to trade.
        """
        # NOTE: In production this would scrape Forex Factory or use an API.
        # For now, we return a static "no events" response since we don't have
        # a calendar source configured yet.
        #
        # Future implementation:
        # 1. Scrape https://www.forexfactory.com/calendar
        # 2. Cache results in economic_events table
        # 3. Return events within hours_ahead window

        now = datetime.now(timezone.utc)

        # Check if we have cached events in DB
        try:
            events = execute(
                """SELECT event_time, currency, event_name, impact, forecast, previous
                FROM economic_events
                WHERE event_time >= %s AND event_time <= %s
                AND (%s = 'all' OR impact = %s)
                ORDER BY event_time""",
                (now, now.replace(hour=now.hour + hours_ahead), impact, impact)
            )
        except Exception:
            events = []

        if events:
            event_list = []
            blocked_pairs = set()
            currency_pair_map = {
                "USD": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"],
                "EUR": ["EURUSD", "EURGBP"],
                "GBP": ["GBPUSD", "EURGBP"],
                "JPY": ["USDJPY"],
                "AUD": ["AUDUSD"],
                "CAD": ["USDCAD"],
            }

            news_buffer = int(execute_one(
                "SELECT value FROM trading_settings WHERE key = 'news_buffer_minutes'", ()
            )["value"] or 30)

            for e in events:
                hours_until = (e["event_time"] - now).total_seconds() / 3600
                affected = currency_pair_map.get(e["currency"], [])

                if hours_until * 60 <= news_buffer:
                    blocked_pairs.update(affected)

                event_list.append({
                    "time": e["event_time"].isoformat(),
                    "currency": e["currency"],
                    "event": e["event_name"],
                    "impact": e["impact"],
                    "forecast": e["forecast"],
                    "previous": e["previous"],
                    "hours_until": round(hours_until, 1),
                    "affects_pairs": affected,
                })

            return json.dumps({
                "timestamp": now.isoformat(),
                "events_ahead": event_list,
                "blocked_pairs": sorted(blocked_pairs),
                "safe_to_trade": len(blocked_pairs) == 0,
                "note": f"Found {len(event_list)} events in next {hours_ahead}h",
            })
        else:
            return json.dumps({
                "timestamp": now.isoformat(),
                "events_ahead": [],
                "blocked_pairs": [],
                "safe_to_trade": True,
                "note": "No economic calendar data available. Consider this a non-blocking check.",
                "todo": "Configure calendar scraper for production use.",
            })
