"""Register all MCP tools."""

from src.tools.analysis import register_analysis_tools
from src.tools.database import register_database_tools
from src.tools.smart import register_smart_tools
from src.tools.system import register_system_tools


def register_all_tools(mcp):
    """Register all tool groups."""
    register_analysis_tools(mcp)
    register_database_tools(mcp)
    register_smart_tools(mcp)
    register_system_tools(mcp)
    # register_trading_tools(mcp)    # Fase 2 (MT5 Bridge)
