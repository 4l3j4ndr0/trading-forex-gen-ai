"""Authentication and request context middleware."""

import os
from dataclasses import dataclass
from typing import Optional

MCP_API_KEY = os.getenv("MCP_API_KEY", "")


@dataclass
class RequestContext:
    """Per-request context with Binance credentials."""
    binance_api_key: str = ""
    binance_api_secret: str = ""
    binance_testnet: bool = True


def validate_api_key(key: Optional[str]) -> bool:
    """Validate the MCP API key. Returns False if no key configured (open mode)."""
    if not MCP_API_KEY:
        return True  # No key configured = open access
    return key == MCP_API_KEY
