"""
Flask Dashboard Server
======================
Run:  python dashboard.py
Open: http://localhost:5000
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import os, json, logging, time

app = Flask(__name__, template_folder="templates")
CORS(app)
logger = logging.getLogger(__name__)

STORE_FILE = "portfolio_store.json"
USD_TO_INR = 84.0
_usd_inr_time = 0

# ── helpers ───────────────────────────────────────────────────

def safe_float(v):
    try:    return float(v)
    except: return 0.0

def load_store() -> dict:
    if os.path.exists(STORE_FILE):
        try:
            with open(STORE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[Store] load error: {e}")
    return {"portfolio": [], "alerts": [], "decisions": []}

def save_store(data: dict):
    with open(STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

def get_usd_inr() -> float:
    """USD/INR rate — cached 1 hour, fallback 84."""
    global USD_TO_INR, _usd_inr_time
    if time.time() - _usd_inr_time < 3600:
        return USD_TO_INR
    try:
        import yfinance as yf
        h = yf.Ticker("USDINR=X").history(period="1d")
        if not h.empty:
            USD_TO_INR = safe_float(h["Close"].iloc[-1])
            _usd_inr_time = time.time()
    except Exception:
        pass
    return USD_TO_INR

def get_live_price_fast(symbol: str, fallback: float) -> float:
    """
    Try yfinance fast_info (non-blocking, 2s timeout).
    Returns fallback if anything fails — dashboard never hangs.
    """
    try:
        import yfinance as yf
        info = yf.Ticker(symbol).fast_info
        p = safe_float(info.last_price)
        return p if p > 0 else fallback
    except Exception:
        return fallback

def get_extra_info(symbol: str) -> dict:
    """yfinance .info — only called from modal chart API, not main table."""
    try:
        import yfinance as yf
        info = yf.Ticker(symbol).info
        return {
            "sector":    info.get("sector", "—") or "—",
            "market_cap": info.get("marketCap", 0) or 0,
            "pe":        safe_float(info.get("trailingPE", 0)),
            "pb":        safe_float(info.get("priceToBook", 0)),
            "week52h":   safe_float(info.get("fiftyTwoWeekHigh", 0)),
            "week52l":   safe_float(info.get("fiftyTwoWeekLow", 0)),
            "avg_vol":   info.get("averageVolume", 0) or 0,
            "div_yield": safe_float(info.get("dividendYield", 0)) * 100,
            "beta":      safe_float(info.get("beta", 0)),
            "name":      info.get("longName", symbol),
        }
    except Exception:
        return {
            "sector": "—", "market_cap": 0, "pe": 0, "pb": 0,
            "week52h": 0, "week52l": 0, "avg_vol": 0,
            "div_yield": 0, "beta": 0, "name": symbol,
        }

# ── routes ────────────────────────────────────────────────────

@app.route("/")
def index():
    base = os.path.dirname(os.path.abspath(__file__))
    for path in [
        os.path.join(base, "dashboard.html"),
        os.path.join(base, "templates", "dashboard.html"),
    ]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    return "<h2>dashboard.html not found</h2>", 404


@app.route("/api/market")
def market_overview():
    """Market indices — uses stored prices when yfinance is slow."""
    indices = {
        "NIFTY 50":  "^NSEI",
        "SENSEX":    "^BSESN",
        "NASDAQ":    "^IXIC",
        "S&P 500":   "^GSPC",
        "DOW JONES": "^DJI",
    }
    result = []
    try:
        import yfinance as yf
        for name, ticker in indices.items():
            try:
                hist = yf.Ticker(ticker).history(period="5d")
                if len(hist) >= 2:
                    prev = safe_float(hist["Close"].iloc[-2])
                    curr = safe_float(hist["Close"].iloc[-1])
                    chg  = round(curr - prev, 2)
                    chgp = round(chg / prev * 100, 2) if prev else 0
                else:
                    curr = chg = chgp = 0
                result.append({"name": name, "value": round(curr, 2),
                                "change": chg, "change_pct": chgp})
            except Exception:
                result.append({"name": name, "value": 0, "change": 0, "change_pct": 0})
    except Exception:
        for name in indices:
            result.append({"name": name, "value": 0, "change": 0, "change_pct": 0})
    return jsonify(result)


@app.route("/api/stocks")
def get_stocks():
    """
    AI signals from portfolio_store.json.
    Uses STORED price as primary — optionally refreshes in background.
    Never hangs even on Sunday / no internet.
    """
    try:
        rate  = get_usd_inr()
        store = load_store()

        # Deduplicate — keep latest decision per symbol
        seen = {}
        for d in store.get("decisions", []):
            seen[d["symbol"]] = d

        if not seen:
            return jsonify([])

        result = []
        for symbol, d in seen.items():
            is_indian  = ".NS" in symbol or ".BO" in symbol

            # ── Price: stored first, live only if stored = 0 ──
            stored_price = safe_float(d.get("price_at_decision", 0))
            if stored_price > 0:
                price_raw = stored_price
            else:
                price_raw = get_live_price_fast(symbol, 0)

            price_inr = price_raw if is_indian else round(price_raw * rate, 2)

            result.append({
                "symbol":     symbol,
                "name":       symbol.replace(".NS", "").replace(".BO", ""),
                "action":     d.get("action", "HOLD"),
                "confidence": round(safe_float(d.get("confidence", 0)), 1),
                "price":      round(price_inr, 2),
                "price_raw":  round(price_raw, 2),
                "change_pct": 0,        # updated by /api/prices separately
                "reason":     d.get("reason", ""),
                "tech_score": round(safe_float(d.get("technical_score", 0)), 1),
                "sector":     "—",
                "market_cap": 0,
                "pe":         0,
                "pb":         0,
                "week52h":    0,
                "week52l":    0,
                "avg_vol":    0,
                "div_yield":  0,
                "beta":       0,
                "is_indian":  is_indian,
                "scanned_at": str(d.get("created_at", ""))[:16],
            })

        return jsonify(result)

    except Exception as e:
        logger.error(f"/api/stocks error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/stock_info/<symbol>")
def stock_info(symbol: str):
    """
    Heavy yfinance .info call — only called when user opens modal.
    Separated so main table loads instantly.
    """
    try:
        rate = get_usd_inr()
        is_indian = ".NS" in symbol or ".BO" in symbol
        info = get_extra_info(symbol)
        if not is_indian:
            info["week52h"] = round(info["week52h"] * rate, 2)
            info["week52l"] = round(info["week52l"] * rate, 2)
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/portfolio")
def get_portfolio():
    """Portfolio from portfolio_store.json — stored prices, no live fetch."""
    try:
        rate  = get_usd_inr()
        store = load_store()
        holdings = [h for h in store.get("portfolio", [])
                    if h.get("is_active", True)]

        items = []
        total_inv = total_val = 0.0

        for h in holdings:
            symbol    = h["symbol"]
            is_indian = ".NS" in symbol or ".BO" in symbol
            bp   = safe_float(h.get("buy_price", 0))
            qty  = safe_float(h.get("quantity", 0))
            inv  = safe_float(h.get("invested_amount", bp * qty))

            # Use stored current_price if available
            curr_raw = safe_float(h.get("current_price", bp))
            curr_inr = curr_raw if is_indian else round(curr_raw * rate, 2)

            pnl  = round((curr_inr - bp) * qty, 2)
            pnlp = round((curr_inr - bp) / bp * 100, 2) if bp else 0

            items.append({
                "symbol":    symbol,
                "quantity":  qty,
                "buy_price": round(bp, 2),
                "current":   curr_inr,
                "invested":  round(inv, 2),
                "value":     round(curr_inr * qty, 2),
                "pnl":       pnl,
                "pnl_pct":  pnlp,
                "market":    h.get("market", "IN" if is_indian else "US"),
            })
            total_inv += inv
            total_val += curr_inr * qty

        pnl_t  = round(total_val - total_inv, 2)
        pnlp_t = round(pnl_t / total_inv * 100, 2) if total_inv else 0

        return jsonify({
            "holdings":       items,
            "total_invested": round(total_inv, 2),
            "total_value":    round(total_val, 2),
            "total_pnl":      pnl_t,
            "total_pnl_pct":  pnlp_t,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/alerts")
def get_alerts():
    """Alerts from portfolio_store.json."""
    try:
        store  = load_store()
        alerts = store.get("alerts", [])[-20:]
        return jsonify([
            {
                "symbol":  a.get("symbol", ""),
                "type":    a.get("alert_type", a.get("type", "INFO")),
                "message": a.get("message", ""),
                "time":    str(a.get("created_at", a.get("time", "")))[:16],
            }
            for a in reversed(alerts)
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/history/<symbol>")
def get_history(symbol: str):
    """Price history + indicators for modal chart."""
    try:
        import yfinance as yf
        import ta as ta_lib
        import pandas as pd

        rate      = get_usd_inr()
        is_indian = ".NS" in symbol or ".BO" in symbol
        hist      = yf.Ticker(symbol).history(period="3mo")

        if hist.empty:
            return jsonify({"dates": [], "prices": [], "rsi": [],
                            "macd": [], "volume": [], "ema20": [], "ema50": []})

        close  = hist["Close"]
        volume = hist["Volume"]
        dates  = [str(d)[:10] for d in hist.index]

        mult   = 1 if is_indian else rate
        prices = [round(safe_float(p) * mult, 2) for p in close]
        vols   = [int(safe_float(v)) for v in volume]

        # RSI using ta library
        try:
            rsi_series = ta_lib.momentum.RSIIndicator(close, window=14).rsi()
            rsi = [round(safe_float(v), 1) if not pd.isna(v) else 50 for v in rsi_series]
        except Exception:
            rsi = [50] * len(dates)

        # MACD using ta library
        try:
            macd_ind = ta_lib.trend.MACD(close)
            macd_line = macd_ind.macd()
            macd = [round(safe_float(v), 4) if not pd.isna(v) else 0 for v in macd_line]
        except Exception:
            macd = [0] * len(dates)

        # EMA using ta library
        try:
            ema20_series = ta_lib.trend.EMAIndicator(close, window=20).ema_indicator()
            ema50_series = ta_lib.trend.EMAIndicator(close, window=50).ema_indicator()
            ema20 = [round(safe_float(v) * mult, 2) if not pd.isna(v) else None for v in ema20_series]
            ema50 = [round(safe_float(v) * mult, 2) if not pd.isna(v) else None for v in ema50_series]
        except Exception:
            ema20 = [None] * len(dates)
            ema50 = [None] * len(dates)

        return jsonify({
            "dates":  dates,
            "prices": prices,
            "rsi":    rsi,
            "macd":   macd,
            "volume": vols,
            "ema20":  ema20,
            "ema50":  ema50,
        })

    except Exception as e:
        return jsonify({"dates": [], "prices": [], "rsi": [],
                        "macd": [], "volume": [], "error": str(e)})


@app.route("/api/summary")
def get_summary():
    """BUY/SELL/HOLD count from decisions."""
    try:
        store = load_store()
        seen  = set()
        buy = sell = hold = 0
        conf_list = []

        for d in store.get("decisions", []):
            sym = d.get("symbol")
            if sym in seen:
                continue
            seen.add(sym)
            action = d.get("action", "HOLD")
            if action == "BUY":    buy  += 1
            elif action == "SELL": sell += 1
            else:                  hold += 1
            conf_list.append(safe_float(d.get("confidence", 0)))

        return jsonify({
            "buy":            buy,
            "sell":           sell,
            "hold":           hold,
            "avg_confidence": round(sum(conf_list) / len(conf_list), 1) if conf_list else 0,
            "total":          len(seen),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Options Chain ─────────────────────────────────────────────

_options_cache      = {}
_options_cache_time = {}
OPTIONS_CACHE_TTL   = 60

def _get_opt_cache(key):
    if key in _options_cache:
        if time.time() - _options_cache_time.get(key, 0) < OPTIONS_CACHE_TTL:
            return _options_cache[key]
    return None

def _set_opt_cache(key, data):
    _options_cache[key]      = data
    _options_cache_time[key] = time.time()


@app.route("/api/options")
@app.route("/api/options/<symbol>")
def get_options_chain(symbol: str = "NIFTY"):
    symbol  = symbol.upper()
    expiry  = request.args.get("expiry", None)
    refresh = request.args.get("refresh", "0") == "1"
    cache_key = f"{symbol}:{expiry or 'nearest'}"
    try:
        from options_fetcher import OptionsFetcher
        from options_engine  import OptionsEngine
        if not refresh:
            cached = _get_opt_cache(cache_key)
            if cached:
                cached["from_cache"] = True
                return jsonify(cached)
        chain    = OptionsFetcher.get_chain(symbol)
        analysis = OptionsEngine.analyze(chain, expiry=expiry)
        _set_opt_cache(cache_key, analysis)
        analysis["from_cache"] = False
        return jsonify(analysis)
    except Exception as e:
        logger.error(f"/api/options/{symbol}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/options/<symbol>/summary")
def get_options_summary(symbol: str = "NIFTY"):
    symbol = symbol.upper()
    try:
        from options_fetcher import OptionsFetcher
        from options_engine  import OptionsEngine
        cached = _get_opt_cache(f"{symbol}:nearest")
        if not cached:
            chain  = OptionsFetcher.get_chain(symbol)
            cached = OptionsEngine.analyze(chain)
            _set_opt_cache(f"{symbol}:nearest", cached)
        m = cached.get("metrics", {})
        return jsonify({
            "spot": cached.get("spot", 0), "expiry": cached.get("expiry", ""),
            "pcr_oi": m.get("pcr_oi", 0), "pcr_vol": m.get("pcr_vol", 0),
            "strong_ce": m.get("strong_ce", 0), "strong_pe": m.get("strong_pe", 0),
            "max_pain": cached.get("max_pain", 0),
            "bias": m.get("bias", ""), "bias_desc": m.get("bias_desc", ""),
            "hot_strikes": m.get("hot_strikes", []),
            "alerts_count": len(cached.get("alerts", [])),
            "source": cached.get("source", ""),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/options/<symbol>/alerts")
def get_options_alerts(symbol: str = "NIFTY"):
    symbol = symbol.upper()
    try:
        from options_fetcher import OptionsFetcher
        from options_engine  import OptionsEngine
        cached = _get_opt_cache(f"{symbol}:nearest")
        if not cached:
            chain  = OptionsFetcher.get_chain(symbol)
            cached = OptionsEngine.analyze(chain)
            _set_opt_cache(f"{symbol}:nearest", cached)
        return jsonify({"symbol": symbol, "alerts": cached.get("alerts", []),
                        "spot": cached.get("spot", 0), "source": cached.get("source", "")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/options/<symbol>/pcr")
def get_pcr(symbol: str = "NIFTY"):
    symbol = symbol.upper()
    try:
        from options_fetcher import OptionsFetcher
        from options_engine  import OptionsEngine
        chain    = OptionsFetcher.get_chain(symbol)
        expiries = chain.get("expiries", [])
        all_data = chain.get("data", {})
        spot     = chain.get("spot", 0)
        out = []
        for exp in expiries[:4]:
            sm = all_data.get(exp, {})
            if not sm: continue
            rows    = OptionsEngine._build_rows(sm, spot, 0)
            metrics = OptionsEngine._compute_metrics(rows, spot)
            out.append({"expiry": exp, "pcr_oi": metrics["pcr_oi"],
                        "pcr_vol": metrics["pcr_vol"], "bias": metrics["bias"]})
        return jsonify({"symbol": symbol, "spot": spot,
                        "pcr_by_expiry": out, "source": chain.get("source", "")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── entry point ───────────────────────────────────────────────

import os
if __name__ == "__main__":
    print("\n  Dashboard: http://localhost:5000")
    print("  APIs: /api/stocks  /api/portfolio  /api/alerts")
    print("        /api/options/NIFTY  /api/options/BANKNIFTY\n")
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)