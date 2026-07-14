"""Application configuration — loaded from environment variables."""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    """Immutable application config."""

    # Binance
    binance_api_key: str = field(default_factory=lambda: os.getenv("BINANCE_API_KEY", ""))
    binance_api_secret: str = field(default_factory=lambda: os.getenv("BINANCE_API_SECRET", ""))
    binance_testnet: bool = field(default_factory=lambda: os.getenv("BINANCE_TESTNET", "true").lower() == "true")

    # Database
    db_path: str = field(default_factory=lambda: os.getenv("DB_PATH", "data/trading.db"))

    # MCP Server
    mcp_host: str = field(default_factory=lambda: os.getenv("MCP_HOST", "0.0.0.0"))
    mcp_port: int = field(default_factory=lambda: int(os.getenv("MCP_PORT", "8000")))


@dataclass(frozen=True)
class SafetyRules:
    """Hard safety limits — enforced at tool level, cannot be overridden by any client."""

    max_open_positions: int = field(default_factory=lambda: int(os.getenv("MAX_OPEN_POSITIONS", "3")))
    max_lot_size: float = field(default_factory=lambda: float(os.getenv("MAX_LOT_SIZE", "500.0")))
    max_daily_loss_usd: float = field(default_factory=lambda: float(os.getenv("MAX_DAILY_LOSS_USD", "50.0")))
    max_consecutive_losses: int = field(default_factory=lambda: int(os.getenv("MAX_CONSECUTIVE_LOSSES", "5")))
    min_balance_usd: float = field(default_factory=lambda: float(os.getenv("MIN_BALANCE_USD", "100.0")))
    allowed_symbols: list = field(default_factory=lambda: os.getenv("ALLOWED_SYMBOLS", "BTCUSDT,ETHUSDT").split(","))
    kill_switch: bool = field(default_factory=lambda: os.getenv("KILL_SWITCH", "false").lower() == "true")


# Singletons
config = Config()
safety = SafetyRules()
