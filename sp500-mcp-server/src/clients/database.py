"""
Database client for SP500 MCP Server
Reads settings from sp500_settings table (configured via frontend)
"""
import os
import psycopg2
import psycopg2.extras
from typing import Optional

DATABASE_URL = os.getenv("DATABASE_URL", "")
USER_ID = os.getenv("USER_ID", "5f7b54c4-3bb5-487e-897e-e273112a914b")

# Cache settings in memory (refreshed every cycle)
_settings_cache: Optional[dict] = None


def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def execute(query: str, params: tuple = ()) -> list:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if cur.description:
                return cur.fetchall()
            conn.commit()
            return []


def execute_one(query: str, params: tuple = ()):
    rows = execute(query, params)
    return rows[0] if rows else None


def get_settings(force_refresh: bool = False) -> dict:
    """
    Get SP500 settings from database.
    Returns dict with all configuration values.
    Cached in memory, call with force_refresh=True to reload.
    """
    global _settings_cache
    if _settings_cache and not force_refresh:
        return _settings_cache

    row = execute_one(
        "SELECT * FROM sp500_settings WHERE user_id = %s",
        (USER_ID,)
    )

    if not row:
        # Return defaults if no settings exist
        _settings_cache = {
            "symbol": "US500Cash",
            "point_value": 1.0,
            "min_lot": 0.01,
            "max_lot": 5.0,
            "max_risk_per_trade_pct": 1.0,
            "max_daily_loss_pct": 5.0,
            "max_consecutive_losses": 5,
            "min_rr_ratio": 1.5,
            "max_open_positions": 5,
            "am_killzone_start": "13:30",
            "am_killzone_end": "15:30",
            "pm_killzone_start": "18:00",
            "pm_killzone_end": "20:00",
            "premarket_start": "12:00",
            "regular_session_start": "13:30",
            "regular_session_end": "20:00",
            "news_buffer_minutes": 15,
            "daily_target_pct": 1.0,
            "daily_target_points": 30.0,
            "min_structure_score": 2,
            "min_sweep_distance_points": 5.0,
            "kill_switch": False,
            "auto_trading_enabled": True,
        }
    else:
        _settings_cache = {
            "symbol": row["symbol"],
            "point_value": float(row["point_value"]),
            "min_lot": float(row["min_lot"]),
            "max_lot": float(row["max_lot"]),
            "max_risk_per_trade_pct": float(row["max_risk_per_trade_pct"]),
            "max_daily_loss_pct": float(row["max_daily_loss_pct"]),
            "max_consecutive_losses": int(row["max_consecutive_losses"]),
            "min_rr_ratio": float(row["min_rr_ratio"]),
            "max_open_positions": int(row["max_open_positions"]),
            "am_killzone_start": row["am_killzone_start"],
            "am_killzone_end": row["am_killzone_end"],
            "pm_killzone_start": row["pm_killzone_start"],
            "pm_killzone_end": row["pm_killzone_end"],
            "premarket_start": row["premarket_start"],
            "regular_session_start": row["regular_session_start"],
            "regular_session_end": row["regular_session_end"],
            "news_buffer_minutes": int(row["news_buffer_minutes"]),
            "daily_target_pct": float(row["daily_target_pct"]),
            "daily_target_points": float(row["daily_target_points"]),
            "min_structure_score": int(row["min_structure_score"]),
            "min_sweep_distance_points": float(row["min_sweep_distance_points"]),
            "kill_switch": bool(row["kill_switch"]),
            "auto_trading_enabled": bool(row["auto_trading_enabled"]),
        }

    return _settings_cache
