"""Trading tools — execute orders via MT5 Bridge."""

import os
import json
from datetime import datetime, timezone

from src.clients.mt5_bridge import bridge
from src.core.db import execute, execute_one, execute_insert

USER_ID = os.getenv("USER_ID", "")


def _get_settings() -> dict:
    """Get trading settings for the current user."""
    row = execute_one("SELECT * FROM trading_settings WHERE user_id = %s", (USER_ID,))
    return row or {}


def _can_open_position(symbol: str, lot_size: float) -> dict | None:
    """Run safety checks. Returns error dict if blocked, None if OK."""
    s = _get_settings()
    if not s:
        return {"error": "No trading settings found for user"}

    # Kill switch
    if s.get("kill_switch"):
        return {"error": "Kill switch is ON — all trading blocked"}

    # Auto trading
    if not s.get("auto_trading_enabled", True):
        return {"error": "Auto trading is disabled"}

    # Trading hours
    now = datetime.now(timezone.utc)

    # Weekend check
    if now.isoweekday() >= 6:
        return {"error": "Forex market closed on weekends"}

    start_hour = int(str(s.get("trading_start_utc", "07:00")).split(":")[0])
    end_hour = int(str(s.get("trading_end_utc", "21:00")).split(":")[0])
    if not (start_hour <= now.hour < end_hour):
        return {"error": f"Outside trading hours ({start_hour:02d}:00-{end_hour:02d}:00 UTC)"}

    # Allowed pairs
    allowed = s.get("allowed_pairs", [])
    if isinstance(allowed, str):
        allowed = json.loads(allowed)
    if symbol not in allowed:
        return {"error": f"{symbol} not in allowed pairs: {allowed}"}

    # Max positions
    max_pos = int(s.get("max_open_positions", 3))
    open_count = execute_one(
        "SELECT COUNT(*) as cnt FROM trades WHERE user_id = %s AND status = 'open'", (USER_ID,)
    )
    if open_count and open_count["cnt"] >= max_pos:
        return {"error": f"Max positions reached ({open_count['cnt']}/{max_pos})"}

    # Max lot
    max_lot = float(s.get("max_lot_size", 0.50))
    if lot_size > max_lot:
        return {"error": f"Lot {lot_size} exceeds max {max_lot}"}

    # Daily loss
    today = now.date()
    daily_rows = execute(
        "SELECT COALESCE(SUM(pnl_usd), 0) as total FROM trades WHERE user_id = %s AND status = 'closed' AND closed_at::date = %s",
        (USER_ID, today)
    )
    daily_pnl = float(daily_rows[0]["total"]) if daily_rows else 0
    balance_result = bridge.get_account()
    balance = balance_result.get("balance", 10000) if "error" not in balance_result else 10000
    max_loss = balance * float(s.get("max_daily_loss_pct", 1.0)) / 100
    if daily_pnl <= -max_loss:
        return {"error": f"Daily loss limit hit (${daily_pnl:.2f}, limit: -${max_loss:.2f})"}

    # Consecutive losses
    max_con = int(s.get("max_consecutive_losses", 5))
    recent = execute(
        "SELECT pnl_usd FROM trades WHERE user_id = %s AND status = 'closed' ORDER BY closed_at DESC LIMIT %s",
        (USER_ID, max_con)
    )
    consecutive = 0
    for r in recent:
        if r["pnl_usd"] is not None and float(r["pnl_usd"]) <= 0:
            consecutive += 1
        else:
            break
    if consecutive >= max_con:
        return {"error": f"Too many consecutive losses ({consecutive})"}

    return None


def register_trading_tools(mcp):
    """Register all trading execution tools."""

    @mcp.tool()
    def open_position(symbol: str, side: str, lot_size: float, sl_pips: float, tp_pips: float, comment: str = "") -> str:
        """
        Open a forex position via MT5 with safety validation.

        Args:
            symbol: Forex pair — EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, EURGBP
            side: 'BUY' or 'SELL'
            lot_size: Position size in lots (0.01 minimum)
            sl_pips: Stop loss in pips
            tp_pips: Take profit in pips
            comment: Reason for the trade (AI reasoning)

        Returns:
            Order confirmation with ticket, entry price, SL/TP prices.
        """
        # Safety checks
        blocked = _can_open_position(symbol, lot_size)
        if blocked:
            return json.dumps(blocked)

        # R:R check
        s = _get_settings()
        min_rr = float(s.get("min_rr_ratio", 1.5))
        rr = tp_pips / sl_pips if sl_pips > 0 else 0
        if rr < min_rr:
            return json.dumps({"error": f"R:R {rr:.2f} below minimum {min_rr}. Increase TP or reduce SL."})

        # Get current price from bridge
        tick = bridge.get_tick(symbol)
        if "error" in tick:
            return json.dumps(tick)

        # Calculate SL/TP prices
        pip_size = 0.01 if "JPY" in symbol else 0.0001

        if side.upper() == "BUY":
            entry_price = tick["ask"]
            sl_price = round(entry_price - sl_pips * pip_size, 5 if "JPY" not in symbol else 3)
            tp_price = round(entry_price + tp_pips * pip_size, 5 if "JPY" not in symbol else 3)
        else:
            entry_price = tick["bid"]
            sl_price = round(entry_price + sl_pips * pip_size, 5 if "JPY" not in symbol else 3)
            tp_price = round(entry_price - tp_pips * pip_size, 5 if "JPY" not in symbol else 3)

        # Send order to bridge
        result = bridge.open_order(
            symbol=symbol,
            side=side.upper(),
            lot=lot_size,
            sl=sl_price,
            tp=tp_price,
            comment=comment[:63],
        )

        if "error" in result:
            return json.dumps(result)

        # Calculate risk
        sym_info = bridge.get_symbol_info(symbol)
        pip_value = sym_info.get("pip_value", 10.0) if "error" not in sym_info else 10.0
        risk_usd = sl_pips * pip_value * lot_size

        # Get pair_id
        pair = execute_one("SELECT id FROM pairs WHERE symbol = %s", (symbol,))
        pair_id = pair["id"] if pair else 1

        # Register in DB
        row = execute_insert(
            """INSERT INTO trades (user_id, pair_id, ticket, side, lot_size, entry_price, sl_price, tp_price,
                sl_pips, tp_pips, risk_usd, rr_ratio, comment, status, opened_at, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'open', NOW(), NOW())
            RETURNING id""",
            (USER_ID, pair_id, result["ticket"], side.upper(), lot_size, result["entry_price"],
             sl_price, tp_price, sl_pips, tp_pips, round(risk_usd, 2), round(rr, 2), comment)
        )

        return json.dumps({
            "success": True,
            "trade_id": str(row["id"]),
            "ticket": result["ticket"],
            "symbol": symbol,
            "side": side.upper(),
            "lot_size": lot_size,
            "entry_price": result["entry_price"],
            "sl_price": sl_price,
            "tp_price": tp_price,
            "sl_pips": sl_pips,
            "tp_pips": tp_pips,
            "rr_ratio": round(rr, 2),
            "risk_usd": round(risk_usd, 2),
        })

    @mcp.tool()
    def close_position(ticket: int, close_reason: str = "manual") -> str:
        """
        Close a specific position by MT5 ticket number.

        Args:
            ticket: MT5 ticket number
            close_reason: 'tp_hit', 'sl_hit', 'expired', 'manual', 'target_reached'

        Returns:
            Close confirmation with exit price, PnL, and holding time.
        """
        trade = execute_one(
            "SELECT * FROM trades WHERE user_id = %s AND ticket = %s AND status = 'open'",
            (USER_ID, ticket)
        )
        if not trade:
            return json.dumps({"error": f"Open trade with ticket {ticket} not found"})

        result = bridge.close_order(ticket)
        if "error" in result:
            return json.dumps(result)

        exit_price = result.get("exit_price", 0)
        entry_price = float(trade["entry_price"])
        pip_size = 0.01 if "JPY" in trade["symbol"] else 0.0001

        # Get symbol from pair
        pair = execute_one("SELECT symbol FROM pairs WHERE id = %s", (trade["pair_id"],))
        symbol = pair["symbol"] if pair else ""

        if trade["side"] == "BUY":
            pnl_pips = (exit_price - entry_price) / pip_size
        else:
            pnl_pips = (entry_price - exit_price) / pip_size

        pnl_usd = result.get("pnl", 0)
        holding_minutes = (datetime.now(timezone.utc) - trade["opened_at"]).total_seconds() / 60
        rr_achieved = pnl_pips / float(trade["sl_pips"]) if float(trade["sl_pips"]) > 0 else 0

        execute(
            """UPDATE trades SET exit_price = %s, pnl_pips = %s, pnl_usd = %s, rr_achieved = %s,
                close_reason = %s, status = 'closed', closed_at = NOW(), holding_minutes = %s, updated_at = NOW()
            WHERE id = %s""",
            (exit_price, round(pnl_pips, 1), round(pnl_usd, 2), round(rr_achieved, 2),
             close_reason, round(holding_minutes, 1), trade["id"])
        )

        return json.dumps({
            "success": True,
            "ticket": ticket,
            "symbol": symbol,
            "side": trade["side"],
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl_pips": round(pnl_pips, 1),
            "pnl_usd": round(pnl_usd, 2),
            "rr_achieved": round(rr_achieved, 2),
            "holding_minutes": round(holding_minutes, 1),
            "close_reason": close_reason,
        })

    @mcp.tool()
    def modify_position(ticket: int, new_sl: float = None, new_tp: float = None) -> str:
        """
        Modify SL/TP of an open position (e.g., move to breakeven, trailing stop).

        Args:
            ticket: MT5 ticket number
            new_sl: New stop loss price (optional)
            new_tp: New take profit price (optional)

        Returns:
            Confirmation with old and new values.
        """
        if new_sl is None and new_tp is None:
            return json.dumps({"error": "Provide at least new_sl or new_tp"})

        result = bridge.modify_order(ticket, sl=new_sl, tp=new_tp)
        if "error" in result:
            return json.dumps(result)

        return json.dumps(result)

    @mcp.tool()
    def close_all_positions(symbol: str = None, reason: str = "batch_close") -> str:
        """
        Close all open positions (or filtered by symbol).

        Args:
            symbol: Optional — only close positions for this pair.
            reason: Reason for closing all positions.

        Returns:
            Count closed, total PnL.
        """
        positions = bridge.get_positions()
        if isinstance(positions, dict) and "error" in positions:
            return json.dumps(positions)

        if symbol:
            positions = [p for p in positions if p.get("symbol") == symbol]

        if not positions:
            return json.dumps({"message": "No open positions to close", "closed_count": 0})

        results = []
        total_pnl = 0.0

        for pos in positions:
            result = json.loads(close_position(pos["ticket"], reason))
            results.append(result)
            if result.get("pnl_usd"):
                total_pnl += result["pnl_usd"]

        return json.dumps({
            "closed_count": len(results),
            "total_pnl_usd": round(total_pnl, 2),
            "details": results,
        })

    @mcp.tool()
    def get_open_positions() -> str:
        """
        Get all open positions with live PnL from MT5.

        Returns:
            List of positions with entry, current price, PnL, and age.
        """
        positions = bridge.get_positions()
        if isinstance(positions, dict) and "error" in positions:
            return json.dumps(positions)

        s = _get_settings()
        max_duration = int(s.get("max_trade_duration_minutes", 240))

        enriched = []
        for pos in positions:
            trade = execute_one(
                "SELECT id, comment, opened_at, sl_pips, tp_pips FROM trades WHERE user_id = %s AND ticket = %s AND status = 'open'",
                (USER_ID, pos["ticket"])
            )
            age_minutes = 0
            if trade and trade["opened_at"]:
                age_minutes = (datetime.now(timezone.utc) - trade["opened_at"]).total_seconds() / 60

            enriched.append({
                "ticket": pos["ticket"],
                "trade_id": str(trade["id"]) if trade else None,
                "symbol": pos["symbol"],
                "side": pos["side"],
                "lot_size": pos["lot_size"],
                "entry_price": pos["entry_price"],
                "current_price": pos["current_price"],
                "sl": pos["sl"],
                "tp": pos["tp"],
                "pnl_usd": pos["pnl"],
                "age_minutes": round(age_minutes, 1),
                "expired": age_minutes >= max_duration,
                "comment": trade["comment"] if trade else pos.get("comment", ""),
            })

        return json.dumps({"count": len(enriched), "positions": enriched})

    @mcp.tool()
    def get_account_info() -> str:
        """
        Get MT5 account info: balance, equity, margin, leverage.

        Returns:
            Full account details from the broker.
        """
        result = bridge.get_account()
        if "error" in result:
            return json.dumps(result)

        return json.dumps({
            "balance": result["balance"],
            "equity": result["equity"],
            "margin_used": result["margin"],
            "free_margin": result["free_margin"],
            "margin_level_pct": result["margin_level"],
            "leverage": result["leverage"],
            "currency": result["currency"],
            "account_type": "demo" if result.get("trade_mode") == 0 else "live",
        })

    @mcp.tool()
    def get_symbol_info(symbol: str) -> str:
        """
        Get symbol details: spread, pip value, lot sizes, current price.

        Args:
            symbol: Forex pair — EURUSD, GBPUSD, etc.

        Returns:
            Spread in pips, pip value, min/max lot, bid/ask.
        """
        return json.dumps(bridge.get_symbol_info(symbol))

    @mcp.tool()
    def get_basket_status(symbol: str = None) -> str:
        """
        Get basket (grouped by symbol) status for all open positions.
        Shows net PnL per basket, individual legs, and whether hedge is active.

        Args:
            symbol: Optional — filter by specific pair. If None, returns all active baskets.

        Returns:
            List of baskets with net PnL, individual positions, hedge status, and recommendation.
        """
        positions = bridge.get_positions()
        if isinstance(positions, dict) and "error" in positions:
            return json.dumps(positions)

        if not positions or (isinstance(positions, list) and len(positions) == 1 and isinstance(positions[0], dict) and not positions[0]):
            return json.dumps({"baskets": [], "total_floating_pnl": 0, "message": "No open positions"})

        # Filter valid positions
        valid_positions = [p for p in positions if isinstance(p, dict) and p.get("symbol")]

        if symbol:
            valid_positions = [p for p in valid_positions if p.get("symbol", "").replace("#", "").replace(".", "") == symbol or p.get("symbol") == symbol]

        # Group by symbol (basket)
        baskets_map: dict = {}
        for pos in valid_positions:
            sym = pos.get("symbol", "UNKNOWN").replace("#", "")
            if sym not in baskets_map:
                baskets_map[sym] = {"buy_legs": [], "sell_legs": [], "total_buy_lots": 0, "total_sell_lots": 0}

            leg = {
                "ticket": pos.get("ticket"),
                "side": "BUY" if pos.get("type") == 0 else "SELL",
                "lots": pos.get("volume", 0),
                "open_price": pos.get("price_open", 0),
                "current_price": pos.get("price_current", 0),
                "pnl": pos.get("profit", 0),
                "swap": pos.get("swap", 0),
                "comment": pos.get("comment", ""),
            }

            if leg["side"] == "BUY":
                baskets_map[sym]["buy_legs"].append(leg)
                baskets_map[sym]["total_buy_lots"] += leg["lots"]
            else:
                baskets_map[sym]["sell_legs"].append(leg)
                baskets_map[sym]["total_sell_lots"] += leg["lots"]

        # Build basket summaries
        baskets = []
        total_floating = 0

        for sym, data in baskets_map.items():
            all_legs = data["buy_legs"] + data["sell_legs"]
            net_pnl = sum(leg["pnl"] + leg["swap"] for leg in all_legs)
            total_floating += net_pnl

            is_hedged = bool(data["buy_legs"] and data["sell_legs"])
            net_lots = round(data["total_buy_lots"] - data["total_sell_lots"], 2)

            # Determine basket state
            if is_hedged:
                if abs(net_lots) < 0.01:
                    state = "FULLY_HEDGED"
                else:
                    state = "PARTIALLY_HEDGED"
            else:
                state = "UNHEDGED"

            # Recommendation
            if net_pnl > 0:
                recommendation = "CLOSE_BASKET_PROFIT"
            elif is_hedged and net_pnl < 0:
                recommendation = "MONITOR_FOR_UNLOCK"
            elif not is_hedged and net_pnl < -10:
                recommendation = "CONSIDER_HEDGE"
            else:
                recommendation = "HOLD"

            basket = {
                "symbol": sym,
                "state": state,
                "net_pnl": round(net_pnl, 2),
                "net_lots": net_lots,
                "direction": "LONG" if net_lots > 0 else "SHORT" if net_lots < 0 else "NEUTRAL",
                "buy_legs": data["buy_legs"],
                "sell_legs": data["sell_legs"],
                "total_positions": len(all_legs),
                "is_hedged": is_hedged,
                "recommendation": recommendation,
            }
            baskets.append(basket)

        # Get basket_ids from DB for context
        db_baskets = execute(
            "SELECT DISTINCT basket_id, pair_id FROM trades WHERE user_id = %s AND status = 'open' AND basket_id IS NOT NULL",
            (USER_ID,)
        )

        return json.dumps({
            "baskets": baskets,
            "total_baskets": len(baskets),
            "total_floating_pnl": round(total_floating, 2),
            "hedged_baskets": sum(1 for b in baskets if b["is_hedged"]),
            "db_basket_ids": [r["basket_id"] for r in db_baskets] if db_baskets else [],
        })
