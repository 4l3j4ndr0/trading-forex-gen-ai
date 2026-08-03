"""
Synchronous MT5 Bridge client — used only by the backtest engine.

The live tools use an async httpx.AsyncClient (src/clients/mt5_bridge.py)
because FastMCP tool handlers are async. The backtest's walk-forward loop
is a plain synchronous script (same reasoning as the forex backtest, which
also needed a sync client separate from its async live-tool client), so
this exposes just what the backtest needs: get_candles_range().
"""
import os
import httpx

BRIDGE_URL = os.getenv("MT5_BRIDGE_URL", "http://mt5-bridge.awslearn.cloud:5000")
API_KEY = os.getenv("MT5_BRIDGE_API_KEY", "")
SYMBOL = os.getenv("SYMBOL", "US500Cash")
USER_ID = os.getenv("USER_ID", "5f7b54c4-3bb5-487e-897e-e273112a914b")

HEADERS = {"X-Bridge-Api-Key": API_KEY, "X-User-Id": USER_ID}
TIMEOUT = 30.0


def get_candles_range(symbol: str, timeframe: str, date_from: int, date_to: int) -> dict:
    """Candles for an explicit UTC unix-seconds range — for backtesting."""
    with httpx.Client(timeout=TIMEOUT) as client:
        r = client.get(
            f"{BRIDGE_URL}/candles_range/{symbol}",
            params={"timeframe": timeframe, "from": date_from, "to": date_to},
            headers=HEADERS,
        )
        if r.status_code >= 400:
            try:
                return r.json()
            except Exception:
                return {"error": f"HTTP {r.status_code}: {r.text[:300]}"}
        return r.json()
