from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
import os

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)

# ---------- FIREBASE ----------
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# ---------- UTIL ----------
def normalize_symbol(sym):
    if not sym:
        return None
    return sym.replace(".NS", "").strip().upper()

# ---------- BUY STOCK ----------
@app.route("/buy-stock", methods=["POST"])
def buy_stock():
    d = request.json
    user = d["user_id"]
    symbol = normalize_symbol(d["symbol"])
    qty = int(d.get("quantity", 1))
    buy_price = float(d["price"])

    ref = db.collection("users").document(user)\
        .collection("portfolio").document(symbol)

    doc = ref.get()
    if doc.exists:
        old = doc.to_dict()
        ref.update({
            "quantity": old["quantity"] + qty,
            "buy_price": buy_price
        })
    else:
        ref.set({
            "symbol": symbol,
            "buy_price": buy_price,
            "quantity": qty
        })

    return jsonify({"message": "Stock bought successfully"})

# ---------- SELL STOCK ----------
@app.route("/sell-stock", methods=["POST"])
def sell_stock():
    d = request.json
    user = d["user_id"]
    symbol = normalize_symbol(d["symbol"])
    sell_qty = int(d["quantity"])

    ref = db.collection("users").document(user)\
        .collection("portfolio").document(symbol)

    doc = ref.get()
    if not doc.exists:
        return jsonify({"message": "Stock not found"}), 404

    qty = doc.to_dict()["quantity"]
    if sell_qty >= qty:
        ref.delete()
    else:
        ref.update({"quantity": qty - sell_qty})

    return jsonify({"message": "Sell successful"})

# ---------- BUY SUGGESTIONS ----------
@app.route("/buy-suggestions", methods=["POST"])
def buy_suggestions():
    data = request.json
    amount = float(data.get("amount", 0))
    clean = {}

    for doc in db.collection("stock_prices").stream():
        stock = doc.to_dict()
        price = stock.get("price")
        symbol = normalize_symbol(doc.id)

        if not price or price <= 0 or price > amount:
            continue

        # keep cheapest price per symbol
        if symbol not in clean or price < clean[symbol]["price"]:
            clean[symbol] = {
                "symbol": symbol,
                "price": price,
                "qty": int(amount // price)
            }

    results = list(clean.values())
    results.sort(key=lambda x: x["qty"], reverse=True)

    return jsonify(results[:20])

# ---------- SELL SUGGESTIONS ----------
@app.route("/sell-suggestions/<user>", methods=["GET"])
def sell_suggestions(user):
    suggestions = []

    portfolio_ref = db.collection("users").document(user).collection("portfolio")
    for doc in portfolio_ref.stream():
        stock = doc.to_dict()
        symbol = normalize_symbol(doc.id)
        qty = stock["quantity"]
        buy_price = stock["buy_price"]

        # try both SYMBOL and SYMBOL.NS
        price_doc = db.collection("stock_prices").document(symbol).get()
        if not price_doc.exists:
            price_doc = db.collection("stock_prices").document(symbol + ".NS").get()

        curr_price = price_doc.to_dict()["price"] if price_doc.exists else buy_price
        profit = (curr_price - buy_price) * qty

        suggestions.append({
            "symbol": symbol,
            "quantity": qty,
            "current_price": curr_price,
            "profit": profit,
            "suggested_sell_qty": qty
        })

    suggestions.sort(key=lambda x: x["profit"], reverse=True)

    return jsonify(suggestions)

# ---------- PORTFOLIO ----------
@app.route("/portfolio/<user>")
def portfolio(user):
    total_invested = 0
    current_value = 0
    stocks = []

    for doc in db.collection("users").document(user).collection("portfolio").stream():
        s = doc.to_dict()
        symbol = normalize_symbol(doc.id)
        qty = s["quantity"]
        buy_price = s["buy_price"]

        price_doc = db.collection("stock_prices").document(symbol).get()
        if not price_doc.exists:
            price_doc = db.collection("stock_prices").document(symbol + ".NS").get()

        curr_price = price_doc.to_dict()["price"] if price_doc.exists else buy_price

        invested = buy_price * qty
        current = curr_price * qty

        total_invested += invested
        current_value += current

        stocks.append({
            "symbol": symbol,
            "quantity": qty,
            "buy_price": buy_price,
            "current_price": curr_price,
            "invested": invested,
            "current_value": current,
            "profit": current - invested
        })

    profit = current_value - total_invested

    return jsonify({
        "total_invested": total_invested,
        "current_value": current_value,
        "profit": profit,
        "direction": "UP" if profit >= 0 else "DOWN",
        "stocks": stocks
    })

# ---------- FRONTEND ----------
@app.route("/", defaults={"path": "index.html"})
@app.route("/<path:path>")
def serve_frontend(path):
    frontend_folder = os.path.join(os.path.dirname(__file__), "../frontend")
    return send_from_directory(frontend_folder, path)

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)
