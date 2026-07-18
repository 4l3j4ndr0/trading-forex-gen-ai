"""
SP500 MCP Server — Dedicated AI Trading Tools for S&P 500 Index
Designed for Smart Money Concepts on US500Cash (XM Broker)
Transport: SSE
"""
import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP(
    "SP500 Trading MCP Server",
    version="1.0.0",
    description="AI-powered S&P 500 index trading tools — SMC + Killzone strategy"
)

# Register all tools
from src.tools.session import register_session_tools
from src.tools.liquidity import register_liquidity_tools
from src.tools.structure import register_structure_tools
from src.tools.risk import register_risk_tools
from src.tools.news import register_news_tools
from src.tools.trading import register_trading_tools
from src.tools.database import register_database_tools
from src.tools.notifications import register_notification_tools

register_session_tools(mcp)
register_liquidity_tools(mcp)
register_structure_tools(mcp)
register_risk_tools(mcp)
register_news_tools(mcp)
register_trading_tools(mcp)
register_database_tools(mcp)
register_notification_tools(mcp)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    host = os.getenv("HOST", "0.0.0.0")

    app = mcp.sse_app()

    import uvicorn
    print(f"🚀 SP500 MCP Server on http://{host}:{port}")
    print(f"📡 Transport: SSE")
    print(f"📊 Tools: session, liquidity, structure, risk, news, trading, database")
    uvicorn.run(app, host=host, port=port)
