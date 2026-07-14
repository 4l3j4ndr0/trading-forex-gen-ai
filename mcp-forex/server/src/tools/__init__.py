"""Register all MCP tools."""

from src.tools.analysis import register_analysis_tools


def register_all_tools(mcp):
    """Register all tool groups."""
    register_analysis_tools(mcp)
    # register_trading_tools(mcp)    # Fase 2
    # register_smart_tools(mcp)      # Fase 1 cont.
    # register_database_tools(mcp)   # Fase 1 cont.
    # register_system_tools(mcp)     # Fase 1 cont.
