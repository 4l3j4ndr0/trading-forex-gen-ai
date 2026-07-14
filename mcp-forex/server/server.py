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
from src.core.db import run_migrations

# Create MCP server
mcp = FastMCP("Forex Trading MCP")

# Register all tools
register_all_tools(mcp)


if __name__ == "__main__":
    # Run migrations on startup
    try:
        run_migrations()
        print("✅ Database migrations OK")
    except Exception as e:
        print(f"⚠️  Database not available: {e} (analysis tools still work)")

    transport = "streamable-http" if ("--http" in sys.argv or os.getenv("MCP_TRANSPORT") == "http") else "stdio"

    if transport == "streamable-http":
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8000"))

        app = mcp.http_app(transport="streamable-http")

        import uvicorn
        print(f"🚀 Forex MCP Server on http://{host}:{port}/mcp")
        print(f"📊 Tools: analysis, smart, database, trading, system")
        uvicorn.run(app, host=host, port=port)
    else:
        mcp.run()
