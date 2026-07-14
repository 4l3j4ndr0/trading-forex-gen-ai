"""MetaTrader 5 client wrapper — multi-user (connects per request)."""

import MetaTrader5 as mt5

from config import Config


class MT5Client:
    """MT5 client that connects dynamically based on user credentials."""

    def __init__(self):
        self._current_login = None

    def connect(self, login: int, password: str, server: str) -> bool:
        """Connect to MT5 with specific credentials. Reconnects if different user."""
        # If already connected with same login, skip
        if self._current_login == login and mt5.terminal_info():
            return True

        # Initialize MT5
        if not mt5.initialize(path=Config.MT5_PATH):
            return False

        authorized = mt5.login(login=login, password=password, server=server)
        if authorized:
            self._current_login = login
            return True

        mt5.shutdown()
        self._current_login = None
        return False

    def is_connected(self) -> bool:
        try:
            return mt5.terminal_info() is not None
        except Exception:
            return False

    def get_account_info(self) -> dict:
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
            "trade_mode": info.trade_mode,
        }

    def get_positions(self, suffix: str = "") -> list:
        positions = mt5.positions_get()
        if positions is None:
            return []
        result = []
        for pos in positions:
            symbol = pos.symbol
            if suffix and symbol.endswith(suffix):
                symbol = symbol[:-len(suffix)]
            result.append({
                "ticket": pos.ticket,
                "symbol": symbol,
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

    def get_symbol_info(self, symbol: str, suffix: str = "") -> dict:
        mt5_sym = symbol + suffix
        info = mt5.symbol_info(mt5_sym)
        if info is None:
            return {"error": f"Symbol '{symbol}' not found (tried {mt5_sym})"}
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

    def open_order(self, symbol: str, side: str, lot: float, sl: float, tp: float, suffix: str = "", comment: str = "") -> dict:
        mt5_sym = symbol + suffix
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
            "deviation": 20,
            "magic": 123456,
            "comment": comment[:63],
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

    def close_order(self, ticket: int, suffix: str = "") -> dict:
        position = mt5.positions_get(ticket=ticket)
        if not position:
            return {"error": f"Position {ticket} not found"}

        pos = position[0]
        symbol = pos.symbol  # Already has suffix from MT5
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

        # Clean symbol
        clean_symbol = pos.symbol
        if suffix and clean_symbol.endswith(suffix):
            clean_symbol = clean_symbol[:-len(suffix)]

        return {
            "closed": True,
            "ticket": ticket,
            "symbol": clean_symbol,
            "exit_price": result.price,
            "pnl": pos.profit,
        }

    def modify_order(self, ticket: int) -> dict:
        """Get position for modify — caller provides new sl/tp."""
        position = mt5.positions_get(ticket=ticket)
        if not position:
            return {"error": f"Position {ticket} not found"}
        return {"position": position[0]}

    def modify_sltp(self, ticket: int, symbol: str, sl: float, tp: float) -> dict:
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": symbol,
            "position": ticket,
            "sl": sl,
            "tp": tp,
        }
        result = mt5.order_send(request)
        if result is None:
            return {"error": f"Modify failed: {mt5.last_error()}"}
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {"error": f"Modify rejected: {result.comment} (code: {result.retcode})"}
        return {"modified": True, "ticket": ticket, "new_sl": sl, "new_tp": tp}

    def get_tick(self, symbol: str, suffix: str = "") -> dict:
        mt5_sym = symbol + suffix
        tick = mt5.symbol_info_tick(mt5_sym)
        if tick is None:
            return {"error": f"Cannot get tick for {symbol}"}
        return {"symbol": symbol, "bid": tick.bid, "ask": tick.ask, "time": int(tick.time), "volume": tick.volume}

    def get_candles(self, symbol: str, timeframe: str = "H1", count: int = 100, suffix: str = "") -> list | dict:
        TIMEFRAME_MAP = {
            "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1, "MN1": mt5.TIMEFRAME_MN1,
        }
        tf = TIMEFRAME_MAP.get(timeframe)
        if tf is None:
            return {"error": f"Invalid timeframe '{timeframe}'. Use: {list(TIMEFRAME_MAP.keys())}"}

        mt5_sym = symbol + suffix
        info = mt5.symbol_info(mt5_sym)
        if info is None:
            return {"error": f"Symbol '{symbol}' not found"}
        if not info.visible:
            mt5.symbol_select(mt5_sym, True)

        rates = mt5.copy_rates_from_pos(mt5_sym, tf, 0, count)
        if rates is None or len(rates) == 0:
            return {"error": f"No candle data for {symbol} {timeframe}"}

        return [{"time": int(r["time"]), "open": float(r["open"]), "high": float(r["high"]),
                 "low": float(r["low"]), "close": float(r["close"]), "volume": int(r["tick_volume"])} for r in rates]

    def get_atr(self, symbol: str, timeframe: str = "H1", period: int = 14, suffix: str = "") -> dict:
        candles = self.get_candles(symbol, timeframe, period + 50, suffix)
        if isinstance(candles, dict) and "error" in candles:
            return candles
        if len(candles) < period + 1:
            return {"error": f"Not enough data. Got {len(candles)}, need {period + 1}"}

        true_ranges = []
        for i in range(1, len(candles)):
            tr = max(candles[i]["high"] - candles[i]["low"],
                     abs(candles[i]["high"] - candles[i - 1]["close"]),
                     abs(candles[i]["low"] - candles[i - 1]["close"]))
            true_ranges.append(tr)

        atr = sum(true_ranges[-period:]) / period
        pip_size = 0.01 if "JPY" in symbol else 0.0001

        return {"symbol": symbol, "timeframe": timeframe, "period": period,
                "atr": round(atr, 6), "atr_pips": round(atr / pip_size, 1), "last_candle": candles[-1]}

    def get_spread(self, symbol: str, suffix: str = "") -> dict:
        mt5_sym = symbol + suffix
        info = mt5.symbol_info(mt5_sym)
        if info is None:
            return {"error": f"Symbol '{symbol}' not found"}
        tick = mt5.symbol_info_tick(mt5_sym)
        if tick is None:
            return {"error": f"Cannot get tick for {symbol}"}
        pip_size = 0.01 if "JPY" in symbol else 0.0001
        return {"symbol": symbol, "spread_points": info.spread,
                "spread_pips": round(info.spread * info.point / pip_size, 1),
                "bid": tick.bid, "ask": tick.ask, "point": info.point}


# Singleton
mt5_client = MT5Client()
