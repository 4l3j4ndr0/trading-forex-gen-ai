"""MetaTrader 5 client wrapper."""

import MetaTrader5 as mt5

from config import Config


class MT5Client:
    """Wrapper around the MetaTrader5 Python library."""

    def __init__(self):
        self._connected = False

    def initialize(self) -> bool:
        """Initialize MT5 connection and login."""
        if not mt5.initialize(path=Config.MT5_PATH):
            return False

        authorized = mt5.login(
            login=Config.MT5_LOGIN,
            password=Config.MT5_PASSWORD,
            server=Config.MT5_SERVER,
        )

        if authorized:
            self._connected = True
            return True

        mt5.shutdown()
        return False

    def _ensure_connected(self):
        """Reconnect if disconnected."""
        if not self._connected or not mt5.terminal_info():
            self.initialize()

    def is_connected(self) -> bool:
        """Check if MT5 is connected."""
        try:
            info = mt5.terminal_info()
            return info is not None
        except Exception:
            return False

    def get_account_info(self) -> dict:
        """Get account balance, equity, margin."""
        self._ensure_connected()
        info = mt5.account_info()
        if info is None:
            return {"error": f"Cannot get account info: {mt5.last_error()}"}

        return {
            "login": info.login,
            "balance": info.balance,
            "equity": info.equity,
            "margin": info.margin,
            "free_margin": info.margin_free,
            "margin_level": info.margin_level,
            "leverage": info.leverage,
            "currency": info.currency,
            "trade_mode": info.trade_mode,  # 0=demo, 1=contest, 2=real
            "open_positions": info.positions if hasattr(info, 'positions') else 0,
        }

    def get_positions(self) -> list:
        """Get all open positions."""
        self._ensure_connected()
        positions = mt5.positions_get()

        if positions is None:
            return []

        result = []
        for pos in positions:
            result.append({
                "ticket": pos.ticket,
                "symbol": pos.symbol,
                "side": "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL",
                "lot_size": pos.volume,
                "entry_price": pos.price_open,
                "current_price": pos.price_current,
                "sl": pos.sl,
                "tp": pos.tp,
                "pnl": pos.profit,
                "swap": pos.swap,
                "comment": pos.comment,
                "time_open": str(pos.time),
            })

        return result

    def get_symbol_info(self, symbol: str) -> dict:
        """Get symbol details: spread, pip value, lot sizes."""
        self._ensure_connected()
        info = mt5.symbol_info(symbol)

        if info is None:
            return {"error": f"Symbol '{symbol}' not found"}

        # Ensure symbol is visible in Market Watch
        if not info.visible:
            mt5.symbol_select(symbol, True)
            info = mt5.symbol_info(symbol)

        tick = mt5.symbol_info_tick(symbol)
        spread_points = info.spread if info.spread else (tick.ask - tick.bid) / info.point if tick else 0

        return {
            "symbol": symbol,
            "spread_points": spread_points,
            "spread_pips": round(spread_points * info.point / (0.01 if "JPY" in symbol else 0.0001), 1),
            "pip_value": info.trade_tick_value,  # Value of 1 point movement per lot
            "min_lot": info.volume_min,
            "max_lot": info.volume_max,
            "lot_step": info.volume_step,
            "digits": info.digits,
            "point": info.point,
            "trade_allowed": info.trade_mode != 0,
            "bid": tick.bid if tick else 0,
            "ask": tick.ask if tick else 0,
        }

    def open_order(self, symbol: str, side: str, lot: float, sl: float, tp: float, comment: str = "") -> dict:
        """Open a market order."""
        self._ensure_connected()

        # Get current price
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"error": f"Cannot get price for {symbol}"}

        order_type = mt5.ORDER_TYPE_BUY if side.upper() == "BUY" else mt5.ORDER_TYPE_SELL
        price = tick.ask if side.upper() == "BUY" else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,  # Max slippage in points
            "magic": 123456,  # EA identifier
            "comment": comment[:63],  # MT5 max comment length
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        if result is None:
            return {"error": f"Order failed: {mt5.last_error()}"}

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {"error": f"Order rejected: {result.comment} (code: {result.retcode})"}

        return {
            "ticket": result.order,
            "symbol": symbol,
            "side": side.upper(),
            "lot_size": lot,
            "entry_price": result.price,
            "sl": sl,
            "tp": tp,
            "comment": comment,
        }

    def close_order(self, ticket: int) -> dict:
        """Close a position by ticket."""
        self._ensure_connected()

        # Find the position
        position = mt5.positions_get(ticket=ticket)
        if not position:
            return {"error": f"Position {ticket} not found"}

        pos = position[0]
        symbol = pos.symbol
        lot = pos.volume
        close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"error": f"Cannot get price for {symbol}"}

        price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 123456,
            "comment": "close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        if result is None:
            return {"error": f"Close failed: {mt5.last_error()}"}

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {"error": f"Close rejected: {result.comment} (code: {result.retcode})"}

        return {
            "closed": True,
            "ticket": ticket,
            "symbol": symbol,
            "exit_price": result.price,
            "pnl": pos.profit,
        }

    def modify_order(self, ticket: int, sl: float = None, tp: float = None) -> dict:
        """Modify SL/TP of an open position."""
        self._ensure_connected()

        position = mt5.positions_get(ticket=ticket)
        if not position:
            return {"error": f"Position {ticket} not found"}

        pos = position[0]

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": pos.symbol,
            "position": ticket,
            "sl": sl if sl is not None else pos.sl,
            "tp": tp if tp is not None else pos.tp,
        }

        result = mt5.order_send(request)

        if result is None:
            return {"error": f"Modify failed: {mt5.last_error()}"}

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {"error": f"Modify rejected: {result.comment} (code: {result.retcode})"}

        return {
            "modified": True,
            "ticket": ticket,
            "old_sl": pos.sl,
            "new_sl": sl if sl is not None else pos.sl,
            "old_tp": pos.tp,
            "new_tp": tp if tp is not None else pos.tp,
        }
