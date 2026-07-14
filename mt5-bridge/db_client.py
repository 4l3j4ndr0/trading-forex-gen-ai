"""Database client for the bridge — reads broker configs."""

import base64
import psycopg2
from psycopg2.extras import RealDictCursor

from config import Config


def _get_conn():
    """Get a database connection."""
    return psycopg2.connect(Config.DATABASE_URL)


def get_user_broker_config(user_id: str) -> dict | None:
    """
    Get broker config for a user from the database.
    Decodes base64 password.
    """
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """SELECT broker_name, mt5_login, mt5_password_encrypted, 
                          mt5_server, symbol_suffix, account_type, is_active
                   FROM broker_configs WHERE user_id = %s""",
                (user_id,)
            )
            row = cur.fetchone()

        if not row:
            return None

        if not row["is_active"]:
            return None

        # Decode base64 password
        mt5_password = base64.b64decode(row["mt5_password_encrypted"]).decode("utf-8")

        return {
            "broker_name": row["broker_name"],
            "mt5_login": row["mt5_login"],
            "mt5_password": mt5_password,
            "mt5_server": row["mt5_server"],
            "symbol_suffix": row["symbol_suffix"],
            "account_type": row["account_type"],
        }
    finally:
        conn.close()
