"""Binance Futures API client — lazy initialization to avoid startup failures."""

from binance.client import Client
from binance.exceptions import BinanceAPIException

from src.core.config import config


class BinanceClient:
    """Wrapper around python-binance for Futures trading. Lazy init."""

    def __init__(self):
        self._client = None

    def _get_client(self) -> Client:
        """Lazy-init: only connects when first used."""
        if self._client is None:
            self._client = Client(
                config.binance_api_key,
                config.binance_api_secret,
                testnet=config.binance_testnet,
            )
            if config.binance_testnet:
                # Override to Futures testnet
                self._client.API_URL = "https://testnet.binancefuture.com/fapi"
        return self._client

    def get_balance(self) -> dict:
        try:
            account = self._get_client().futures_account()
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

    def get_price(self, symbol: str) -> float:
        ticker = self._get_client().futures_symbol_ticker(symbol=symbol)
        return float(ticker["price"])

    def open_market_order(self, symbol: str, side: str, quantity: float) -> dict:
        try:
            order = self._get_client().futures_create_order(
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

    def close_market_order(self, symbol: str, side: str, quantity: float) -> dict:
        try:
            order = self._get_client().futures_create_order(
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

    def get_symbol_info(self, symbol: str) -> dict:
        try:
            info = self._get_client().futures_exchange_info()
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


# Singleton — lazy, won't connect until first tool call
binance = BinanceClient()
