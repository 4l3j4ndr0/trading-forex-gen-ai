"""Binance Futures API client — direct HTTP, no SDK, no geo-blocking on init."""

import hashlib
import hmac
import time
import urllib.parse

import requests

from src.core.config import config

# Endpoints
FUTURES_TESTNET = "https://testnet.binancefuture.com"
FUTURES_PROD = "https://fapi.binance.com"


def _get_credentials():
    """Get Binance credentials from context vars (HTTP mode) or env (stdio mode)."""
    try:
        from server import binance_api_key_var, binance_api_secret_var, binance_testnet_var
        key = binance_api_key_var.get() or config.binance_api_key
        secret = binance_api_secret_var.get() or config.binance_api_secret
        testnet = binance_testnet_var.get()
    except (ImportError, LookupError):
        key = config.binance_api_key
        secret = config.binance_api_secret
        testnet = config.binance_testnet

    return key, secret, testnet


def _base_url(testnet: bool) -> str:
    return FUTURES_TESTNET if testnet else FUTURES_PROD


def _sign(query_string: str, secret: str) -> str:
    return hmac.new(secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()


def _public_request(endpoint: str, params: dict = None) -> dict:
    """Unsigned GET request."""
    _, _, testnet = _get_credentials()
    url = f"{_base_url(testnet)}{endpoint}"
    try:
        resp = requests.get(url, params=params or {}, timeout=15)
        data = resp.json()
        if resp.status_code != 200:
            return {"error": f"Binance ({resp.status_code}): {data.get('msg', resp.text)}"}
        return data
    except Exception as e:
        return {"error": f"Connection error: {str(e)}"}


def _signed_request(method: str, endpoint: str, params: dict = None) -> dict:
    """Signed request (requires API key + secret)."""
    key, secret, testnet = _get_credentials()

    if not key or not secret:
        return {"error": "Missing Binance credentials. Configure X-Binance-Api-Key and X-Binance-Api-Secret headers."}

    url = f"{_base_url(testnet)}{endpoint}"
    params = params or {}
    params["timestamp"] = int(time.time() * 1000)
    params["recvWindow"] = 5000

    query_string = urllib.parse.urlencode(params)
    signature = hmac.new(secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    params["signature"] = signature

    headers = {"X-MBX-APIKEY": key}

    try:
        if method == "GET":
            resp = requests.get(url, params=params, headers=headers, timeout=15)
        else:
            resp = requests.post(url, params=params, headers=headers, timeout=15)

        data = resp.json()
        if resp.status_code != 200:
            return {"error": f"Binance ({resp.status_code}): {data.get('msg', resp.text)}"}
        return data
    except Exception as e:
        return {"error": f"Connection error: {str(e)}"}


class BinanceClient:
    """Binance Futures — direct HTTP requests. No SDK init, no geo-blocking."""

    def get_balance(self) -> dict:
        result = _signed_request("GET", "/fapi/v2/account")
        if "error" in result:
            return result
        return {
            "total_balance": float(result.get("totalWalletBalance", 0)),
            "available_balance": float(result.get("availableBalance", 0)),
            "unrealized_pnl": float(result.get("totalUnrealizedProfit", 0)),
            "total_margin_balance": float(result.get("totalMarginBalance", 0)),
        }

    def get_price(self, symbol: str) -> float:
        result = _public_request("/fapi/v1/ticker/price", {"symbol": symbol})
        if isinstance(result, dict) and "error" in result:
            raise ValueError(result["error"])
        return float(result.get("price", 0))

    def open_market_order(self, symbol: str, side: str, quantity: float) -> dict:
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": "MARKET",
            "quantity": quantity,
        }
        result = _signed_request("POST", "/fapi/v1/order", params)
        if "error" in result:
            return result
        return {
            "order_id": str(result.get("orderId", "")),
            "symbol": result.get("symbol", symbol),
            "side": result.get("side", side),
            "quantity": float(result.get("origQty", quantity)),
            "avg_price": float(result.get("avgPrice", 0)),
            "status": result.get("status", "UNKNOWN"),
        }

    def close_market_order(self, symbol: str, side: str, quantity: float) -> dict:
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": "MARKET",
            "quantity": quantity,
            "reduceOnly": "true",
        }
        result = _signed_request("POST", "/fapi/v1/order", params)
        if "error" in result:
            return result
        return {
            "order_id": str(result.get("orderId", "")),
            "symbol": result.get("symbol", symbol),
            "side": result.get("side", side),
            "quantity": float(result.get("origQty", quantity)),
            "avg_price": float(result.get("avgPrice", 0)),
            "status": result.get("status", "UNKNOWN"),
        }

    def get_symbol_info(self, symbol: str) -> dict:
        result = _public_request("/fapi/v1/exchangeInfo")
        if "error" in result:
            return result
        for s in result.get("symbols", []):
            if s["symbol"] == symbol:
                filters = {f["filterType"]: f for f in s.get("filters", [])}
                lot_filter = filters.get("LOT_SIZE", {})
                return {
                    "symbol": symbol,
                    "min_qty": float(lot_filter.get("minQty", 0)),
                    "max_qty": float(lot_filter.get("maxQty", 0)),
                    "step_size": float(lot_filter.get("stepSize", 0)),
                    "price_precision": s.get("pricePrecision", 2),
                    "quantity_precision": s.get("quantityPrecision", 3),
                }
        return {"error": f"Symbol {symbol} not found"}

    def get_open_positions(self) -> list:
        result = _signed_request("GET", "/fapi/v2/positionRisk")
        if isinstance(result, dict) and "error" in result:
            return [result]
        positions = []
        for p in result:
            amt = float(p.get("positionAmt", 0))
            if amt != 0:
                positions.append({
                    "symbol": p["symbol"],
                    "side": "BUY" if amt > 0 else "SELL",
                    "quantity": abs(amt),
                    "entry_price": float(p.get("entryPrice", 0)),
                    "mark_price": float(p.get("markPrice", 0)),
                    "unrealized_pnl": float(p.get("unRealizedProfit", 0)),
                    "leverage": int(p.get("leverage", 1)),
                })
        return positions


# Singleton
binance = BinanceClient()
