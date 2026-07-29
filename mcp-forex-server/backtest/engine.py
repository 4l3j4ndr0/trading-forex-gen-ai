"""
Walk-forward backtest engine for the Recovery Zone / SMC forex strategy.

Scope (v1 — see AGENT_PROMPT_V2.md and the assistant's analysis for context):
  - Reuses the SAME deterministic code the live agent's tools use:
    get_full_analysis() for RSI/MACD/ADX/EMA/divergences/recommendation, and
    _analyze_market_structure() for SMC swings/BOS/CHoCH/Order Blocks/FVGs/bias.
    This is not a reimplementation — it's the production logic replayed
    against historical candles with no lookahead.
  - The "Trade Quality Score" (H4 bias / POI / M15 BOS-CHoCH / RSI divergence /
    session) is otherwise pure LLM judgment in the live system (the prompt
    describes it, nothing in code enforces it). This engine implements a
    deterministic proxy of that same rubric so the rule itself can be tested
    and tuned — it will not perfectly match what the live LLM agent would
    have decided on any single trade, but it tests the documented rule
    faithfully.
  - NO hedging/basket simulation in v1: every trade is a plain SL/TP
    directional position. The Recovery Zone hedge logic depends on
    LLM-judged "BOS/CHoCH confirmation" nuance that's hard to replicate
    faithfully, and there's no point simulating a safety net before we know
    whether the underlying entries have any edge at all.
  - No historical economic-calendar data is available, so the news filter
    (Fase 3, Paso 1) is NOT applied. Live performance around NFP/FOMC/ECB
    could differ from this backtest.
  - Entry price = the M15 candle's close at signal time (a same-bar-close
    approximation, not true next-tick execution).
  - If SL and TP are both touched within the same M15 bar, SL is assumed to
    have been hit first (conservative — avoids overstating results).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

from src.clients.local_indicators import get_full_analysis
from src.tools.market_data import _analyze_market_structure
from src.tools.quality_score import evaluate_setup, pip_size as _pip_size

ANALYSIS_WINDOW = 200  # matches count=200 used by forex_analysis/forex_multi_timeframe live
STRUCTURE_WINDOW = {"D1": 200, "H4": 200, "H1": 200, "M15": 100}


def _pip_value_per_lot(symbol: str, price: float) -> float:
    """Same formula as calculate_lot_size() in src/tools/smart.py."""
    pip_size = _pip_size(symbol)
    quote = symbol[3:]
    if quote == "USD":
        return pip_size * 100000
    if symbol[:3] == "USD":
        return pip_size * 100000 / price
    return pip_size * 100000 / price if price > 2 else pip_size * 100000


def calc_lot_size(symbol: str, sl_pips: float, balance: float, risk_pct: float, price: float, max_lot: float) -> tuple[float, float]:
    """Same formula as calculate_lot_size(). Returns (lot, risk_usd)."""
    if sl_pips <= 0:
        return 0.0, 0.0
    pip_value = _pip_value_per_lot(symbol, price)
    risk_usd = balance * risk_pct / 100
    calculated_lot = risk_usd / (sl_pips * pip_value)
    lot = round(int(calculated_lot * 100) / 100, 2)
    lot = min(lot, max_lot)
    lot = max(lot, 0.01)
    return lot, risk_usd


def calc_optimal_sl_tp(symbol: str, side: str, h1_analysis: dict, h1_structure: dict, min_rr: float) -> dict:
    """Same ATR-based formula as get_optimal_sl_tp(), plus the prompt's
    'SL behind structure' rule: extend the ATR stop to clear the nearest H1
    swing level (+2 pips buffer) when structure requires more room than ATR."""
    close = h1_analysis["price"]["close"]
    pip_size = _pip_size(symbol)
    atr_pips = h1_analysis["indicators"]["atr_pips"] or 15.0
    if atr_pips < 5:
        atr_pips = 15.0

    sl_mult, tp1_mult, tp2_mult = 1.5, 2.0, 3.0
    sl_pips = max(round(atr_pips * sl_mult, 1), 10.0)

    swing_low = h1_structure.get("structure", {}).get("last_swing_low")
    swing_high = h1_structure.get("structure", {}).get("last_swing_high")
    if side == "BUY" and swing_low:
        structure_sl_pips = round((close - swing_low["price"]) / pip_size, 1) + 2
        sl_pips = max(sl_pips, structure_sl_pips)
    elif side == "SELL" and swing_high:
        structure_sl_pips = round((swing_high["price"] - close) / pip_size, 1) + 2
        sl_pips = max(sl_pips, structure_sl_pips)

    tp1_pips = round(atr_pips * tp1_mult, 1)
    tp2_pips = round(atr_pips * tp2_mult, 1)
    rr2 = tp2_pips / sl_pips if sl_pips > 0 else 0
    tp_pips = tp2_pips if rr2 >= min_rr else tp1_pips

    if side == "BUY":
        sl_price = close - sl_pips * pip_size
        tp_price = close + tp_pips * pip_size
    else:
        sl_price = close + sl_pips * pip_size
        tp_price = close - tp_pips * pip_size

    return {"sl_pips": sl_pips, "tp_pips": tp_pips, "sl_price": sl_price, "tp_price": tp_price,
            "rr_ratio": round(tp_pips / sl_pips, 2) if sl_pips > 0 else 0}


class _AsOf:
    """Tracks, per (symbol, timeframe), the index of the last candle with
    time <= current simulated T, and caches analysis results keyed by that
    index so repeated M15 ticks within the same H1/H4/D1 bar don't redo
    O(n^2) indicator work."""

    def __init__(self, candles_by_symbol: dict[str, dict[str, list[dict]]]):
        self.candles = candles_by_symbol
        self._idx = {}
        self._cache = {}

    def advance(self, symbol: str, tf: str, t: int) -> int:
        candles = self.candles[symbol][tf]
        key = (symbol, tf)
        idx = self._idx.get(key, -1)
        n = len(candles)
        while idx + 1 < n and candles[idx + 1]["time"] <= t:
            idx += 1
        self._idx[key] = idx
        return idx

    def slice(self, symbol: str, tf: str, idx: int) -> list[dict]:
        window = STRUCTURE_WINDOW.get(tf, ANALYSIS_WINDOW)
        return self.candles[symbol][tf][max(0, idx - window + 1): idx + 1]

    def full_analysis(self, symbol: str, tf: str, idx: int) -> dict | None:
        key = (symbol, tf, "full", idx)
        if key in self._cache:
            return self._cache[key]
        sl = self.slice(symbol, tf, idx)
        result = get_full_analysis(symbol, tf, candles=sl) if len(sl) >= 50 else {"error": "warmup"}
        self._cache[key] = None if "error" in result else result
        return self._cache[key]

    def structure(self, symbol: str, tf: str, idx: int) -> dict | None:
        key = (symbol, tf, "struct", idx)
        if key in self._cache:
            return self._cache[key]
        sl = self.slice(symbol, tf, idx)
        result = _analyze_market_structure(sl, symbol, tf) if len(sl) >= 30 else {"error": "warmup"}
        self._cache[key] = None if "error" in result else result
        return self._cache[key]


@dataclass
class Position:
    symbol: str
    side: str
    entry_time: int
    entry_price: float
    sl_price: float
    tp_price: float
    sl_pips: float
    tp_pips: float
    lot_size: float
    risk_usd: float
    score: int
    reasoning: str


@dataclass
class ClosedTrade:
    symbol: str
    side: str
    entry_time: int
    exit_time: int
    entry_price: float
    exit_price: float
    pnl_pips: float
    pnl_usd: float
    close_reason: str
    rr_achieved: float
    holding_minutes: float
    score: int


@dataclass
class Settings:
    max_risk_per_trade_pct: float = 2.0
    max_daily_loss_pct: float = 10.0
    max_lot_size: float = 0.05
    max_open_positions: int = 5
    min_rr_ratio: float = 2.0
    daily_target_pct: float = 3.0
    min_adx_entry: float = 15.0
    max_consecutive_losses: int = 5
    consecutive_loss_cooldown_minutes: int = 120
    score_threshold: int = 3
    max_trade_duration_minutes: int = 5760


@dataclass
class BacktestResult:
    trades: list[ClosedTrade] = field(default_factory=list)
    equity_curve: list[tuple[int, float]] = field(default_factory=list)
    ending_balance: float = 0.0
    starting_balance: float = 0.0


def evaluate_entry(asof: _AsOf, symbol: str, t: int, dt_utc: datetime, settings: Settings) -> Position | None:
    """Advance this symbol's candle pointers to T and score the setup via the
    SAME evaluate_setup() the live get_trade_quality_score() tool uses — no
    separate scoring logic here, so backtest and live can't drift. Passes
    _AsOf's per-bar cache in so D1/H4/H1 analysis isn't recomputed on every
    M15 tick (only when that timeframe's bar actually advances)."""
    idx = {tf: asof.advance(symbol, tf, t) for tf in ("D1", "H4", "H1", "M15")}

    result = evaluate_setup(
        symbol, dt_utc=dt_utc, min_adx_entry=settings.min_adx_entry,
        full_analysis_fn=lambda sym, tf: asof.full_analysis(sym, tf, idx[tf]),
        structure_fn=lambda sym, tf: asof.structure(sym, tf, idx[tf]),
    )
    if "no_setup" in result:
        return None
    if result["score"] < settings.score_threshold:
        return None

    side = result["side"]
    sltp = calc_optimal_sl_tp(symbol, side, result["h1_analysis"], result["h1_structure"] or {}, settings.min_rr_ratio)
    if sltp["rr_ratio"] < settings.min_rr_ratio:
        return None

    return Position(
        symbol=symbol, side=side, entry_time=t, entry_price=result["current_price"],
        sl_price=sltp["sl_price"], tp_price=sltp["tp_price"],
        sl_pips=sltp["sl_pips"], tp_pips=sltp["tp_pips"],
        lot_size=0.0, risk_usd=0.0, score=result["score"],
        reasoning=f"H4={side} align={result['align_score']} adx={result['adx_h1']:.1f} score={result['score']}",
    )


class BacktestEngine:
    def __init__(self, pairs: list[str], candles_by_symbol: dict[str, dict[str, list[dict]]],
                 settings: Settings, starting_balance: float, start_time: int, end_time: int):
        self.pairs = pairs
        self.asof = _AsOf(candles_by_symbol)
        self.settings = settings
        self.balance = starting_balance
        self.starting_balance = starting_balance
        self.start_time = start_time
        self.end_time = end_time
        self.open_positions: dict[str, Position] = {}
        self.closed_trades: list[ClosedTrade] = []
        self.equity_curve: list[tuple[int, float]] = []
        self._daily_pnl = 0.0
        self._daily_day = None

    def _reset_daily_if_needed(self, dt_utc: datetime):
        day = dt_utc.date()
        if self._daily_day != day:
            self._daily_day = day
            self._daily_pnl = 0.0

    def _cooldown_active(self, t: int) -> bool:
        s = self.settings
        n = s.max_consecutive_losses
        if len(self.closed_trades) < n:
            return False
        recent = self.closed_trades[-max(n * 2, 20):][::-1]  # most recent first
        streak = 0
        last_loss_time = None
        for tr in recent:
            if tr.pnl_usd < 0:
                streak += 1
                if last_loss_time is None:
                    last_loss_time = tr.exit_time
            else:
                break
        if streak >= n and last_loss_time is not None:
            minutes_since = (t - last_loss_time) / 60
            return minutes_since < s.consecutive_loss_cooldown_minutes
        return False

    def _try_close(self, pos: Position, bar: dict, dt_utc: datetime) -> ClosedTrade | None:
        pip_size = _pip_size(pos.symbol)
        hit_sl = (bar["low"] <= pos.sl_price) if pos.side == "BUY" else (bar["high"] >= pos.sl_price)
        hit_tp = (bar["high"] >= pos.tp_price) if pos.side == "BUY" else (bar["low"] <= pos.tp_price)

        exit_price, reason = None, None
        if hit_sl:  # conservative: SL wins if both touched in the same bar
            exit_price, reason = pos.sl_price, "sl_hit"
        elif hit_tp:
            exit_price, reason = pos.tp_price, "tp_hit"
        else:
            age_min = (bar["time"] - pos.entry_time) / 60
            if age_min >= self.settings.max_trade_duration_minutes:
                exit_price, reason = bar["close"], "expired"

        if exit_price is None:
            return None

        if pos.side == "BUY":
            pnl_pips = (exit_price - pos.entry_price) / pip_size
        else:
            pnl_pips = (pos.entry_price - exit_price) / pip_size
        pip_value = _pip_value_per_lot(pos.symbol, exit_price)
        pnl_usd = pnl_pips * pip_value * pos.lot_size

        trade = ClosedTrade(
            symbol=pos.symbol, side=pos.side, entry_time=pos.entry_time, exit_time=bar["time"],
            entry_price=pos.entry_price, exit_price=exit_price, pnl_pips=round(pnl_pips, 1),
            pnl_usd=round(pnl_usd, 2), close_reason=reason,
            rr_achieved=round(pnl_pips / pos.sl_pips, 2) if pos.sl_pips else 0,
            holding_minutes=round((bar["time"] - pos.entry_time) / 60, 1), score=pos.score,
        )
        return trade

    def run(self) -> BacktestResult:
        s = self.settings
        m15_times = sorted({c["time"] for sym in self.pairs for c in self.asof.candles[sym]["M15"]
                             if self.start_time <= c["time"] < self.end_time})
        bar_by_symbol_time = {
            sym: {c["time"]: c for c in self.asof.candles[sym]["M15"]} for sym in self.pairs
        }

        for t in m15_times:
            dt_utc = datetime.fromtimestamp(t, tz=timezone.utc)
            self._reset_daily_if_needed(dt_utc)
            is_weekend = dt_utc.isoweekday() >= 6
            friday_force_close = dt_utc.isoweekday() == 5 and dt_utc.hour >= 21
            friday_no_new = dt_utc.isoweekday() == 5 and dt_utc.hour >= 18

            # 1) Manage open positions first
            for sym in list(self.open_positions.keys()):
                bar = bar_by_symbol_time.get(sym, {}).get(t)
                if not bar:
                    continue
                pos = self.open_positions[sym]
                trade = None
                if is_weekend:
                    continue
                if friday_force_close:
                    trade = ClosedTrade(
                        symbol=sym, side=pos.side, entry_time=pos.entry_time, exit_time=t,
                        entry_price=pos.entry_price, exit_price=bar["close"], pnl_pips=0, pnl_usd=0,
                        close_reason="friday_close", rr_achieved=0,
                        holding_minutes=round((t - pos.entry_time) / 60, 1), score=pos.score,
                    )
                    pip_size = _pip_size(sym)
                    pnl_pips = (bar["close"] - pos.entry_price) / pip_size if pos.side == "BUY" else (pos.entry_price - bar["close"]) / pip_size
                    trade.pnl_pips = round(pnl_pips, 1)
                    trade.pnl_usd = round(pnl_pips * _pip_value_per_lot(sym, bar["close"]) * pos.lot_size, 2)
                else:
                    trade = self._try_close(pos, bar, dt_utc)

                if trade:
                    self.balance += trade.pnl_usd
                    self._daily_pnl += trade.pnl_usd
                    self.closed_trades.append(trade)
                    del self.open_positions[sym]
                    self.equity_curve.append((t, self.balance))

            if is_weekend:
                continue

            # 2) Daily loss / target gates
            max_loss_usd = self.balance * s.max_daily_loss_pct / 100
            target_usd = self.balance * s.daily_target_pct / 100
            if self._daily_pnl <= -max_loss_usd or self._daily_pnl >= target_usd:
                continue
            if friday_no_new:
                continue
            if self._cooldown_active(t):
                continue
            if len(self.open_positions) >= s.max_open_positions:
                continue

            # 3) New entries — one basket per pair
            for sym in self.pairs:
                if sym in self.open_positions:
                    continue
                if len(self.open_positions) >= s.max_open_positions:
                    break
                bar = bar_by_symbol_time.get(sym, {}).get(t)
                if not bar:
                    continue
                pos = evaluate_entry(self.asof, sym, t, dt_utc, s)
                if pos is None:
                    continue
                lot, risk_usd = calc_lot_size(sym, pos.sl_pips, self.balance, s.max_risk_per_trade_pct, pos.entry_price, s.max_lot_size)
                if lot <= 0:
                    continue
                pos.lot_size, pos.risk_usd = lot, risk_usd
                self.open_positions[sym] = pos

        return BacktestResult(
            trades=self.closed_trades, equity_curve=self.equity_curve,
            ending_balance=self.balance, starting_balance=self.starting_balance,
        )


def compute_stats(result: BacktestResult) -> dict:
    trades = result.trades
    if not trades:
        return {"total_trades": 0, "message": "No trades generated"}

    pnls = [t.pnl_usd for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    peak = max_dd = cumulative = 0.0
    for p in pnls:
        cumulative += p
        peak = max(peak, cumulative)
        max_dd = max(max_dd, peak - cumulative)

    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0

    first_t = datetime.fromtimestamp(trades[0].entry_time, tz=timezone.utc)
    last_t = datetime.fromtimestamp(trades[-1].exit_time, tz=timezone.utc)
    months = max((last_t - first_t).days / 30.44, 1 / 30.44)

    return {
        "total_trades": len(trades),
        "win_rate_pct": round(100 * len(wins) / len(trades), 1),
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else None,
        "total_pnl_usd": round(sum(pnls), 2),
        "avg_pnl_per_trade": round(sum(pnls) / len(trades), 2),
        "avg_win_usd": round(sum(wins) / len(wins), 2) if wins else 0,
        "avg_loss_usd": round(sum(losses) / len(losses), 2) if losses else 0,
        "max_drawdown_usd": round(max_dd, 2),
        "starting_balance": result.starting_balance,
        "ending_balance": round(result.ending_balance, 2),
        "return_pct": round(100 * (result.ending_balance - result.starting_balance) / result.starting_balance, 2),
        "trades_per_month": round(len(trades) / months, 1),
        "period": f"{first_t.date()} to {last_t.date()}",
        "by_symbol": _stats_by_symbol(trades),
        "by_close_reason": _stats_by_reason(trades),
    }


def _stats_by_symbol(trades: list[ClosedTrade]) -> dict:
    out = {}
    for t in trades:
        d = out.setdefault(t.symbol, {"trades": 0, "pnl_usd": 0.0, "wins": 0})
        d["trades"] += 1
        d["pnl_usd"] += t.pnl_usd
        d["wins"] += 1 if t.pnl_usd > 0 else 0
    for d in out.values():
        d["pnl_usd"] = round(d["pnl_usd"], 2)
        d["win_rate_pct"] = round(100 * d["wins"] / d["trades"], 1)
    return out


def _stats_by_reason(trades: list[ClosedTrade]) -> dict:
    out = {}
    for t in trades:
        d = out.setdefault(t.close_reason, {"count": 0, "pnl_usd": 0.0})
        d["count"] += 1
        d["pnl_usd"] += t.pnl_usd
    for d in out.values():
        d["pnl_usd"] = round(d["pnl_usd"], 2)
    return out
