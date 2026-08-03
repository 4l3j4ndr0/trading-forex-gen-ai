"""
Walk-forward backtest for the redesigned SP500 once-daily Wyckoff strategy.

Reuses the SAME pure functions the live tools use (src/tools/structure.py's
_detect_swing_points, _detect_bos_choch_historical, _detect_wyckoff_phase) —
not a reimplementation, so backtest and live can't silently drift apart.

Cadence (see /Users/usuario/.claude/plans/sharded-cooking-sun.md for the
full design rationale):
  - Phase A ("daily plan"), once per trading day, `plan_offset_minutes`
    after AM killzone open: reads H1 structure trend (BULLISH/BEARISH/
    RANGING) to set daily_bias. RANGING -> no trade today.
  - Phase B ("mechanical trigger"), scanned bar-by-bar across the AM and PM
    killzones until it fires or the day ends: looks for a FRESH (candles_ago
    == 0) M5 wyckoff.spring (if daily_bias=BUY) or wyckoff.upthrust (if
    daily_bias=SELL) with penetration >= min_sweep_distance_points. First
    hit wins — hard cap of 1 trade/day.
  - SL = MAX(points behind the spring/upthrust wick, sl_atr_mult * ATR(14)
    H1) — the structure invalidation point, floored by an ATR buffer so a
    multi-hour hold isn't stopped out by ordinary M5 noise.
  - TP = SL * min_rr_ratio. Optional breakeven-at-R trailing. Forced close
    at regular_session_end (16:00 ET) if unresolved — no overnight in v1.
  - No news filter (no historical economic-calendar data), no hedging —
    same scope limitations the forex backtest documents for the same reasons.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field
from datetime import datetime, date, time as dtime, timedelta, timezone

import pytz

from src.tools.structure import (
    _detect_swing_points, _detect_bos_choch_historical, _detect_wyckoff_phase, _calculate_effort_result,
)

NY_TZ = pytz.timezone("America/New_York")
H1_LOOKBACK = 150
M5_LOOKBACK = 110


def _et_bound(d: date, hhmm: str) -> int:
    """Convert an ET-local 'HH:MM' time on calendar date d to a UTC unix timestamp (DST-aware)."""
    h, m = (int(x) for x in hhmm.split(":"))
    local_dt = NY_TZ.localize(datetime.combine(d, dtime(h, m)))
    return int(local_dt.astimezone(timezone.utc).timestamp())


def _atr(candles: list[dict], period: int = 14) -> float:
    if len(candles) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i]["high"], candles[i]["low"], candles[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    window = trs[-period:]
    return sum(window) / len(window) if window else 0.0


def _tf_score(structure_trend: str, wyckoff_phase: str) -> float:
    """Same scoring convention as the live sp500_multi_timeframe() tool."""
    score = 1 if structure_trend == "BULLISH" else -1 if structure_trend == "BEARISH" else 0
    if wyckoff_phase in ("ACCUMULATION_SPRING", "ACCUMULATION"):
        score += 0.5
    elif wyckoff_phase in ("DISTRIBUTION_UPTHRUST", "DISTRIBUTION"):
        score -= 0.5
    return score


def calc_lot_size(sl_points: float, balance: float, risk_pct: float, point_value: float,
                   lot_step: float, min_lot: float, max_lot: float) -> tuple[float, float]:
    """Same formula as sp500_calculate_risk() — floors to the broker lot_step."""
    if sl_points <= 0 or balance <= 0:
        return 0.0, 0.0
    risk_usd = balance * risk_pct / 100.0
    raw_lot = risk_usd / (sl_points * point_value)
    stepped = int(raw_lot / lot_step) * lot_step
    lot = max(min_lot, min(max_lot, stepped))
    return round(lot, 2), risk_usd


@dataclass
class Settings:
    starting_balance: float = 1000.0
    point_value: float = 1.0
    min_lot: float = 0.10
    max_lot: float = 5.0
    lot_step: float = 0.10
    max_risk_per_trade_pct: float = 1.0
    min_rr_ratio: float = 1.5
    sl_atr_mult: float = 1.0
    sl_structure_buffer_points: float = 3.0
    min_structure_score: float = 1.5
    min_sweep_distance_points: float = 5.0
    max_consecutive_losses: int = 5
    plan_offset_minutes: int = 15
    breakeven_at_r: float = 0.0  # 0 disables; e.g. 1.0 = move SL to entry once +1R is reached
    am_killzone_start: str = "09:30"
    am_killzone_end: str = "11:30"
    pm_killzone_start: str = "14:00"
    pm_killzone_end: str = "16:00"
    regular_session_end: str = "16:00"


@dataclass
class ClosedTrade:
    side: str
    entry_time: int
    exit_time: int
    entry_price: float
    exit_price: float
    sl_points: float
    tp_points: float
    pnl_points: float
    pnl_usd: float
    close_reason: str
    rr_achieved: float
    holding_minutes: float
    daily_bias_score: float
    sweep_penetration_points: float


@dataclass
class DayLog:
    trading_day: str
    daily_bias: str | None
    reason: str


@dataclass
class BacktestResult:
    trades: list[ClosedTrade] = field(default_factory=list)
    day_logs: list[DayLog] = field(default_factory=list)
    equity_curve: list[tuple[int, float]] = field(default_factory=list)
    starting_balance: float = 0.0
    ending_balance: float = 0.0


class _TimeSeries:
    """Sorted (times, candles) for one timeframe, with bisect-based as-of slicing."""

    def __init__(self, candles: list[dict]):
        self.candles = sorted(candles, key=lambda c: c["time"])
        self.times = [c["time"] for c in self.candles]

    def slice_as_of(self, t: int, lookback: int) -> list[dict]:
        idx = bisect.bisect_right(self.times, t)
        return self.candles[max(0, idx - lookback): idx]

    def bars_in(self, start: int, end: int) -> list[dict]:
        lo = bisect.bisect_left(self.times, start)
        hi = bisect.bisect_left(self.times, end)
        return self.candles[lo:hi]


def _daily_bias(h1: _TimeSeries, plan_time: int) -> tuple[str | None, float, str]:
    """
    Phase A: H1 structure trend sets the day's directional bias.

    When H1 swing-structure is RANGING (the common case — a clean 3-swing
    HH+HL/LH+LL sequence is strict and real price rarely holds it), fall
    back to the same carve-out the strategy always intended ("H1 RANGING:
    ambos lados permitidos SI el Effort/Result confirma" / spring-upthrust
    on H1 itself): Effort-vs-Result absorption/distribution, or an already-
    forming H1 Wyckoff accumulation/distribution phase, can still set a
    directional bias. Only truly directionless days are skipped.
    """
    window = h1.slice_as_of(plan_time, H1_LOOKBACK)
    if len(window) < 30:
        return None, 0.0, "H1 insuficiente para plan diario"

    opens = [float(c["open"]) for c in window]
    highs = [float(c["high"]) for c in window]
    lows = [float(c["low"]) for c in window]
    closes = [float(c["close"]) for c in window]
    swing_highs, swing_lows = _detect_swing_points(highs, lows, 2)
    structure = _detect_bos_choch_historical(highs, lows, closes, swing_highs, swing_lows)
    wyckoff = _detect_wyckoff_phase(window, swing_highs, swing_lows, closes[-1])
    score = _tf_score(structure["structure"], wyckoff.get("phase", ""))

    if structure["structure"] == "BULLISH":
        return "BUY", score, f"H1 BULLISH, wyckoff={wyckoff.get('phase')}, score={score}"
    if structure["structure"] == "BEARISH":
        return "SELL", score, f"H1 BEARISH, wyckoff={wyckoff.get('phase')}, score={score}"

    # RANGING fallback
    phase = wyckoff.get("phase", "")
    if phase in ("ACCUMULATION_SPRING", "ACCUMULATION"):
        return "BUY", score, f"H1 RANGING pero wyckoff={phase} (spring en H1), score={score}"
    if phase in ("DISTRIBUTION_UPTHRUST", "DISTRIBUTION"):
        return "SELL", score, f"H1 RANGING pero wyckoff={phase} (upthrust en H1), score={score}"

    er = _calculate_effort_result(opens, highs, lows, closes, lookback=10)
    if er["harmony"] == "DIVERGENT" and er["dominant_effort"] == "BEARISH":
        return "BUY", score, f"H1 RANGING pero absorcion (E/R divergent, bearish effort), score={score}"
    if er["harmony"] == "DIVERGENT" and er["dominant_effort"] == "BULLISH":
        return "SELL", score, f"H1 RANGING pero distribucion (E/R divergent, bullish effort), score={score}"

    return None, score, f"H1 RANGING sin wyckoff ni E/R claro — sin bias, no hay trade hoy (score={score})"


def _find_trigger(m5: _TimeSeries, bias: str, scan_times: list[int], min_sweep_pts: float):
    """Phase B: scan candidate M5 bars for a FRESH spring/upthrust in the daily_bias direction."""
    for t in scan_times:
        window = m5.slice_as_of(t, M5_LOOKBACK)
        if len(window) < 30:
            continue
        highs = [float(c["high"]) for c in window]
        lows = [float(c["low"]) for c in window]
        swing_highs, swing_lows = _detect_swing_points(highs, lows, 2)
        current_price = float(window[-1]["close"])
        wyckoff = _detect_wyckoff_phase(window, swing_highs, swing_lows, current_price)

        cand = wyckoff.get("spring") if bias == "BUY" else wyckoff.get("upthrust")
        if not cand or cand.get("candles_ago") != 0:
            continue
        if cand["penetration_points"] < min_sweep_pts:
            continue
        score = _tf_score("BULLISH" if bias == "BUY" else "BEARISH", wyckoff.get("phase", ""))
        return t, window[-1], cand, score
    return None


def _manage_position(m5: _TimeSeries, side: str, entry_time: int, entry_price: float,
                      sl_price: float, tp_price: float, session_end: int, settings: Settings) -> tuple[float, int, str]:
    """Walk M5 bars forward from entry until SL/TP/session-end. Returns (exit_price, exit_time, reason)."""
    r_points = abs(entry_price - sl_price)
    be_armed = False
    cur_sl = sl_price

    for bar in m5.bars_in(entry_time + 1, session_end):
        hi, lo = float(bar["high"]), float(bar["low"])

        if settings.breakeven_at_r > 0 and not be_armed:
            favorable = (hi - entry_price) if side == "BUY" else (entry_price - lo)
            if favorable >= settings.breakeven_at_r * r_points:
                cur_sl = entry_price
                be_armed = True

        hit_sl = (lo <= cur_sl) if side == "BUY" else (hi >= cur_sl)
        hit_tp = (hi >= tp_price) if side == "BUY" else (lo <= tp_price)

        if hit_sl:  # conservative: SL wins if both touched in the same bar
            reason = "breakeven" if be_armed and cur_sl == entry_price else "sl_hit"
            return cur_sl, bar["time"], reason
        if hit_tp:
            return tp_price, bar["time"], "tp_hit"

    # Unresolved by session end — force close at last available price
    remaining = m5.bars_in(entry_time, session_end + 3600)
    last_price = float(remaining[-1]["close"]) if remaining else entry_price
    return last_price, session_end, "session_end"


class BacktestEngine:
    def __init__(self, candles: dict[str, list[dict]], settings: Settings, start_date: date, end_date: date):
        self.h1 = _TimeSeries(candles["H1"])
        self.m5 = _TimeSeries(candles["M5"])
        self.settings = settings
        self.start_date = start_date
        self.end_date = end_date
        self.balance = settings.starting_balance

    def run(self) -> BacktestResult:
        s = self.settings
        trades: list[ClosedTrade] = []
        day_logs: list[DayLog] = []
        equity_curve: list[tuple[int, float]] = []

        d = self.start_date
        while d <= self.end_date:
            if d.weekday() >= 5:
                d += timedelta(days=1)
                continue

            # Consecutive-loss gate — with 1 trade/day, N-in-a-row losses == N losing days.
            if s.max_consecutive_losses and len(trades) >= s.max_consecutive_losses:
                recent = trades[-s.max_consecutive_losses:]
                if all(t.pnl_usd < 0 for t in recent):
                    day_logs.append(DayLog(d.isoformat(), None, "Cooldown: racha de perdidas consecutivas alcanzo el maximo"))
                    d += timedelta(days=1)
                    continue

            am_start = _et_bound(d, s.am_killzone_start)
            am_end = _et_bound(d, s.am_killzone_end)
            pm_start = _et_bound(d, s.pm_killzone_start)
            pm_end = _et_bound(d, s.pm_killzone_end)
            session_end = _et_bound(d, s.regular_session_end)
            plan_time = am_start + s.plan_offset_minutes * 60

            bias, h1_score, reason = _daily_bias(self.h1, plan_time)
            if bias is None:
                day_logs.append(DayLog(d.isoformat(), None, reason))
                d += timedelta(days=1)
                continue

            scan_times = [c["time"] for c in self.m5.bars_in(plan_time, am_end)] + \
                         [c["time"] for c in self.m5.bars_in(pm_start, pm_end)]
            trigger = _find_trigger(self.m5, bias, scan_times, s.min_sweep_distance_points)
            if trigger is None:
                day_logs.append(DayLog(d.isoformat(), bias, f"{reason} — sin spring/upthrust fresco en killzones"))
                d += timedelta(days=1)
                continue

            entry_time, entry_bar, cand, trigger_score = trigger
            total_score = h1_score + trigger_score
            if abs(total_score) < s.min_structure_score:
                day_logs.append(DayLog(d.isoformat(), bias, f"Trigger encontrado pero score {total_score} < min_structure_score {s.min_structure_score}"))
                d += timedelta(days=1)
                continue

            entry_price = float(entry_bar["close"])
            h1_window = self.h1.slice_as_of(entry_time, H1_LOOKBACK)
            atr_h1 = _atr(h1_window, 14)
            structure_sl_pts = abs(entry_price - cand["sl_suggested"])
            sl_points = max(structure_sl_pts, s.sl_atr_mult * atr_h1, s.sl_structure_buffer_points)
            tp_points = sl_points * s.min_rr_ratio

            if bias == "BUY":
                sl_price, tp_price = entry_price - sl_points, entry_price + tp_points
            else:
                sl_price, tp_price = entry_price + sl_points, entry_price - tp_points

            lot, risk_usd = calc_lot_size(sl_points, self.balance, s.max_risk_per_trade_pct,
                                           s.point_value, s.lot_step, s.min_lot, s.max_lot)
            if lot <= 0:
                day_logs.append(DayLog(d.isoformat(), bias, "Trigger valido pero lot_size calculado es 0 — balance insuficiente"))
                d += timedelta(days=1)
                continue

            exit_price, exit_time, close_reason = _manage_position(
                self.m5, bias, entry_time, entry_price, sl_price, tp_price, session_end, s
            )

            pnl_points = (exit_price - entry_price) if bias == "BUY" else (entry_price - exit_price)
            pnl_usd = round(pnl_points * s.point_value * lot, 2)
            self.balance += pnl_usd

            trades.append(ClosedTrade(
                side=bias, entry_time=entry_time, exit_time=exit_time,
                entry_price=round(entry_price, 2), exit_price=round(exit_price, 2),
                sl_points=round(sl_points, 2), tp_points=round(tp_points, 2),
                pnl_points=round(pnl_points, 2), pnl_usd=pnl_usd, close_reason=close_reason,
                rr_achieved=round(pnl_points / sl_points, 2) if sl_points else 0,
                holding_minutes=round((exit_time - entry_time) / 60, 1),
                daily_bias_score=round(total_score, 2),
                sweep_penetration_points=cand["penetration_points"],
            ))
            equity_curve.append((exit_time, round(self.balance, 2)))
            day_logs.append(DayLog(d.isoformat(), bias, f"TRADE: {bias} entry={entry_price} sl={sl_points}pts tp={tp_points}pts -> {close_reason} pnl=${pnl_usd}"))

            d += timedelta(days=1)

        return BacktestResult(
            trades=trades, day_logs=day_logs, equity_curve=equity_curve,
            starting_balance=s.starting_balance, ending_balance=round(self.balance, 2),
        )


def compute_stats(result: BacktestResult) -> dict:
    trades = result.trades
    tradeable_days = len(result.day_logs)
    if not trades:
        return {"total_trades": 0, "tradeable_days": tradeable_days, "message": "No trades generated"}

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

    by_reason: dict[str, dict] = {}
    for t in trades:
        d = by_reason.setdefault(t.close_reason, {"count": 0, "pnl_usd": 0.0})
        d["count"] += 1
        d["pnl_usd"] += t.pnl_usd
    for d in by_reason.values():
        d["pnl_usd"] = round(d["pnl_usd"], 2)

    return {
        "total_trades": len(trades),
        "tradeable_days_scanned": tradeable_days,
        "trade_frequency_pct": round(100 * len(trades) / tradeable_days, 1) if tradeable_days else 0,
        "win_rate_pct": round(100 * len(wins) / len(trades), 1),
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else None,
        "total_pnl_usd": round(sum(pnls), 2),
        "avg_pnl_per_trade": round(sum(pnls) / len(trades), 2),
        "avg_win_usd": round(sum(wins) / len(wins), 2) if wins else 0,
        "avg_loss_usd": round(sum(losses) / len(losses), 2) if losses else 0,
        "max_drawdown_usd": round(max_dd, 2),
        "starting_balance": result.starting_balance,
        "ending_balance": result.ending_balance,
        "return_pct": round(100 * (result.ending_balance - result.starting_balance) / result.starting_balance, 2),
        "period": f"{first_t.date()} to {last_t.date()}",
        "by_close_reason": by_reason,
    }
