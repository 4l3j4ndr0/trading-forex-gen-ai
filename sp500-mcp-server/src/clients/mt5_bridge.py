"""
MT5 Bridge Client — SP500 specific
Reuses the same MT5 Bridge on the VPS but with US500Cash symbol
"""
import os
import httpx
from typing import Optional

BRIDGE_URL = os.getenv("MT5_BRIDGE_URL", "http://mt5-bridge.awslearn.cloud:5000")
API_KEY = os.getenv("MT5_BRIDGE_API_KEY", "")
SYMBOL = os.getenv("SYMBOL", "US500Cash")
USER_ID = os.getenv("USER_ID", "5f7b54c4-3bb5-487e-897e-e273112a914b")

HEADERS = {"X-Bridge-Api-Key": API_KEY, "X-User-Id": USER_ID}
TIMEOUT = 15.0


async def get_candles(timeframe: str = "M5", count: int = 100) -> dict:
    """Get OHLCV candles for US500Cash"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(
            f"{BRIDGE_URL}/candles/{SYMBOL}",
            params={"timeframe": timeframe, "count": count},
            headers=HEADERS
        )
        r.raise_for_status()
        data = r.json()
        # Normalize time from unix timestamp to string
        for c in data.get("candles", []):
            if isinstance(c.get("time"), (int, float)):
                from datetime import datetime, timezone
                c["time"] = datetime.fromtimestamp(c["time"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        return data


async def get_account_info() -> dict:
    """Get account balance, equity, margin"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(f"{BRIDGE_URL}/account", headers=HEADERS)
        r.raise_for_status()
        return r.json()


async def get_positions(symbol: Optional[str] = None) -> dict:
    """Get open positions, filtered to US500Cash"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(f"{BRIDGE_URL}/positions", headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        # Bridge may return list directly or {"positions": [...]}
        if isinstance(data, list):
            positions_list = data
        else:
            positions_list = data.get("positions", [])
        # Filter to only US500Cash positions
        target = symbol or SYMBOL
        positions = [
            p for p in positions_list
            if p.get("symbol", "").replace("#", "").replace(".", "") == target
        ]
        return {"positions": positions}


async def open_position(side: str, lot_size: float, sl_points: float = 0, tp_points: float = 0, comment: str = "") -> dict:
    """Open a position on US500Cash"""
    # Get current price to calculate SL/TP levels
    tick = await get_spread()
    current_price = float(tick.get("bid", 0)) if side.upper() == "SELL" else float(tick.get("ask", 0))

    sl_price = 0.0
    tp_price = 0.0
    if sl_points > 0:
        sl_price = (current_price - sl_points) if side.upper() == "BUY" else (current_price + sl_points)
    if tp_points > 0:
        tp_price = (current_price + tp_points) if side.upper() == "BUY" else (current_price - tp_points)

    payload = {
        "symbol": SYMBOL,
        "side": side.lower(),
        "lot": lot_size,
        "sl": round(sl_price, 2),
        "tp": round(tp_price, 2),
        "comment": comment,
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{BRIDGE_URL}/order/open", json=payload, headers=HEADERS)
        r.raise_for_status()
        return r.json()


async def close_position(ticket: int, reason: str = "") -> dict:
    """Close a position by ticket"""
    payload = {"ticket": ticket}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{BRIDGE_URL}/order/close", json=payload, headers=HEADERS)
        r.raise_for_status()
        return r.json()


async def modify_position(ticket: int, sl: float = 0, tp: float = 0) -> dict:
    """Modify SL/TP of an open position"""
    payload = {"ticket": ticket}
    if sl > 0:
        payload["sl"] = sl
    if tp > 0:
        payload["tp"] = tp

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{BRIDGE_URL}/order/modify", json=payload, headers=HEADERS)
        r.raise_for_status()
        return r.json()


async def get_symbol_info() -> dict:
    """Get US500Cash symbol specifications"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(f"{BRIDGE_URL}/symbol/{SYMBOL}", headers=HEADERS)
        r.raise_for_status()
        return r.json()


async def get_spread() -> dict:
    """Get current spread for US500Cash"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(f"{BRIDGE_URL}/indicator/spread/{SYMBOL}", headers=HEADERS)
        r.raise_for_status()
        return r.json()


async def get_deal_history(ticket: int) -> dict:
    """Get deal history for reconciliation"""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(f"{BRIDGE_URL}/history/deal/{ticket}", headers=HEADERS)
        r.raise_for_status()
        return r.json()
