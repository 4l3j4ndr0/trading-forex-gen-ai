"""MetaTrader 5 client wrapper."""

import MetaTrader5 as mt5

from config import Config


def _sym(symbol: str) -> str:
    """Add broker suffix to symbol. EURUSD → EURUSD#"""
    suffix = Config.SYMBOL_SUFFIX
    if suffix and not symbol.endswith(suffix):
        return symbol + suffix
    return symbol


def _clean_sym(symbol: str) -> str:
    """Remove broker suffix from symbol. EURUSD# → EURUSD"""
    suffix = Config.SYMBOL_SUFFIX
    if suffix and symbol.endswith(suffix):
        return symbol[:-len(suffix)]
    return symbol


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
                "symbol": _clean_sym(pos.symbol),
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
        mt5_sym = _sym(symbol)
        info = mt5.symbol_info(mt5_sym)

        if info is None:
            return {"error": f"Symbol '{symbol}' not found (tried {mt5_sym})"}

        # Ensure symbol is visible in Market Watch
        if not info.visible:
            mt5.symbol_select(mt5_sym, True)
            info = mt5.symbol_info(mt5_sym)

        tick = mt5.symbol_info_tick(mt5_sym)
        spread_points = info.spread if info.spread else (tick.ask - tick.bid) / info.point if tick else 0

        return {
            "symbol": symbol,
            "spread_points": spread_points,
            "spread_pips": round(spread_points * info.point / (0.01 if "JPY" in symbol else 0.0001), 1),
            "pip_value": info.trade_tick_value,
            "min_lot": info.volume_min,
            "max_lot": info.volume_max,
            "lot_step": info.volume_step,
            "digits": info.digits,
            "point": info.point,
            "trade_allowed": info.trade_mode == 4,
            "bid": tick.bid if tick else 0,
            "ask": tick.ask if tick else 0,
        }

    def open_order(self, symbol: str, side: str, lot: float, sl: float, tp: float, comment: str = "") -> dict:
        """Open a market order."""
        self._ensure_connected()
        mt5_sym = _sym(symbol)

        # Get current price
        tick = mt5.symbol_info_tick(mt5_sym)
        if tick is None:
            return {"error": f"Cannot get price for {symbol}"}

        order_type = mt5.ORDER_TYPE_BUY if side.upper() == "BUY" else mt5.ORDER_TYPE_SELL
        price = tick.ask if side.upper() == "BUY" else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": mt5_sym,
            "volume": lot,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,  # Max slippage in points
            "magic": 123456,  # EA identifier
            "comment": comment[:63],  # MT5 max comment length
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
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
            "type_filling": mt5.ORDER_FILLING_RETURN,
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

    # ─── Market Data ──────────────────────────────────────

    TIMEFRAME_MAP = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
        "W1": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1,
    }

    def get_candles(self, symbol: str, timeframe: str = "H1", count: int = 100) -> list | dict:
        """Get OHLCV candles from MT5."""
        self._ensure_connected()
        mt5_sym = _sym(symbol)

        tf = self.TIMEFRAME_MAP.get(timeframe)
        if tf is None:
            return {"error": f"Invalid timeframe '{timeframe}'. Use: {list(self.TIMEFRAME_MAP.keys())}"}

        # Ensure symbol is in Market Watch
        info = mt5.symbol_info(mt5_sym)
        if info is None:
            return {"error": f"Symbol '{symbol}' not found"}
        if not info.visible:
            mt5.symbol_select(mt5_sym, True)

        rates = mt5.copy_rates_from_pos(mt5_sym, tf, 0, count)
        if rates is None or len(rates) == 0:
            return {"error": f"No candle data for {symbol} {timeframe}"}

        candles = []
        for r in rates:
            candles.append({
                "time": int(r["time"]),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": int(r["tick_volume"]),
            })

        return candles

    def get_atr(self, symbol: str, timeframe: str = "H1", period: int = 14) -> dict:
        """Calculate ATR from candle data."""
        self._ensure_connected()

        # Need period + 1 candles to calculate ATR
        candles = self.get_candles(symbol, timeframe, period + 50)
        if isinstance(candles, dict) and "error" in candles:
            return candles

        if len(candles) < period + 1:
            return {"error": f"Not enough data. Got {len(candles)} candles, need {period + 1}"}

        # Calculate True Range for each candle
        true_ranges = []
        for i in range(1, len(candles)):
            high = candles[i]["high"]
            low = candles[i]["low"]
            prev_close = candles[i - 1]["close"]

            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close),
            )
            true_ranges.append(tr)

        # ATR = SMA of last `period` true ranges
        atr_values = []
        for i in range(len(true_ranges) - period, len(true_ranges)):
            window = true_ranges[i - period + 1 : i + 1]
            atr_values.append(sum(window) / len(window))

        current_atr = atr_values[-1] if atr_values else 0

        # Convert to pips
        if "JPY" in symbol:
            pip_size = 0.01
        else:
            pip_size = 0.0001

        atr_pips = current_atr / pip_size

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "period": period,
            "atr": round(current_atr, 6),
            "atr_pips": round(atr_pips, 1),
            "last_candle": candles[-1],
        }

    def get_spread(self, symbol: str) -> dict:
        """Get current real-time spread."""
        self._ensure_connected()
        mt5_sym = _sym(symbol)

        info = mt5.symbol_info(mt5_sym)
        if info is None:
            return {"error": f"Symbol '{symbol}' not found"}

        tick = mt5.symbol_info_tick(mt5_sym)
        if tick is None:
            return {"error": f"Cannot get tick for {symbol}"}

        spread_points = info.spread
        point = info.point

        if "JPY" in symbol:
            pip_size = 0.01
        else:
            pip_size = 0.0001

        spread_pips = spread_points * point / pip_size

        return {
            "symbol": symbol,
            "spread_points": spread_points,
            "spread_pips": round(spread_pips, 1),
            "bid": tick.bid,
            "ask": tick.ask,
            "point": point,
        }

    def get_tick(self, symbol: str) -> dict:
        """Get current bid/ask."""
        self._ensure_connected()
        mt5_sym = _sym(symbol)

        tick = mt5.symbol_info_tick(mt5_sym)
        if tick is None:
            return {"error": f"Cannot get tick for {symbol}"}

        return {
            "symbol": symbol,
            "bid": tick.bid,
            "ask": tick.ask,
            "time": int(tick.time),
            "volume": tick.volume,
        }
