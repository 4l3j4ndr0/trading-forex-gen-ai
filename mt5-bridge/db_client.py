"""Database client for the bridge — reads broker configs."""

import json
import base64
import hashlib
import psycopg2
from psycopg2.extras import RealDictCursor

from config import Config


def _get_conn():
    """Get a database connection."""
    return psycopg2.connect(Config.DATABASE_URL)


def _decrypt_adonisjs(encrypted_value: str, app_key: str) -> str:
    """
    Decrypt a value encrypted by AdonisJS encryption service.
    AdonisJS uses aes-256-cbc with the APP_KEY.
    The encrypted value is a base64-encoded JSON: {iv, value}
    """
    try:
        # AdonisJS encryption format: base64(JSON({iv, value}))
        decoded = base64.b64decode(encrypted_value)
        data = json.loads(decoded)

        iv = base64.b64decode(data["iv"])
        value = base64.b64decode(data["value"])

        # Derive key from APP_KEY
        key = base64.b64decode(app_key)

        # AES-256-CBC decrypt
        from Crypto.Cipher import AES
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(value)

        # Remove PKCS7 padding
        pad_len = decrypted[-1]
        return decrypted[:-pad_len].decode("utf-8")
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}")


def get_user_broker_config(user_id: str) -> dict | None:
    """
    Get broker config for a user from the database.
    Returns decrypted credentials ready to use.
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

        # Decrypt password
        mt5_password = _decrypt_adonisjs(row["mt5_password_encrypted"], Config.APP_KEY)

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
