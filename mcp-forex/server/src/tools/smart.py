"""Smart tools — business logic for position sizing, validation, and SL/TP."""

import os
import json
from datetime import datetime, timezone

from src.core.db import execute, execute_one
from src.clients.tradingview import get_analysis

USER_ID = os.getenv("USER_ID", "")


def _get_settings() -> dict:
    """Get trading settings for the current user."""
    row = execute_one("SELECT * FROM trading_settings WHERE user_id = %s", (USER_ID,))
    return row or {}


def register_smart_tools(mcp):
    """Register all smart/business-logic tools."""

    @mcp.tool()
    def calculate_lot_size(symbol: str, sl_pips: float, risk_pct: float = None) -> str:
        """
        Calculate the correct lot size based on risk management.
        Formula: lot = (balance × risk%) / (sl_pips × pip_value_per_lot)

        Args:
            symbol: Forex pair (EURUSD, GBPUSD, etc)
            sl_pips: Stop loss distance in pips
            risk_pct: Risk percentage of balance (default from settings)

        Returns:
            Calculated lot size, risk in USD, and validation.
        """
        if risk_pct is None:
            s = _get_settings()
            risk_pct = float(s.get("max_risk_per_trade_pct", 1.0))

        s = _get_settings()
        max_lot = float(s.get("max_lot_size", 0.50))

        # Get current price to calculate pip value dynamically
        from src.clients.tradingview import get_analysis
        analysis = get_analysis(symbol, "1h")
        if "error" in analysis:
            return json.dumps({"error": f"Cannot get price for {symbol}: {analysis['error']}"})

        close = analysis["price"]["close"]
        if not close:
            return json.dumps({"error": "Price data unavailable"})

        # Calculate pip value per standard lot (100,000 units)
        # For pairs where USD is quote (EURUSD, GBPUSD, AUDUSD, NZDUSD):
        #   pip_value = 0.0001 × 100,000 = $10
        # For pairs where USD is base (USDCAD, USDCHF, USDJPY):
        #   pip_value = pip_size × 100,000 / current_price
        # For crosses (EURGBP):
        #   pip_value = 0.0001 × 100,000 / GBPUSD_rate (approx)

        if "JPY" in symbol:
            pip_size = 0.01
        else:
            pip_size = 0.0001

        quote_currency = symbol[3:]  # Last 3 chars

        if quote_currency == "USD":
            # EURUSD, GBPUSD, AUDUSD — pip value is always $10
            pip_value = pip_size * 100000
        elif symbol[:3] == "USD":
            # USDJPY, USDCAD, USDCHF — pip value varies with price
            pip_value = pip_size * 100000 / close
        else:
            # Crosses (EURGBP, etc) — approximate using $10 adjusted
            pip_value = pip_size * 100000 / close if close > 2 else pip_size * 100000

        # Use min_balance as estimate (in production, comes from MT5)
        from src.clients.mt5_bridge import bridge
        account = bridge.get_account()
        balance = account.get("balance", 10000) if "error" not in account else float(s.get("min_balance_usd", 10000))

        # Calculate
        risk_usd = balance * risk_pct / 100
        if sl_pips <= 0:
            return json.dumps({"error": "sl_pips must be > 0"})

        calculated_lot = risk_usd / (sl_pips * pip_value)

        # Round down to 0.01 step
        adjusted_lot = round(int(calculated_lot * 100) / 100, 2)

        # Cap at max
        if adjusted_lot > max_lot:
            adjusted_lot = max_lot

        # Minimum 0.01
        if adjusted_lot < 0.01:
            adjusted_lot = 0.01

        margin_required = adjusted_lot * 100000 * 0.002  # ~1:500 leverage estimate

        return json.dumps({
            "symbol": symbol,
            "current_price": close,
            "balance": balance,
            "risk_pct": risk_pct,
            "risk_usd": round(risk_usd, 2),
            "sl_pips": sl_pips,
            "pip_value_per_lot": round(pip_value, 2),
            "calculated_lot": round(calculated_lot, 4),
            "adjusted_lot": adjusted_lot,
            "max_allowed_lot": max_lot,
            "margin_required_estimate": round(margin_required, 2),
        })

    @mcp.tool()
    def get_daily_target_status() -> str:
        """
        Check if daily target has been reached. Should the agent keep trading?

        Returns:
            Target USD, current PnL, progress percentage, and recommendation.
        """
        today = datetime.now(timezone.utc).date()
        s = _get_settings()
        target_pct = float(s.get("daily_target_pct", 1.0))
        max_daily_loss_pct = float(s.get("max_daily_loss_pct", 1.0))
        reduce_at = float(s.get("reduce_lot_at_pct", 80.0))

        # Get live balance
        from src.clients.mt5_bridge import bridge
        account = bridge.get_account()
        balance = account.get("balance", 10000) if "error" not in account else 10000

        target_usd = balance * target_pct / 100
        max_loss_usd = balance * max_daily_loss_pct / 100

        # Realized PnL today
        daily_rows = execute(
            "SELECT COALESCE(SUM(pnl_usd), 0) as total, COUNT(*) as cnt FROM trades WHERE user_id = %s AND status = 'closed' AND closed_at::date = %s",
            (USER_ID, today)
        )
        realized_pnl = float(daily_rows[0]["total"]) if daily_rows else 0
        trades_today = int(daily_rows[0]["cnt"]) if daily_rows else 0

        wins = execute_one(
            "SELECT COUNT(*) as cnt FROM trades WHERE user_id = %s AND status = 'closed' AND closed_at::date = %s AND pnl_usd > 0",
            (USER_ID, today)
        )
        losses = execute_one(
            "SELECT COUNT(*) as cnt FROM trades WHERE user_id = %s AND status = 'closed' AND closed_at::date = %s AND pnl_usd <= 0",
            (USER_ID, today)
        )

        progress_pct = round(realized_pnl / target_usd * 100, 1) if target_usd > 0 else 0

        # Determine recommendation
        if realized_pnl >= target_usd:
            recommendation = "STOP — Daily target reached. No more trades today."
        elif realized_pnl <= -max_loss_usd:
            recommendation = "STOP — Daily loss limit hit. No more trades today."
        elif progress_pct >= reduce_at:
            recommendation = "CAREFUL — Close to target. Reduce lot size by 50%."
        else:
            recommendation = "CONTINUE — Target not reached."

        return json.dumps({
            "date": str(today),
            "balance": balance,
            "target_pct": target_pct,
            "target_usd": round(target_usd, 2),
            "max_loss_usd": round(max_loss_usd, 2),
            "realized_pnl": round(realized_pnl, 4),
            "progress_pct": progress_pct,
            "target_reached": realized_pnl >= target_usd,
            "loss_limit_hit": realized_pnl <= -max_loss_usd,
            "trades_today": trades_today,
            "wins_today": wins["cnt"] if wins else 0,
            "losses_today": losses["cnt"] if losses else 0,
            "recommendation": recommendation,
        })

    @mcp.tool()
    def should_trade_now() -> str:
        """
        Comprehensive validation: is it safe and appropriate to trade right now?
        Checks session, daily loss, positions, kill switch, consecutive losses.

        Returns:
            can_trade boolean, individual check results, and any warnings.
        """
        now = datetime.now(timezone.utc)
        hour = now.hour
        today = now.date()
        s = _get_settings()

        checks = {}
        warnings = []
        blocked_reasons = []

        # 1. Kill switch
        kill_switch = s.get("kill_switch", False)
        checks["kill_switch_off"] = {
            "pass": not kill_switch,
            "detail": "Kill switch: OFF" if not kill_switch else "Kill switch: ON — all trading blocked",
        }
        if kill_switch:
            blocked_reasons.append("Kill switch is ON")

        # 2. Trading hours
        start_hour = int(str(s.get("trading_start_utc", "07:00")).split(":")[0])
        end_hour = int(str(s.get("trading_end_utc", "21:00")).split(":")[0])
        in_hours = start_hour <= hour < end_hour
        checks["session_active"] = {
            "pass": in_hours,
            "detail": f"Trading hours: {start_hour:02d}:00-{end_hour:02d}:00 UTC. Current: {hour:02d}:00",
        }
        if not in_hours:
            blocked_reasons.append(f"Outside trading hours ({start_hour:02d}:00-{end_hour:02d}:00 UTC)")

        # 3. Sessions
        sessions = []
        if 7 <= hour < 16:
            sessions.append("london")
        if 12 <= hour < 21:
            sessions.append("new_york")
        if 0 <= hour < 9:
            sessions.append("tokyo")

        if in_hours and hour >= end_hour - 1:
            warnings.append("Trading window ends in <1 hour. Consider smaller positions.")

        # 4. Daily loss check
        from src.clients.mt5_bridge import bridge
        account = bridge.get_account()
        balance = account.get("balance", 10000) if "error" not in account else 10000
        max_loss_pct = float(s.get("max_daily_loss_pct", 1.0))
        max_loss_usd = balance * max_loss_pct / 100

        daily_rows = execute(
            "SELECT COALESCE(SUM(pnl_usd), 0) as total FROM trades WHERE user_id = %s AND status = 'closed' AND closed_at::date = %s",
            (USER_ID, today)
        )
        daily_pnl = float(daily_rows[0]["total"]) if daily_rows else 0
        loss_ok = daily_pnl > -max_loss_usd
        checks["daily_loss_ok"] = {
            "pass": loss_ok,
            "detail": f"Daily PnL: ${daily_pnl:.2f} (limit: -${max_loss_usd:.2f})",
        }
        if not loss_ok:
            blocked_reasons.append(f"Daily loss limit hit (${daily_pnl:.2f})")

        # 5. Max positions
        max_positions = int(s.get("max_open_positions", 3))
        open_count = execute_one(
            "SELECT COUNT(*) as cnt FROM trades WHERE user_id = %s AND status = 'open'", (USER_ID,)
        )
        current_open = open_count["cnt"] if open_count else 0
        pos_ok = current_open < max_positions
        checks["max_positions_ok"] = {
            "pass": pos_ok,
            "detail": f"Open: {current_open}/{max_positions} positions",
        }
        if not pos_ok:
            blocked_reasons.append(f"Max positions reached ({current_open}/{max_positions})")

        # 6. Consecutive losses
        max_con_losses = int(s.get("max_consecutive_losses", 5))
        recent = execute(
            "SELECT pnl_usd FROM trades WHERE user_id = %s AND status = 'closed' ORDER BY closed_at DESC LIMIT %s",
            (USER_ID, max_con_losses)
        )
        consecutive_losses = 0
        for r in recent:
            if r["pnl_usd"] is not None and float(r["pnl_usd"]) <= 0:
                consecutive_losses += 1
            else:
                break

        con_ok = consecutive_losses < max_con_losses
        checks["consecutive_losses_ok"] = {
            "pass": con_ok,
            "detail": f"Consecutive losses: {consecutive_losses} (max: {max_con_losses})",
        }
        if not con_ok:
            blocked_reasons.append(f"Too many consecutive losses ({consecutive_losses})")

        can_trade = len(blocked_reasons) == 0

        return json.dumps({
            "can_trade": can_trade,
            "checks": checks,
            "active_sessions": sessions,
            "warnings": warnings,
            "blocked_reasons": blocked_reasons,
        })

    @mcp.tool()
    def get_optimal_sl_tp(symbol: str, side: str, strategy: str = "balanced") -> str:
        """
        Calculate dynamic SL and TP based on ATR-equivalent volatility.
        Uses H1 price range as ATR proxy (TradingView doesn't provide ATR for forex).

        Args:
            symbol: Forex pair
            side: 'BUY' or 'SELL'
            strategy: 'conservative', 'balanced', 'aggressive'

        Returns:
            SL/TP in pips and price, with R:R ratio.
        """
        # Get H1 data for volatility estimate
        h1 = get_analysis(symbol, "1h")
        if "error" in h1:
            return json.dumps(h1)

        # Also get H4 for better ATR estimate
        h4 = get_analysis(symbol, "4h")

        close = h1["price"]["close"]
        high = h1["price"]["high"]
        low = h1["price"]["low"]

        if not close or not high or not low:
            return json.dumps({"error": "Price data unavailable"})

        # ATR proxy: use H1 high-low range (typical bar range)
        h1_range = high - low

        # For 5-digit pairs (EURUSD, GBPUSD), 1 pip = 0.0001
        # For JPY pairs, 1 pip = 0.01
        if "JPY" in symbol:
            pip_size = 0.01
        else:
            pip_size = 0.0001

        atr_pips = h1_range / pip_size

        # Ensure minimum ATR (avoid too-tight stops)
        if atr_pips < 5:
            atr_pips = 15  # Default minimum

        # Strategy multipliers
        strategies = {
            "conservative": {"sl_mult": 2.0, "tp1_mult": 2.0, "tp2_mult": 3.0},
            "balanced": {"sl_mult": 1.5, "tp1_mult": 2.0, "tp2_mult": 3.0},
            "aggressive": {"sl_mult": 1.0, "tp1_mult": 2.5, "tp2_mult": 4.0},
        }
        strat = strategies.get(strategy, strategies["balanced"])

        sl_pips = round(atr_pips * strat["sl_mult"], 1)
        tp1_pips = round(atr_pips * strat["tp1_mult"], 1)
        tp2_pips = round(atr_pips * strat["tp2_mult"], 1)

        # Ensure minimum SL
        s = _get_settings()
        min_rr = float(s.get("min_rr_ratio", 1.5))
        if sl_pips < 10:
            sl_pips = 10.0

        # Calculate prices
        if side.upper() == "BUY":
            sl_price = round(close - sl_pips * pip_size, 5 if "JPY" not in symbol else 3)
            tp1_price = round(close + tp1_pips * pip_size, 5 if "JPY" not in symbol else 3)
            tp2_price = round(close + tp2_pips * pip_size, 5 if "JPY" not in symbol else 3)
        else:
            sl_price = round(close + sl_pips * pip_size, 5 if "JPY" not in symbol else 3)
            tp1_price = round(close - tp1_pips * pip_size, 5 if "JPY" not in symbol else 3)
            tp2_price = round(close - tp2_pips * pip_size, 5 if "JPY" not in symbol else 3)

        rr1 = round(tp1_pips / sl_pips, 2) if sl_pips > 0 else 0
        rr2 = round(tp2_pips / sl_pips, 2) if sl_pips > 0 else 0

        return json.dumps({
            "symbol": symbol,
            "side": side.upper(),
            "strategy": strategy,
            "current_price": close,
            "atr_proxy_pips": round(atr_pips, 1),
            "stop_loss": {
                "price": sl_price,
                "pips": sl_pips,
                "method": f"{strat['sl_mult']}× ATR",
            },
            "take_profit_1": {
                "price": tp1_price,
                "pips": tp1_pips,
                "rr_ratio": rr1,
                "method": f"{strat['tp1_mult']}× ATR",
            },
            "take_profit_2": {
                "price": tp2_price,
                "pips": tp2_pips,
                "rr_ratio": rr2,
                "method": f"{strat['tp2_mult']}× ATR",
            },
            "recommended_tp": "take_profit_1" if rr1 >= min_rr else "take_profit_2",
            "min_rr_required": min_rr,
            "valid": rr1 >= min_rr,
        })
