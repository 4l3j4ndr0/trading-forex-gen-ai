"""Binance Futures API client — credentials from request headers via context vars."""

from binance.client import Client
from binance.exceptions import BinanceAPIException

from src.core.config import config


def _get_credentials():
    """Get Binance credentials from context vars (set by middleware) or fallback to env."""
    from server import binance_api_key_var, binance_api_secret_var, binance_testnet_var

    key = binance_api_key_var.get() or config.binance_api_key
    secret = binance_api_secret_var.get() or config.binance_api_secret
    testnet = binance_testnet_var.get()

    return key, secret, testnet


def _create_client() -> Client:
    """Create a Binance client with current request credentials."""
    key, secret, testnet = _get_credentials()

    if not key or not secret:
        raise ValueError("Binance credentials not provided. Send X-Binance-Api-Key and X-Binance-Api-Secret headers.")

    client = Client(key, secret, testnet=testnet)
    if testnet:
        client.API_URL = "https://testnet.binancefuture.com/fapi"
    return client


class BinanceClient:
    """Binance Futures client — uses per-request credentials from headers."""

    def get_balance(self) -> dict:
        try:
            account = _create_client().futures_account()
            return {
                "total_balance": float(account["totalWalletBalance"]),
                "available_balance": float(account["availableBalance"]),
                "unrealized_pnl": float(account["totalUnrealizedProfit"]),
                "total_margin_balance": float(account["totalMarginBalance"]),
            }
        except ValueError as e:
            return {"error": str(e)}
        except BinanceAPIException as e:
            return {"error": f"Binance API error: {e.message}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def get_price(self, symbol: str) -> float:
        ticker = _create_client().futures_symbol_ticker(symbol=symbol)
        return float(ticker["price"])

    def open_market_order(self, symbol: str, side: str, quantity: float) -> dict:
        try:
            order = _create_client().futures_create_order(
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
        except ValueError as e:
            return {"error": str(e)}
        except BinanceAPIException as e:
            return {"error": f"Binance API error: {e.message}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def close_market_order(self, symbol: str, side: str, quantity: float) -> dict:
        try:
            order = _create_client().futures_create_order(
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
        except ValueError as e:
            return {"error": str(e)}
        except BinanceAPIException as e:
            return {"error": f"Binance API error: {e.message}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def get_symbol_info(self, symbol: str) -> dict:
        try:
            info = _create_client().futures_exchange_info()
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
        except ValueError as e:
            return {"error": str(e)}
        except BinanceAPIException as e:
            return {"error": f"Binance API error: {e.message}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}


# Singleton
binance = BinanceClient()
