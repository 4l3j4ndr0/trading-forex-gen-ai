"""MT5 Bridge configuration."""

import os


class Config:
    # Bridge
    BRIDGE_PORT = int(os.getenv("BRIDGE_PORT", "5000"))
    BRIDGE_API_KEY = os.getenv("BRIDGE_API_KEY", "")

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "")

    # Encryption key (same APP_KEY as backend — for decrypting passwords)
    APP_KEY = os.getenv("APP_KEY", "")

    # MT5 Path
    MT5_PATH = os.getenv("MT5_PATH", r"C:\Program Files\XM Global MT5\terminal64.exe")

    # Security
    ALLOWED_IPS = os.getenv("ALLOWED_IPS", "").split(",")
