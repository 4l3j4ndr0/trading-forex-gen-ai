"""MCP Tools — organized by domain."""

from src.tools.analysis import register_analysis_tools
from src.tools.trading import register_trading_tools
from src.tools.portfolio import register_portfolio_tools
from src.tools.system import register_system_tools


def register_all_tools(mcp):
    """Register all tools on the MCP server."""
    register_analysis_tools(mcp)
    register_trading_tools(mcp)
    register_portfolio_tools(mcp)
    register_system_tools(mcp)
