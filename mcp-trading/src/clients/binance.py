"""Binance Futures API client — credentials from MCP request context."""

from binance.client import Client
from binance.exceptions import BinanceAPIException

from src.core.config import config


def get_binance_client(api_key: str = None, api_secret: str = None, testnet: bool = None) -> Client:
    """Create a Binance client with the given credentials."""
    key = api_key or config.binance_api_key
    secret = api_secret or config.binance_api_secret
    is_testnet = testnet if testnet is not None else config.binance_testnet

    client = Client(key, secret, testnet=is_testnet)
    if is_testnet:
        client.API_URL = "https://testnet.binancefuture.com/fapi"
    return client


class BinanceClient:
    """Wrapper around python-binance for Futures trading.
    
    Uses credentials from .env as fallback, but tools can pass
    per-request credentials from the MCP client headers.
    """

    def _client(self, api_key: str = None, api_secret: str = None, testnet: bool = None) -> Client:
        return get_binance_client(api_key, api_secret, testnet)

    def get_balance(self, api_key: str = None, api_secret: str = None, testnet: bool = None) -> dict:
        try:
            account = self._client(api_key, api_secret, testnet).futures_account()
            return {
                "total_balance": float(account["totalWalletBalance"]),
                "available_balance": float(account["availableBalance"]),
                "unrealized_pnl": float(account["totalUnrealizedProfit"]),
                "total_margin_balance": float(account["totalMarginBalance"]),
            }
        except BinanceAPIException as e:
            return {"error": f"Binance API error: {e.message}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def get_price(self, symbol: str, api_key: str = None, api_secret: str = None, testnet: bool = None) -> float:
        ticker = self._client(api_key, api_secret, testnet).futures_symbol_ticker(symbol=symbol)
        return float(ticker["price"])

    def open_market_order(self, symbol: str, side: str, quantity: float, api_key: str = None, api_secret: str = None, testnet: bool = None) -> dict:
        try:
            order = self._client(api_key, api_secret, testnet).futures_create_order(
                symbol=symbol,
                side=side.upper(),
                type="MARKET",
                quantity=quantity,
            )
            return {
                "order_id": str(order["orderId"]),
                "symbol": order["symbol"],
                "side": order["side"],
                "quantity": float(order["origQty"]),
                "avg_price": float(order.get("avgPrice", 0)),
                "status": order["status"],
            }
        except BinanceAPIException as e:
            return {"error": f"Binance API error: {e.message}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def close_market_order(self, symbol: str, side: str, quantity: float, api_key: str = None, api_secret: str = None, testnet: bool = None) -> dict:
        try:
            order = self._client(api_key, api_secret, testnet).futures_create_order(
                symbol=symbol,
                side=side.upper(),
                type="MARKET",
                quantity=quantity,
                reduceOnly=True,
            )
            return {
                "order_id": str(order["orderId"]),
                "symbol": order["symbol"],
                "side": order["side"],
                "quantity": float(order["origQty"]),
                "avg_price": float(order.get("avgPrice", 0)),
                "status": order["status"],
            }
        except BinanceAPIException as e:
            return {"error": f"Binance API error: {e.message}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def get_symbol_info(self, symbol: str, api_key: str = None, api_secret: str = None, testnet: bool = None) -> dict:
        try:
            info = self._client(api_key, api_secret, testnet).futures_exchange_info()
            for s in info["symbols"]:
                if s["symbol"] == symbol:
                    filters = {f["filterType"]: f for f in s["filters"]}
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
        except BinanceAPIException as e:
            return {"error": f"Binance API error: {e.message}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}


# Singleton
binance = BinanceClient()
