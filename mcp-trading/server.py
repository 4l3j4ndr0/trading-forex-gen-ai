"""
MCP Trading Server — Entry point.

Exposes crypto trading tools (Binance + TradingView) via MCP protocol.
Supports stdio (local) and streamable-http (remote) transports.

Binance credentials are sent by the client via headers:
    - X-Binance-Api-Key: <key>
    - X-Binance-Api-Secret: <secret>
    - X-Binance-Testnet: true/false

Usage:
    Local (stdio):   python server.py
    Remote (HTTP):   python server.py --http
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

from fastmcp import FastMCP
from src.tools import register_all_tools

# Create MCP server
mcp = FastMCP("Trading MCP")

# Register all tools
register_all_tools(mcp)


if __name__ == "__main__":
    transport = "streamable-http" if ("--http" in sys.argv or os.getenv("MCP_TRANSPORT") == "http") else "stdio"

    if transport == "streamable-http":
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8000"))
        mcp.run(transport=transport, host=host, port=port)
    else:
        mcp.run()
