"""Database layer — SQLite with proper schema and operations."""

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.core.config import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id              TEXT PRIMARY KEY,
    symbol          TEXT NOT NULL,
    side            TEXT NOT NULL CHECK(side IN ('BUY', 'SELL')),
    lot_size        REAL NOT NULL,
    entry_price     REAL NOT NULL,
    exit_price      REAL,
    quantity        REAL NOT NULL,
    opened_at       TEXT NOT NULL,
    close_by        TEXT NOT NULL,
    closed_at       TEXT,
    pnl_usd         REAL,
    pnl_pips        REAL,
    status          TEXT DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'CLOSED', 'EXPIRED')),
    decision_score  REAL,
    decision_reason TEXT,
    confidence      INTEGER,
    binance_order_id TEXT,
    binance_close_order_id TEXT,
    session_active  TEXT,
    d1_trend_score  INTEGER,
    h1_rsi          REAL,
    h1_ema20        REAL,
    h1_ema50        REAL,
    h1_adx          REAL,
    h1_bb_width     REAL
);

CREATE TABLE IF NOT EXISTS hourly_logs (
    id              TEXT PRIMARY KEY,
    timestamp       TEXT NOT NULL,
    balance_usd     REAL,
    equity_usd      REAL,
    open_positions  INTEGER,
    trades_opened   INTEGER DEFAULT 0,
    trades_closed   INTEGER DEFAULT 0,
    trades_skipped  INTEGER DEFAULT 0,
    pnl_this_hour   REAL,
    cumulative_pnl  REAL,
    symbols_analyzed TEXT,
    market_context  TEXT
);

CREATE TABLE IF NOT EXISTS performance_daily (
    date            TEXT PRIMARY KEY,
    total_trades    INTEGER,
    winning_trades  INTEGER,
    losing_trades   INTEGER,
    skipped_hours   INTEGER,
    win_rate        REAL,
    gross_pnl       REAL,
    net_pnl         REAL,
    max_drawdown    REAL,
    best_trade_pnl  REAL,
    worst_trade_pnl REAL
);

CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_opened ON trades(opened_at);
CREATE INDEX IF NOT EXISTS idx_hourly_timestamp ON hourly_logs(timestamp);
"""


class Database:
    """Thread-safe SQLite database operations."""

    def __init__(self, db_path: str = None):
        self._db_path = db_path or config.db_path
        self._ensure_dir()
        self._init_schema()

    def _ensure_dir(self):
        db_dir = os.path.dirname(self._db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self):
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    # ─── TRADES ─────────────────────────────────────────────────

    def insert_trade(
        self,
        symbol: str,
        side: str,
        lot_size: float,
        entry_price: float,
        quantity: float,
        decision_score: Optional[float] = None,
        decision_reason: Optional[str] = None,
        confidence: Optional[int] = None,
        binance_order_id: Optional[str] = None,
        session_active: Optional[str] = None,
        indicators: Optional[dict] = None,
    ) -> str:
        trade_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        close_by = now + timedelta(hours=1)
        ind = indicators or {}

        with self._conn() as conn:
            conn.execute(
                """INSERT INTO trades (
                    id, symbol, side, lot_size, entry_price, quantity,
                    opened_at, close_by, status,
                    decision_score, decision_reason, confidence,
                    binance_order_id, session_active,
                    d1_trend_score, h1_rsi, h1_ema20, h1_ema50, h1_adx, h1_bb_width
                ) VALUES (?,?,?,?,?,?,?,?,'OPEN',?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    trade_id, symbol, side, lot_size, entry_price, quantity,
                    now.isoformat(), close_by.isoformat(),
                    decision_score, decision_reason, confidence,
                    binance_order_id, session_active,
                    ind.get("d1_trend_score"), ind.get("h1_rsi"),
                    ind.get("h1_ema20"), ind.get("h1_ema50"),
                    ind.get("h1_adx"), ind.get("h1_bb_width"),
                ),
            )
        return trade_id

    def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        pnl_usd: float,
        pnl_pips: Optional[float] = None,
        binance_close_order_id: Optional[str] = None,
    ):
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                """UPDATE trades SET
                    exit_price=?, pnl_usd=?, pnl_pips=?,
                    closed_at=?, status='CLOSED', binance_close_order_id=?
                WHERE id=?""",
                (exit_price, pnl_usd, pnl_pips, now, binance_close_order_id, trade_id),
            )

    def get_open_trades(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM trades WHERE status='OPEN' ORDER BY opened_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_trade_history(self, period: str = "today", symbol: Optional[str] = None) -> list[dict]:
        now = datetime.now(timezone.utc)
        since_map = {
            "today": now.replace(hour=0, minute=0, second=0, microsecond=0),
            "yesterday": (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
            "7d": now - timedelta(days=7),
            "30d": now - timedelta(days=30),
        }
        since = since_map.get(period, now - timedelta(days=1))

        query = "SELECT * FROM trades WHERE opened_at >= ? AND status='CLOSED'"
        params: list = [since.isoformat()]
        if symbol:
            query += " AND symbol=?"
            params.append(symbol)
        query += " ORDER BY closed_at DESC"

        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_daily_pnl(self) -> float:
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(pnl_usd),0) as total FROM trades WHERE closed_at>=? AND status='CLOSED'",
                (today.isoformat(),),
            ).fetchone()
        return row["total"] if row else 0.0

    def get_consecutive_losses(self) -> int:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT pnl_usd FROM trades WHERE status='CLOSED' ORDER BY closed_at DESC LIMIT 20"
            ).fetchall()
        count = 0
        for r in rows:
            if r["pnl_usd"] is not None and r["pnl_usd"] < 0:
                count += 1
            else:
                break
        return count

    # ─── HOURLY LOGS ────────────────────────────────────────────

    def insert_hourly_log(self, **kwargs):
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO hourly_logs (
                    id, timestamp, balance_usd, equity_usd, open_positions,
                    trades_opened, trades_closed, trades_skipped,
                    pnl_this_hour, cumulative_pnl, symbols_analyzed, market_context
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(uuid.uuid4()),
                    datetime.now(timezone.utc).isoformat(),
                    kwargs.get("balance_usd"),
                    kwargs.get("equity_usd"),
                    kwargs.get("open_positions", 0),
                    kwargs.get("trades_opened", 0),
                    kwargs.get("trades_closed", 0),
                    kwargs.get("trades_skipped", 0),
                    kwargs.get("pnl_this_hour"),
                    kwargs.get("cumulative_pnl"),
                    kwargs.get("symbols_analyzed"),
                    kwargs.get("market_context"),
                ),
            )

    # ─── PERFORMANCE ────────────────────────────────────────────

    def get_performance_stats(self) -> dict:
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

        with self._conn() as conn:
            today_row = conn.execute(
                """SELECT COUNT(*) as total,
                   SUM(CASE WHEN pnl_usd>0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN pnl_usd<=0 THEN 1 ELSE 0 END) as losses,
                   COALESCE(SUM(pnl_usd),0) as pnl
                FROM trades WHERE closed_at>=? AND status='CLOSED'""",
                (today,),
            ).fetchone()

            week_row = conn.execute(
                """SELECT COUNT(*) as total,
                   SUM(CASE WHEN pnl_usd>0 THEN 1 ELSE 0 END) as wins,
                   COALESCE(SUM(pnl_usd),0) as pnl
                FROM trades WHERE closed_at>=? AND status='CLOSED'""",
                (week_ago,),
            ).fetchone()

            all_row = conn.execute(
                """SELECT COUNT(*) as total,
                   SUM(CASE WHEN pnl_usd>0 THEN 1 ELSE 0 END) as wins,
                   COALESCE(SUM(pnl_usd),0) as pnl,
                   MIN(pnl_usd) as worst, MAX(pnl_usd) as best
                FROM trades WHERE status='CLOSED'"""
            ).fetchone()

        total_all = all_row["total"] or 0
        wins_all = all_row["wins"] or 0

        return {
            "today": {
                "trades": today_row["total"] or 0,
                "wins": today_row["wins"] or 0,
                "losses": today_row["losses"] or 0,
                "pnl_usd": today_row["pnl"] or 0.0,
                "win_rate": round((today_row["wins"] or 0) / max(today_row["total"] or 1, 1) * 100, 1),
            },
            "this_week": {
                "trades": week_row["total"] or 0,
                "wins": week_row["wins"] or 0,
                "pnl_usd": week_row["pnl"] or 0.0,
            },
            "all_time": {
                "trades": total_all,
                "wins": wins_all,
                "win_rate": round(wins_all / max(total_all, 1) * 100, 1),
                "pnl_usd": all_row["pnl"] or 0.0,
                "best_trade": all_row["best"],
                "worst_trade": all_row["worst"],
            },
            "consecutive_losses": self.get_consecutive_losses(),
        }


# Singleton
db = Database()
