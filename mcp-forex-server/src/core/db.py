"""PostgreSQL connection pool and query helpers."""

import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

DATABASE_URL = os.getenv("DATABASE_URL", "")

_pool: ThreadedConnectionPool | None = None


def get_pool() -> ThreadedConnectionPool:
    """Get or create the connection pool."""
    global _pool
    if _pool is None or _pool.closed:
        _pool = ThreadedConnectionPool(minconn=2, maxconn=10, dsn=DATABASE_URL)
    return _pool


@contextmanager
def get_conn():
    """Context manager for a pooled connection."""
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


@contextmanager
def get_cursor():
    """Context manager for a cursor with RealDictCursor."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur


def execute(query: str, params: tuple = None) -> list[dict]:
    """Execute a query and return all rows as dicts."""
    with get_cursor() as cur:
        cur.execute(query, params)
        if cur.description:
            return [dict(row) for row in cur.fetchall()]
        return []


def execute_one(query: str, params: tuple = None) -> dict | None:
    """Execute a query and return one row."""
    with get_cursor() as cur:
        cur.execute(query, params)
        if cur.description:
            row = cur.fetchone()
            return dict(row) if row else None
        return None


def execute_insert(query: str, params: tuple = None) -> dict | None:
    """Execute an INSERT ... RETURNING and return the row."""
    return execute_one(query, params)
