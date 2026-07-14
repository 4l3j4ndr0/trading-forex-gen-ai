"""MT5 Bridge API — Exposes MetaTrader 5 operations via REST."""

import os
from functools import wraps

from flask import Flask, request, jsonify

from mt5_client import MT5Client
from config import Config

app = Flask(__name__)
mt5 = MT5Client()


def require_api_key(f):
    """Validate API key and IP whitelist."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # IP whitelist
        if Config.ALLOWED_IPS and Config.ALLOWED_IPS[0]:
            client_ip = request.remote_addr
            if client_ip not in Config.ALLOWED_IPS:
                return jsonify({"error": f"IP {client_ip} not allowed"}), 403

        # API key
        key = request.headers.get("X-Bridge-Api-Key", "")
        if key != Config.BRIDGE_API_KEY:
            return jsonify({"error": "Invalid API key"}), 401
        return f(*args, **kwargs)
    return decorated


# ─── Health ───────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    """Health check — no auth required."""
    connected = mt5.is_connected()
    account = mt5.get_account_info() if connected else None
    return jsonify({
        "status": "ok" if connected else "disconnected",
        "mt5_connected": connected,
        "broker": Config.MT5_SERVER,
        "account_type": "demo" if account and account.get("trade_mode") == 0 else "live",
    })


# ─── Account ─────────────────────────────────────────────

@app.route("/account", methods=["GET"])
@require_api_key
def account():
    """Get account info: balance, equity, margin."""
    info = mt5.get_account_info()
    if "error" in info:
        return jsonify(info), 500
    return jsonify(info)


# ─── Positions ────────────────────────────────────────────

@app.route("/positions", methods=["GET"])
@require_api_key
def positions():
    """Get all open positions."""
    pos = mt5.get_positions()
    return jsonify(pos)


# ─── Symbol Info ──────────────────────────────────────────

@app.route("/symbol/<symbol>", methods=["GET"])
@require_api_key
def symbol_info(symbol):
    """Get symbol info: spread, pip value, lot sizes."""
    info = mt5.get_symbol_info(symbol)
    if "error" in info:
        return jsonify(info), 400
    return jsonify(info)


# ─── Open Order ───────────────────────────────────────────

@app.route("/order/open", methods=["POST"])
@require_api_key
def order_open():
    """Open a market order.
    
    Body: {symbol, side, lot, sl, tp, comment?}
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    required = ["symbol", "side", "lot", "sl", "tp"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    result = mt5.open_order(
        symbol=data["symbol"],
        side=data["side"],
        lot=float(data["lot"]),
        sl=float(data["sl"]),
        tp=float(data["tp"]),
        comment=data.get("comment", ""),
    )

    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


# ─── Close Order ──────────────────────────────────────────

@app.route("/order/close", methods=["POST"])
@require_api_key
def order_close():
    """Close a position by ticket.
    
    Body: {ticket}
    """
    data = request.get_json()
    if not data or "ticket" not in data:
        return jsonify({"error": "ticket required"}), 400

    result = mt5.close_order(int(data["ticket"]))

    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


# ─── Modify Order ─────────────────────────────────────────

@app.route("/order/modify", methods=["POST"])
@require_api_key
def order_modify():
    """Modify SL/TP of an open position.
    
    Body: {ticket, sl?, tp?}
    """
    data = request.get_json()
    if not data or "ticket" not in data:
        return jsonify({"error": "ticket required"}), 400

    result = mt5.modify_order(
        ticket=int(data["ticket"]),
        sl=float(data["sl"]) if "sl" in data else None,
        tp=float(data["tp"]) if "tp" in data else None,
    )

    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


# ─── Run ──────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"🖥️  MT5 Bridge starting on port {Config.BRIDGE_PORT}")
    print(f"📡 Broker: {Config.MT5_SERVER}")

    # Initialize MT5 connection
    if mt5.initialize():
        print("✅ MT5 connected")
    else:
        print("⚠️  MT5 not connected — will retry on first request")

    # Production: use waitress
    try:
        from waitress import serve
        print(f"🚀 Serving on http://0.0.0.0:{Config.BRIDGE_PORT}")
        serve(app, host="0.0.0.0", port=Config.BRIDGE_PORT)
    except ImportError:
        # Dev: use Flask dev server
        app.run(host="0.0.0.0", port=Config.BRIDGE_PORT, debug=True)
