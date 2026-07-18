"""
WhatsApp Notification Tool — Send trading alerts via WhatsApp
Uses the same WhatsApp API service as VitalID
"""
import json
import os
import httpx

WHATSAPP_API_KEY = os.getenv("WHATSAPP_API_KEY", "")
WHATSAPP_SERVICE_URL = os.getenv("WHATSAPP_SERVICE_URL", "https://whatsapp.vitalid.co")
WHATSAPP_NUMBER = os.getenv("WHATSAPP_NUMBER", "573146254435")


async def _send_whatsapp(message: str) -> dict:
    """Send a WhatsApp message via the API"""
    if not WHATSAPP_API_KEY:
        return {"error": "WHATSAPP_API_KEY not configured"}

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{WHATSAPP_SERVICE_URL}/send",
            headers={
                "Content-Type": "application/json",
                "x-api-key": WHATSAPP_API_KEY,
            },
            json={
                "number": WHATSAPP_NUMBER,
                "message": message,
            },
        )

    if response.status_code == 200:
        return {"status": "sent", "number": WHATSAPP_NUMBER}
    else:
        return {"error": f"HTTP {response.status_code}: {response.text}"}


def register_notification_tools(mcp):

    @mcp.tool()
    async def send_whatsapp_alert(alert_type: str, message: str) -> str:
        """
        Send a WhatsApp notification to the trader.
        Use this to inform about trade openings, closings, and daily/weekly reports.

        Args:
            alert_type: Type of alert. One of: TRADE_OPENED, TRADE_CLOSED, DAILY_REPORT, WEEKLY_REPORT, ALERT
            message: The message content. Use emojis and formatting (*bold*, _italic_) for readability.

        When to use:
        - TRADE_OPENED: Immediately after opening a new position
        - TRADE_CLOSED: Immediately after closing a position (include PnL)
        - DAILY_REPORT: At the last cycle of the trading session (end of day)
        - WEEKLY_REPORT: On Friday's last cycle (end of week summary)
        - ALERT: For critical events (margin warning, kill switch, etc.)
        """
        valid_types = ["TRADE_OPENED", "TRADE_CLOSED", "DAILY_REPORT", "WEEKLY_REPORT", "ALERT"]
        if alert_type not in valid_types:
            return json.dumps({"error": f"Invalid alert_type. Must be one of: {valid_types}"})

        prefix_map = {
            "TRADE_OPENED": "📈",
            "TRADE_CLOSED": "💰",
            "DAILY_REPORT": "📊",
            "WEEKLY_REPORT": "📋",
            "ALERT": "🚨",
        }

        formatted_message = f"{prefix_map[alert_type]} *AutoTrader AI — {alert_type.replace('_', ' ')}*\n\n{message}"

        result = await _send_whatsapp(formatted_message)
        return json.dumps(result)
