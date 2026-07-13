"""System tools — safety rules, configuration, and health."""

import json
from datetime import datetime, timezone

from src.core.safety import SafetyGuard


def register_system_tools(mcp):
    """Register system/config tools."""

    @mcp.tool()
    def get_safety_rules() -> str:
        """
        Get active safety rules and trading limits.

        Returns:
            All hard limits: max positions, lot size, daily loss, kill switch, etc.
        """
        return json.dumps(SafetyGuard.get_rules_summary())

    @mcp.tool()
    def health_check() -> str:
        """
        Server health check — confirms the MCP server is running.

        Returns:
            Status, server time, and version.
        """
        return json.dumps({
            "status": "healthy",
            "server": "MCP Trading Server",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
