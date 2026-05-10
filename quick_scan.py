"""
quick_scan.py
=============
Ye script kuch popular stocks scan karke portfolio_store.json mein save karta hai
taaki dashboard mein data dikhne lage.

Run: python quick_scan.py
"""

import json
import os
import uuid
from datetime import datetime

STORE_FILE = "portfolio_store.json"

# ── Load existing store ───────────────────────────────────────
def load():
    if os.path.exists(STORE_FILE):
        try:
            with open(STORE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"portfolio": [], "alerts": [], "decisions": []}

def save(data):
    with open(STORE_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

# ── Symbols to scan (fast subset) ────────────────────────────
SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "WIPRO.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "LT.NS",
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "AMD",
    "SPY", "QQQ",
]

def main():
    # Import project modules
    try:
        from ai_engine import AIEngine
    except Exception as e:
        print(f"[ERROR] Could not import AIEngine: {e}")
        return

    store = load()
    # Remove old decisions so we get fresh data
    store["decisions"] = [
        d for d in store["decisions"]
        if d.get("symbol") not in SYMBOLS
    ]

    print(f"\n{'='*55}")
    print(f"  Quick Scan — {len(SYMBOLS)} stocks")
    print(f"{'='*55}\n")

    for symbol in SYMBOLS:
        try:
            print(f"  Analyzing {symbol}...", end=" ", flush=True)
            result = AIEngine.analyze_stock(symbol)

            action     = result.get("action", "HOLD")
            confidence = float(result.get("confidence", 0))
            price      = float(result.get("current_price", 0))
            tech_score = float(result.get("technical_score", 0))
            reason     = result.get("reason", "")

            # Save decision
            decision = {
                "id":                str(uuid.uuid4()),
                "symbol":            symbol,
                "action":            action,
                "confidence":        confidence,
                "reason":            reason,
                "price_at_decision": price,
                "technical_score":   tech_score,
                "created_at":        datetime.now().isoformat(),
            }
            store["decisions"].append(decision)
            save(store)

            icon = "🟢" if action == "BUY" else "🔴" if action == "SELL" else "🟡"
            print(f"{icon} {action} ({confidence:.0f}%) @ {price:.2f}")

        except Exception as e:
            print(f"❌ Error: {e}")

    save(store)
    print(f"\n{'='*55}")
    print(f"  Done! Refresh dashboard: http://localhost:5000")
    print(f"{'='*55}\n")

if __name__ == "__main__":
    main()