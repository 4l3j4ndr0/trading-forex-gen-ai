"""PostgreSQL connection pool and query helpers."""

import os
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://forex_user:forex_pass@localhost:5433/forex_trading")

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


def run_migrations():
    """Run all migration files in order."""
    migrations_dir = os.path.join(os.path.dirname(__file__), "..", "..", "migrations")
    if not os.path.exists(migrations_dir):
        return

    with get_conn() as conn:
        with conn.cursor() as cur:
            # Create migrations tracking table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS _migrations (
                    filename VARCHAR(200) PRIMARY KEY,
                    applied_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            # Get already applied
            cur.execute("SELECT filename FROM _migrations ORDER BY filename")
            applied = {row[0] for row in cur.fetchall()}

            # Apply new ones
            files = sorted(f for f in os.listdir(migrations_dir) if f.endswith(".sql"))
            for f in files:
                if f not in applied:
                    path = os.path.join(migrations_dir, f)
                    with open(path) as sql_file:
                        cur.execute(sql_file.read())
                    cur.execute("INSERT INTO _migrations (filename) VALUES (%s)", (f,))
                    print(f"  ✅ Migration: {f}")

        conn.commit()
