"""Safety guard — validates all trading operations against hard limits."""

from dataclasses import dataclass
from typing import Optional

from src.core.config import safety
from src.core.database import db


@dataclass
class SafetyCheck:
    """Result of a safety check."""
    allowed: bool
    reason: Optional[str] = None


class SafetyGuard:
    """Validates trading operations against safety rules."""

    @staticmethod
    def can_open_position(symbol: str, lot_size: float) -> SafetyCheck:
        """Check if a new position can be opened."""

        if safety.kill_switch:
            return SafetyCheck(False, "KILL SWITCH ACTIVE — all trading halted")

        if symbol not in safety.allowed_symbols:
            return SafetyCheck(False, f"Symbol '{symbol}' not in allowed list: {safety.allowed_symbols}")

        if lot_size > safety.max_lot_size:
            return SafetyCheck(False, f"Lot size {lot_size} exceeds max {safety.max_lot_size}")

        open_trades = db.get_open_trades()
        if len(open_trades) >= safety.max_open_positions:
            return SafetyCheck(False, f"Max open positions ({safety.max_open_positions}) reached")

        daily_pnl = db.get_daily_pnl()
        if daily_pnl <= -safety.max_daily_loss_usd:
            return SafetyCheck(False, f"Daily loss limit (${safety.max_daily_loss_usd}) reached. PnL today: ${daily_pnl:.2f}")

        consecutive = db.get_consecutive_losses()
        if consecutive >= safety.max_consecutive_losses:
            return SafetyCheck(False, f"{consecutive} consecutive losses — trading paused")

        return SafetyCheck(True)

    @staticmethod
    def get_rules_summary() -> dict:
        """Return current safety rules as a dict."""
        return {
            "max_open_positions": safety.max_open_positions,
            "max_lot_size_usd": safety.max_lot_size,
            "max_daily_loss_usd": safety.max_daily_loss_usd,
            "max_consecutive_losses": safety.max_consecutive_losses,
            "min_balance_usd": safety.min_balance_usd,
            "allowed_symbols": safety.allowed_symbols,
            "kill_switch": safety.kill_switch,
            "note": "lot_size is in USD. Binance minimum notional is $50.",
        }
