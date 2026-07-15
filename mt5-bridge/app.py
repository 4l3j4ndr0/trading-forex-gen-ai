"""MT5 Bridge API — Multi-user, credentials from database."""

from functools import wraps

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify

from mt5_client import mt5_client
from db_client import get_user_broker_config
from config import Config

app = Flask(__name__)


def require_auth(f):
    """Validate API key, IP whitelist, and connect MT5 for the user."""
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

        # User ID
        user_id = request.headers.get("X-User-Id", "")
        if not user_id:
            return jsonify({"error": "X-User-Id header required"}), 400

        # Get broker config from DB
        broker_config = get_user_broker_config(user_id)
        if not broker_config:
            return jsonify({"error": f"No active broker config for user {user_id}"}), 404

        # Connect MT5 with user's credentials
        connected = mt5_client.connect(
            login=broker_config["mt5_login"],
            password=broker_config["mt5_password"],
            server=broker_config["mt5_server"],
        )
        if not connected:
            return jsonify({"error": "Failed to connect to MT5 with user credentials"}), 503

        # Pass broker config to handler
        request.broker_config = broker_config
        return f(*args, **kwargs)
    return decorated


def _suffix():
    """Get symbol suffix from current request's broker config."""
    return getattr(request, 'broker_config', {}).get('symbol_suffix', '')


# ─── Health (no auth) ─────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "multi_user": True})


# ─── Account ─────────────────────────────────────────────

@app.route("/account", methods=["GET"])
@require_auth
def account():
    info = mt5_client.get_account_info()
    if "error" in info:
        return jsonify(info), 500
    return jsonify(info)


# ─── Positions ────────────────────────────────────────────

@app.route("/positions", methods=["GET"])
@require_auth
def positions():
    pos = mt5_client.get_positions(suffix=_suffix())
    return jsonify(pos)


# ─── Symbol Info ──────────────────────────────────────────

@app.route("/symbol/<symbol>", methods=["GET"])
@require_auth
def symbol_info(symbol):
    info = mt5_client.get_symbol_info(symbol, suffix=_suffix())
    if "error" in info:
        return jsonify(info), 400
    return jsonify(info)


# ─── Tick ─────────────────────────────────────────────────

@app.route("/tick/<symbol>", methods=["GET"])
@require_auth
def tick(symbol):
    result = mt5_client.get_tick(symbol, suffix=_suffix())
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


# ─── Candles ──────────────────────────────────────────────

@app.route("/candles/<symbol>", methods=["GET"])
@require_auth
def candles(symbol):
    timeframe = request.args.get("timeframe", "H1").upper()
    count = min(int(request.args.get("count", 100)), 1000)
    result = mt5_client.get_candles(symbol, timeframe, count, suffix=_suffix())
    if isinstance(result, dict) and "error" in result:
        return jsonify(result), 400
    return jsonify({"symbol": symbol, "timeframe": timeframe, "count": len(result), "candles": result})


# ─── ATR ──────────────────────────────────────────────────

@app.route("/indicator/atr/<symbol>", methods=["GET"])
@require_auth
def indicator_atr(symbol):
    period = int(request.args.get("period", 14))
    timeframe = request.args.get("timeframe", "H1").upper()
    result = mt5_client.get_atr(symbol, timeframe, period, suffix=_suffix())
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


# ─── Spread ───────────────────────────────────────────────

@app.route("/indicator/spread/<symbol>", methods=["GET"])
@require_auth
def indicator_spread(symbol):
    result = mt5_client.get_spread(symbol, suffix=_suffix())
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


# ─── Open Order ───────────────────────────────────────────

@app.route("/order/open", methods=["POST"])
@require_auth
def order_open():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    required = ["symbol", "side", "lot", "sl", "tp"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    result = mt5_client.open_order(
        symbol=data["symbol"],
        side=data["side"],
        lot=float(data["lot"]),
        sl=float(data["sl"]),
        tp=float(data["tp"]),
        suffix=_suffix(),
        comment=data.get("comment", ""),
    )
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


# ─── Close Order ──────────────────────────────────────────

@app.route("/order/close", methods=["POST"])
@require_auth
def order_close():
    data = request.get_json()
    if not data or "ticket" not in data:
        return jsonify({"error": "ticket required"}), 400

    result = mt5_client.close_order(int(data["ticket"]), suffix=_suffix())
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


# ─── Modify Order ─────────────────────────────────────────

@app.route("/order/modify", methods=["POST"])
@require_auth
def order_modify():
    data = request.get_json()
    if not data or "ticket" not in data:
        return jsonify({"error": "ticket required"}), 400

    ticket = int(data["ticket"])
    pos_result = mt5_client.modify_order(ticket)
    if "error" in pos_result:
        return jsonify(pos_result), 400

    pos = pos_result["position"]
    new_sl = float(data["sl"]) if "sl" in data else pos.sl
    new_tp = float(data["tp"]) if "tp" in data else pos.tp

    result = mt5_client.modify_sltp(ticket, pos.symbol, new_sl, new_tp)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


# ─── Deal History (for reconciliation) ────────────────────

@app.route("/history/deal/<int:ticket>", methods=["GET"])
@require_auth
def deal_history(ticket):
    result = mt5_client.get_deal_history(ticket, suffix=_suffix())
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)


# ─── Run ──────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"🖥️  MT5 Bridge (multi-user) starting on port {Config.BRIDGE_PORT}")
    print(f"🔒 Auth: X-Bridge-Api-Key + X-User-Id → DB lookup")
    print(f"🗄️  DB: {Config.DATABASE_URL.split('@')[1] if '@' in Config.DATABASE_URL else 'configured'}")

    try:
        from waitress import serve
        print(f"🚀 Serving on http://0.0.0.0:{Config.BRIDGE_PORT}")
        serve(app, host="0.0.0.0", port=Config.BRIDGE_PORT)
    except ImportError:
        app.run(host="0.0.0.0", port=Config.BRIDGE_PORT, debug=True)
