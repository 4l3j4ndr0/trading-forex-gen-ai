"""
MCP Trading Server — Entry point.

Security model:
    Binance credentials are sent via HTTPS headers by the MCP client.
    Headers: X-Binance-Api-Key, X-Binance-Api-Secret, X-Binance-Testnet

Usage:
    Local (stdio):   python server.py
    Remote (HTTP):   python server.py --http
"""

import os
import sys
import contextvars

from dotenv import load_dotenv

load_dotenv()

from fastmcp import FastMCP
from src.tools import register_all_tools

# Context vars to pass headers to tools (thread-safe)
binance_api_key_var: contextvars.ContextVar[str] = contextvars.ContextVar("binance_api_key", default="")
binance_api_secret_var: contextvars.ContextVar[str] = contextvars.ContextVar("binance_api_secret", default="")
binance_testnet_var: contextvars.ContextVar[bool] = contextvars.ContextVar("binance_testnet", default=True)

# Create MCP server
mcp = FastMCP("Trading MCP")

# Register all tools
register_all_tools(mcp)


if __name__ == "__main__":
    transport = "streamable-http" if ("--http" in sys.argv or os.getenv("MCP_TRANSPORT") == "http") else "stdio"

    if transport == "streamable-http":
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8000"))

        # Wrap with middleware to extract headers
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import Request

        class BinanceHeadersMiddleware(BaseHTTPMiddleware):
            """Extracts X-Binance-* headers and stores in context vars."""

            async def dispatch(self, request: Request, call_next):
                key = request.headers.get("x-binance-api-key", "")
                secret = request.headers.get("x-binance-api-secret", "")
                testnet = request.headers.get("x-binance-testnet", "true").lower() == "true"

                binance_api_key_var.set(key)
                binance_api_secret_var.set(secret)
                binance_testnet_var.set(testnet)

                return await call_next(request)

        app = mcp.http_app(transport="streamable-http")
        app.add_middleware(BinanceHeadersMiddleware)

        import uvicorn
        print(f"🚀 MCP Trading Server on https://{host}:{port}/mcp")
        print(f"🔒 Binance credentials via X-Binance-* headers")
        uvicorn.run(app, host=host, port=port)
    else:
        mcp.run()
