"""
Historical candle fetching for backtesting.

Pages across the bridge's /candles_range endpoint (capped at 90 days per
request server-side) and caches results to disk as JSON so re-running a
backtest doesn't re-hit the bridge/broker every time.
"""

import json
import os
from datetime import datetime, timezone

from src.clients.mt5_bridge import bridge

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
WINDOW_SECONDS = 85 * 86400  # stay under the bridge's 90-day cap with margin


def _cache_path(symbol: str, timeframe: str, date_from: int, date_to: int) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{symbol}_{timeframe}_{date_from}_{date_to}.json")


def fetch_range(symbol: str, timeframe: str, date_from: int, date_to: int, use_cache: bool = True) -> list[dict]:
    """
    Fetch candles for [date_from, date_to) (unix seconds, UTC), paging across
    the bridge's per-request window limit. Returns candles sorted by time,
    deduplicated. Raises RuntimeError if any page fails to fetch — a partial,
    silently-incomplete history would corrupt the backtest (e.g. fake gaps
    that look like missed SL/TP touches), so we fail loud instead.
    """
    cache_file = _cache_path(symbol, timeframe, date_from, date_to)
    if use_cache and os.path.exists(cache_file):
        with open(cache_file) as f:
            return json.load(f)

    all_candles: dict[int, dict] = {}
    cursor = date_from
    while cursor < date_to:
        window_end = min(cursor + WINDOW_SECONDS, date_to)
        result = bridge.get_candles_range(symbol, timeframe, cursor, window_end)
        if isinstance(result, dict) and "error" in result:
            raise RuntimeError(
                f"Failed to fetch {symbol} {timeframe} [{cursor}, {window_end}): {result['error']}"
            )
        candles = result.get("candles", []) if isinstance(result, dict) else result
        for c in candles:
            all_candles[c["time"]] = c
        cursor = window_end

    ordered = [all_candles[t] for t in sorted(all_candles)]
    if use_cache:
        with open(cache_file, "w") as f:
            json.dump(ordered, f)
    return ordered


def fetch_all_timeframes(symbol: str, date_from: int, date_to: int, use_cache: bool = True) -> dict[str, list[dict]]:
    """Fetch D1, H4, H1, M15 for one pair over the given range."""
    # D1/H4/H1 need extra lookback before date_from so indicators (EMA200, ADX14,
    # swing detection) are warmed up by the time the backtest window starts.
    warmup = {"D1": 250 * 86400, "H4": 60 * 86400, "H1": 15 * 86400, "M15": 4 * 86400}
    return {
        tf: fetch_range(symbol, tf, date_from - warmup[tf], date_to, use_cache=use_cache)
        for tf in ("D1", "H4", "H1", "M15")
    }


def parse_date(s: str) -> int:
    """Parse 'YYYY-MM-DD' (UTC) into unix seconds."""
    return int(datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
