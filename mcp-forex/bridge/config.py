"""MT5 Bridge configuration."""

import os


class Config:
    # MT5 Connection
    MT5_LOGIN = int(os.getenv("MT5_LOGIN", "0"))
    MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
    MT5_SERVER = os.getenv("MT5_SERVER", "XMGlobal-MT5")
    MT5_PATH = os.getenv("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")

    # Bridge
    BRIDGE_PORT = int(os.getenv("BRIDGE_PORT", "5000"))
    BRIDGE_API_KEY = os.getenv("BRIDGE_API_KEY", "change-me-in-production")

    # Security
    ALLOWED_IPS = os.getenv("ALLOWED_IPS", "").split(",")  # Empty = allow all
