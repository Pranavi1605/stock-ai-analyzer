from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yfinance as yf
import numpy as np
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd

# ----------------------------- Flask Setup -----------------------------
app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)

# ----------------------------- Firebase Setup -----------------------------
cred = credentials.Certificate("serviceAccountKey.json")  # JSON in backend folder
firebase_admin.initialize_app(cred)
db = firestore.client()

# ----------------------------- Load NSE Symbols -----------------------------
symbols_df = pd.read_csv("nse_symbols.csv")
symbols_df.columns = symbols_df.columns.str.strip()  # remove extra spaces
all_stock_codes = [
    sym if sym.endswith(".NS") else sym + ".NS"
    for sym in symbols_df["SYMBOL"].tolist()  # match your CSV header
]

# ----------------------------- Serve Frontend -----------------------------
@app.route("/")
def serve_frontend():
    return send_from_directory(app.static_folder, "index.html")

# ----------------------------- Stock Analysis -----------------------------
@app.route("/analyze", methods=["POST"])
def analyze_stock():
    try:
        data_json = request.get_json()
        symbol = data_json.get("symbol", "").upper()
        if not symbol:
            return jsonify({"error": "Stock symbol is required"}), 400
        if not symbol.endswith(".NS"):
            symbol += ".NS"

        data = yf.download(symbol, period="3mo", interval="1d", progress=False)
        if data.empty:
            return jsonify({"error": f"No data found for symbol {symbol}"}), 404

        if isinstance(data.columns, tuple):
            data.columns = data.columns.get_level_values(0)

        data["MA20"] = data["Close"].rolling(20).mean()
        data["Returns"] = data["Close"].pct_change()
        data = data.dropna()

        close_price = float(data["Close"].iloc[-1])
        ma20 = float(data["MA20"].iloc[-1])

        reasons = []
        if close_price > ma20:
            decision = "BUY"
            reasons.append("Price is above the 20-day moving average")
        elif close_price < ma20:
            decision = "SELL"
            reasons.append("Price is below the 20-day moving average")
        else:
            decision = "HOLD"
            reasons.append("Price is equal to the moving average")

        volatility = float(np.std(data["Returns"]))
        if volatility > 0.03:
            risk = "High"
            reasons.append("High volatility indicates higher risk")
        elif volatility > 0.015:
            risk = "Medium"
            reasons.append("Moderate volatility observed")
        else:
            risk = "Low"
            reasons.append("Low volatility suggests stable price movement")

        prices = data["Close"].tail(30).squeeze().tolist()
        dates = data.index[-30:].strftime("%Y-%m-%d").tolist()

        # Save search to Firebase
        db.collection("user_searches").add({
            "symbol": symbol,
            "price": round(close_price, 2),
            "decision": decision,
            "risk": risk,
            "reason": reasons,
            "timestamp": firestore.SERVER_TIMESTAMP
        })

        return jsonify({
            "symbol": symbol,
            "price": round(close_price, 2),
            "decision": decision,
            "risk": risk,
            "reason": reasons,
            "prices": prices,
            "dates": dates
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------------------- Buy Suggestions -----------------------------
@app.route("/buy-suggestions", methods=["POST"])
def buy_suggestions():
    data = request.get_json()
    amount = float(data.get("amount", 0))
    if amount <= 0:
        return jsonify({"error": "Enter a valid amount"}), 400

    suggestions = []
    batch_size = 50  # fetch in batches

    for i in range(0, len(all_stock_codes), batch_size):
        batch_symbols = all_stock_codes[i:i+batch_size]
        try:
            prices_df = yf.download(batch_symbols, period="1d")["Close"].iloc[-1]
            if isinstance(prices_df, float):
                prices_df = {batch_symbols[0]: prices_df}
            else:
                prices_df = prices_df.to_dict()

            for sym, price in prices_df.items():
                if price <= amount:
                    suggestions.append({"symbol": sym, "price": price})
        except:
            continue

    if not suggestions:
        return jsonify({"message": "No stocks available for this amount"}), 200

    return jsonify(suggestions[:10])

# ----------------------------- Buy Stock -----------------------------
@app.route("/buy-stock", methods=["POST"])
def buy_stock():
    data = request.get_json()
    user_id = data.get("user_id")
    symbol = data.get("symbol")
    price = float(data.get("price", 0))
    quantity = int(data.get("quantity", 1))

    if not all([user_id, symbol, price]):
        return jsonify({"error": "Missing parameters"}), 400

    db.collection("users").document(user_id).collection("portfolio").document(symbol).set({
        "symbol": symbol,
        "price": price,
        "quantity": quantity
    })

    return jsonify({"message": f"Bought {quantity} of {symbol} at {price}"}), 200

# ----------------------------- Sell Stock -----------------------------
@app.route("/sell-stock", methods=["POST"])
def sell_stock():
    data = request.get_json()
    user_id = data.get("user_id")
    symbol = data.get("symbol")

    if not all([user_id, symbol]):
        return jsonify({"error": "Missing parameters"}), 400

    db.collection("users").document(user_id).collection("portfolio").document(symbol).delete()
    return jsonify({"message": f"Sold {symbol} successfully"}), 200

# ----------------------------- User Portfolio -----------------------------
@app.route("/portfolio/<user_id>", methods=["GET"])
def portfolio(user_id):
    docs = db.collection("users").document(user_id).collection("portfolio").stream()
    portfolio = [doc.to_dict() for doc in docs]
    return jsonify(portfolio)

# ----------------------------- Run App -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
