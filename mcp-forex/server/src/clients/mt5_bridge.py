"""HTTP client to communicate with the MT5 Bridge (VPS Windows)."""

import os
import requests

MT5_BRIDGE_URL = os.getenv("MT5_BRIDGE_URL", "http://mt5-bridge.awslearn.cloud:5000")
MT5_BRIDGE_API_KEY = os.getenv("MT5_BRIDGE_API_KEY", "")


def _headers():
    return {"X-Bridge-Api-Key": MT5_BRIDGE_API_KEY, "Content-Type": "application/json"}


def _get(endpoint: str, params: dict = None) -> dict:
    """GET request to the bridge."""
    try:
        resp = requests.get(f"{MT5_BRIDGE_URL}{endpoint}", headers=_headers(), params=params, timeout=10)
        return resp.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Bridge connection failed: {str(e)}"}


def _post(endpoint: str, data: dict) -> dict:
    """POST request to the bridge."""
    try:
        resp = requests.post(f"{MT5_BRIDGE_URL}{endpoint}", headers=_headers(), json=data, timeout=10)
        return resp.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Bridge connection failed: {str(e)}"}


class MT5BridgeClient:
    """Client for the MT5 Bridge REST API."""

    def health(self) -> dict:
        return _get("/health")

    def get_account(self) -> dict:
        return _get("/account")

    def get_positions(self) -> list:
        result = _get("/positions")
        return result if isinstance(result, list) else [result]

    def get_symbol_info(self, symbol: str) -> dict:
        return _get(f"/symbol/{symbol}")

    def get_tick(self, symbol: str) -> dict:
        return _get(f"/tick/{symbol}")

    def get_spread(self, symbol: str) -> dict:
        return _get(f"/indicator/spread/{symbol}")

    def get_candles(self, symbol: str, timeframe: str = "H1", count: int = 100) -> dict:
        return _get(f"/candles/{symbol}", {"timeframe": timeframe, "count": count})

    def get_atr(self, symbol: str, timeframe: str = "H1", period: int = 14) -> dict:
        return _get(f"/indicator/atr/{symbol}", {"timeframe": timeframe, "period": period})

    def open_order(self, symbol: str, side: str, lot: float, sl: float, tp: float, comment: str = "") -> dict:
        return _post("/order/open", {
            "symbol": symbol,
            "side": side,
            "lot": lot,
            "sl": sl,
            "tp": tp,
            "comment": comment,
        })

    def close_order(self, ticket: int) -> dict:
        return _post("/order/close", {"ticket": ticket})

    def modify_order(self, ticket: int, sl: float = None, tp: float = None) -> dict:
        data = {"ticket": ticket}
        if sl is not None:
            data["sl"] = sl
        if tp is not None:
            data["tp"] = tp
        return _post("/order/modify", data)


# Singleton
bridge = MT5BridgeClient()
