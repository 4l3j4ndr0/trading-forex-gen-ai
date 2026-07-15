"""
MCP Forex Trading Server — Entry point.

Usage:
    Local (stdio):   python server.py
    Remote (HTTP):   python server.py --http
    Docker:          MCP_TRANSPORT=http python server.py
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

from fastmcp import FastMCP
from src.tools import register_all_tools

# Create MCP server
mcp = FastMCP("Forex Trading MCP")

# Register all tools
register_all_tools(mcp)


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "streamable-http")
    if "--http" in sys.argv:
        transport = "streamable-http"
    elif "--sse" in sys.argv:
        transport = "sse"

    if transport in ("streamable-http", "sse"):
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8000"))

        app = mcp.http_app(transport=transport)

        import uvicorn
        print(f"🚀 Forex MCP Server on http://{host}:{port}")
        print(f"📡 Transport: {transport}")
        print(f"📊 Tools: analysis, smart, database, trading, system, market_data, news")
        uvicorn.run(app, host=host, port=port)
    else:
        mcp.run()
