"""
CLI entry point for the SP500 once-daily Wyckoff strategy backtest.

Usage:
    python -m backtest.run_backtest --from 2025-11-01 --to 2026-08-01 \
        --balance 1000 --min-rr 1.5 --sl-atr-mult 1.0 --min-structure-score 1.5

Run from sp500-mcp-server/. Requires DATABASE_URL and MT5_BRIDGE_* in .env
(same as the live server) — pulls sp500_settings from the DB and candles
from the bridge's /candles_range endpoint.
"""

import argparse
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from backtest.data_fetch import fetch_all_timeframes, parse_date
from backtest.engine import BacktestEngine, Settings, compute_stats


def load_settings(overrides: dict) -> Settings:
    s = Settings()
    try:
        from src.clients.database import get_settings as get_db_settings
        row = get_db_settings(force_refresh=True)
        s.point_value = float(row.get("point_value", s.point_value))
        s.min_lot = float(row.get("min_lot", s.min_lot))
        s.max_lot = float(row.get("max_lot", s.max_lot))
        s.max_risk_per_trade_pct = float(row.get("max_risk_per_trade_pct", s.max_risk_per_trade_pct))
        s.min_rr_ratio = float(row.get("min_rr_ratio", s.min_rr_ratio))
        s.max_consecutive_losses = int(row.get("max_consecutive_losses", s.max_consecutive_losses))
        s.min_sweep_distance_points = float(row.get("min_sweep_distance_points", s.min_sweep_distance_points))
        s.am_killzone_start = row.get("am_killzone_start", s.am_killzone_start)
        s.am_killzone_end = row.get("am_killzone_end", s.am_killzone_end)
        s.pm_killzone_start = row.get("pm_killzone_start", s.pm_killzone_start)
        s.pm_killzone_end = row.get("pm_killzone_end", s.pm_killzone_end)
        s.regular_session_end = row.get("regular_session_end", s.regular_session_end)
    except Exception as e:
        print(f"[warn] could not load sp500_settings from DB, using defaults: {e}", file=sys.stderr)
    for k, v in overrides.items():
        if v is not None:
            setattr(s, k, v)
    return s


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--from", dest="date_from", required=True, help="YYYY-MM-DD (UTC)")
    p.add_argument("--to", dest="date_to", required=True, help="YYYY-MM-DD (UTC)")
    p.add_argument("--balance", type=float, default=1000.0)
    p.add_argument("--min-rr", dest="min_rr_ratio", type=float, default=None)
    p.add_argument("--sl-atr-mult", dest="sl_atr_mult", type=float, default=None)
    p.add_argument("--min-structure-score", dest="min_structure_score", type=float, default=None)
    p.add_argument("--min-sweep-points", dest="min_sweep_distance_points", type=float, default=None)
    p.add_argument("--breakeven-at-r", dest="breakeven_at_r", type=float, default=None)
    p.add_argument("--plan-offset-min", dest="plan_offset_minutes", type=int, default=None)
    p.add_argument("--no-cache", action="store_true")
    p.add_argument("--out", default=None, help="Write full JSON results (trades + day logs) here")
    args = p.parse_args()

    date_from_ts = parse_date(args.date_from)
    date_to_ts = parse_date(args.date_to)

    overrides = {
        "starting_balance": args.balance,
        "min_rr_ratio": args.min_rr_ratio,
        "sl_atr_mult": args.sl_atr_mult,
        "min_structure_score": args.min_structure_score,
        "min_sweep_distance_points": args.min_sweep_distance_points,
        "breakeven_at_r": args.breakeven_at_r,
        "plan_offset_minutes": args.plan_offset_minutes,
    }
    settings = load_settings(overrides)
    print(f"Settings: {settings}")

    print("Fetching US500Cash candles ...")
    candles = fetch_all_timeframes("US500Cash", date_from_ts, date_to_ts, use_cache=not args.no_cache)
    counts = {tf: len(c) for tf, c in candles.items()}
    print(f"  US500Cash: {counts}")
    if counts.get("M5", 0) < 100 or counts.get("H1", 0) < 100:
        print("[warn] very little candle data returned — check bridge connectivity/date range before trusting results", file=sys.stderr)

    start_date = date.fromisoformat(args.date_from)
    end_date = date.fromisoformat(args.date_to)

    engine = BacktestEngine(candles, settings, start_date, end_date)
    result = engine.run()
    stats = compute_stats(result)

    print("\n=== BACKTEST RESULTS ===")
    print(json.dumps(stats, indent=2, default=str))

    if args.out:
        with open(args.out, "w") as f:
            json.dump({
                "stats": stats,
                "trades": [t.__dict__ for t in result.trades],
                "day_logs": [dl.__dict__ for dl in result.day_logs],
            }, f, indent=2, default=str)
        print(f"\nFull results written to {args.out}")


if __name__ == "__main__":
    main()
