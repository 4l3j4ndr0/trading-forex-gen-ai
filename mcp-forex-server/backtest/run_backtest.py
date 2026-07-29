"""
CLI entry point for the strategy backtest.

Usage:
    python -m backtest.run_backtest --from 2025-08-01 --to 2026-07-28 \
        --pairs EURUSD,GBPUSD,USDJPY,AUDUSD,USDCAD --balance 1000 --score-threshold 3

Run from mcp-forex-server/. Requires DATABASE_URL and MT5_BRIDGE_* in .env
(same as the live server) — pulls trading_settings from the DB and candles
from the bridge's /candles_range endpoint (needs the bridge redeployed with
that endpoint; see mt5-bridge/app.py).
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from backtest.data_fetch import fetch_all_timeframes, parse_date
from backtest.engine import BacktestEngine, Settings, compute_stats

DEFAULT_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "EURGBP", "NZDUSD", "USDCHF", "GBPJPY"]


def load_settings(overrides: dict) -> Settings:
    s = Settings()
    try:
        from src.tools.database import USER_ID
        from src.core.db import execute_one
        row = execute_one("SELECT * FROM trading_settings WHERE user_id = %s", (USER_ID,))
        if row:
            s.max_risk_per_trade_pct = float(row.get("max_risk_per_trade_pct", s.max_risk_per_trade_pct))
            s.max_daily_loss_pct = float(row.get("max_daily_loss_pct", s.max_daily_loss_pct))
            s.max_lot_size = float(row.get("max_lot_size", s.max_lot_size))
            s.max_open_positions = int(row.get("max_open_positions", s.max_open_positions))
            s.min_rr_ratio = float(row.get("min_rr_ratio", s.min_rr_ratio))
            s.daily_target_pct = float(row.get("daily_target_pct", s.daily_target_pct))
            s.min_adx_entry = float(row.get("min_adx_entry", s.min_adx_entry))
            s.max_consecutive_losses = int(row.get("max_consecutive_losses", s.max_consecutive_losses))
            s.consecutive_loss_cooldown_minutes = int(row.get("consecutive_loss_cooldown_minutes", s.consecutive_loss_cooldown_minutes))
    except Exception as e:
        print(f"[warn] could not load trading_settings from DB, using defaults: {e}", file=sys.stderr)
    for k, v in overrides.items():
        if v is not None:
            setattr(s, k, v)
    return s


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--from", dest="date_from", required=True, help="YYYY-MM-DD (UTC)")
    p.add_argument("--to", dest="date_to", required=True, help="YYYY-MM-DD (UTC)")
    p.add_argument("--pairs", default=",".join(DEFAULT_PAIRS))
    p.add_argument("--balance", type=float, default=1000.0)
    p.add_argument("--score-threshold", type=int, default=None)
    p.add_argument("--no-cache", action="store_true")
    p.add_argument("--out", default=None, help="Write full JSON results here")
    args = p.parse_args()

    pairs = [x.strip().upper() for x in args.pairs.split(",") if x.strip()]
    date_from = parse_date(args.date_from)
    date_to = parse_date(args.date_to)

    settings = load_settings({"score_threshold": args.score_threshold})
    print(f"Settings: {settings}")

    candles_by_symbol = {}
    for sym in pairs:
        print(f"Fetching {sym} ...")
        candles_by_symbol[sym] = fetch_all_timeframes(sym, date_from, date_to, use_cache=not args.no_cache)
        counts = {tf: len(c) for tf, c in candles_by_symbol[sym].items()}
        print(f"  {sym}: {counts}")

    engine = BacktestEngine(pairs, candles_by_symbol, settings, args.balance, date_from, date_to)
    result = engine.run()
    stats = compute_stats(result)

    print("\n=== BACKTEST RESULTS ===")
    print(json.dumps(stats, indent=2, default=str))

    if args.out:
        with open(args.out, "w") as f:
            json.dump({
                "stats": stats,
                "trades": [t.__dict__ for t in result.trades],
            }, f, indent=2, default=str)
        print(f"\nFull results written to {args.out}")


if __name__ == "__main__":
    main()
