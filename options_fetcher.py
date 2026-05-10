"""
options_fetcher.py
==================
NSE se live Nifty 50 options chain data fetch karta hai.
NSE ke liye pehle ek session banana padta hai (cookies ke liye),
tabhi options API response deta hai.

Usage:
    from options_fetcher import OptionsFetcher
    data = OptionsFetcher.get_chain("NIFTY")
"""

import requests
import logging
import time

logger = logging.getLogger(__name__)

# ── NSE headers (browser jaisa dikhne ke liye) ───────────────
NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/option-chain",
    "X-Requested-With": "XMLHttpRequest",
    "Connection": "keep-alive",
}

# In-memory session cache (restart pe reset hoga)
_session = None
_session_time = 0
SESSION_TTL = 300  # 5 minutes


def _get_session() -> requests.Session:
    """NSE ke liye valid session banao (cookies required)."""
    global _session, _session_time

    now = time.time()
    if _session and (now - _session_time) < SESSION_TTL:
        return _session

    s = requests.Session()
    s.headers.update(NSE_HEADERS)

    try:
        # Pehle NSE homepage hit karo — cookies milenge
        s.get("https://www.nseindia.com", timeout=10)
        time.sleep(1)
        # Option chain page bhi hit karo
        s.get("https://www.nseindia.com/option-chain", timeout=10)
        time.sleep(0.5)
    except Exception as e:
        logger.warning(f"[OptionsFetcher] Session warm-up failed: {e}")

    _session = s
    _session_time = now
    logger.info("[OptionsFetcher] New NSE session created")
    return s


class OptionsFetcher:

    @staticmethod
    def get_chain(symbol: str = "NIFTY") -> dict:
        """
        NSE se live options chain fetch karo.

        Returns:
            {
                "spot": float,
                "expiries": [str, ...],
                "data": {
                    expiry: {
                        strike: {
                            "ce": {oi, chgOI, vol, ltp, iv, delta},
                            "pe": {oi, chgOI, vol, ltp, iv, delta}
                        }
                    }
                },
                "timestamp": str,
                "source": "nse" | "fallback"
            }
        """
        url = (
            f"https://www.nseindia.com/api/option-chain-indices"
            f"?symbol={symbol.upper()}"
        )

        # Real NSE data try karo
        try:
            s = _get_session()
            resp = s.get(url, timeout=15)
            resp.raise_for_status()
            raw = resp.json()

            if "records" not in raw:
                raise ValueError("Invalid NSE response structure")

            parsed = OptionsFetcher._parse_nse(raw)
            parsed["source"] = "nse"
            logger.info(
                f"[OptionsFetcher] {symbol} live data fetched: "
                f"{len(parsed['expiries'])} expiries"
            )
            return parsed

        except Exception as e:
            logger.warning(
                f"[OptionsFetcher] NSE fetch failed ({e}), "
                f"using fallback data"
            )
            return OptionsFetcher._fallback_data(symbol)

    @staticmethod
    def _parse_nse(raw: dict) -> dict:
        """NSE JSON ko clean structure mein convert karo."""
        records = raw["records"]
        spot    = float(records.get("underlyingValue", 0))
        expiries = records.get("expiryDates", [])
        rows     = records.get("data", [])

        data = {}
        for row in rows:
            expiry = row.get("expiryDate", "")
            strike = row.get("strikePrice", 0)

            if expiry not in data:
                data[expiry] = {}

            chain_row = {"ce": {}, "pe": {}}

            if "CE" in row and row["CE"]:
                ce = row["CE"]
                chain_row["ce"] = {
                    "oi":    int(ce.get("openInterest", 0) or 0),
                    "chgOI": int(ce.get("changeinOpenInterest", 0) or 0),
                    "vol":   int(ce.get("totalTradedVolume", 0) or 0),
                    "ltp":   float(ce.get("lastPrice", 0) or 0),
                    "iv":    float(ce.get("impliedVolatility", 0) or 0),
                    "bid":   float(ce.get("bidPrice", 0) or 0),
                    "ask":   float(ce.get("askPrice", 0) or 0),
                }

            if "PE" in row and row["PE"]:
                pe = row["PE"]
                chain_row["pe"] = {
                    "oi":    int(pe.get("openInterest", 0) or 0),
                    "chgOI": int(pe.get("changeinOpenInterest", 0) or 0),
                    "vol":   int(pe.get("totalTradedVolume", 0) or 0),
                    "ltp":   float(pe.get("lastPrice", 0) or 0),
                    "iv":    float(pe.get("impliedVolatility", 0) or 0),
                    "bid":   float(pe.get("bidPrice", 0) or 0),
                    "ask":   float(pe.get("askPrice", 0) or 0),
                }

            data[expiry][strike] = chain_row

        from datetime import datetime
        return {
            "spot":      spot,
            "expiries":  expiries,
            "data":      data,
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def _fallback_data(symbol: str) -> dict:
        """
        NSE block kare to realistic simulated data return karo.
        Ye sirf development/testing ke liye hai.
        """
        import random
        from datetime import datetime, timedelta

        random.seed(42)  # Consistent demo data

        # Approximate spot prices
        spots = {
            "NIFTY":     24500,
            "BANKNIFTY": 52000,
            "FINNIFTY":  23500,
            "MIDCPNIFTY": 12000,
        }
        spot = spots.get(symbol.upper(), 24500)
        spot += random.randint(-300, 300)

        # Expiries (next 3 Thursdays)
        today = datetime.now()
        expiries = []
        d = today
        for _ in range(21):
            d += timedelta(days=1)
            if d.weekday() == 3:  # Thursday
                expiries.append(d.strftime("%d-%b-%Y"))
                if len(expiries) == 3:
                    break

        # Strike range: spot ± 3000 in steps of 50 (NIFTY)
        step = 50 if symbol.upper() == "NIFTY" else 100
        strikes = range(
            int(spot // step) * step - 3000,
            int(spot // step) * step + 3050,
            step
        )

        data = {}
        for expiry in expiries:
            data[expiry] = {}
            for s in strikes:
                dist = abs(s - spot)
                atm_factor = max(0.05, 1 - dist / 4000)
                base_oi = int(atm_factor * 600000 * (0.6 + random.random() * 0.8))

                # CE: higher OI above spot (sellers write OTM calls)
                ce_oi = int(base_oi * (1.3 if s > spot else 0.5))
                # PE: higher OI below spot (sellers write OTM puts)
                pe_oi = int(base_oi * (1.3 if s < spot else 0.5))

                # Hot zones: inject extra OI near round numbers
                for hot in [
                    round(spot / 500) * 500,
                    round(spot / 500) * 500 + 500,
                    round(spot / 500) * 500 - 500,
                ]:
                    if abs(s - hot) <= step:
                        ce_oi = int(ce_oi * 2.5)
                        pe_oi = int(pe_oi * 2.5)

                ce_chg = int((random.random() - 0.35) * ce_oi * 0.2)
                pe_chg = int((random.random() - 0.35) * pe_oi * 0.2)
                ce_ltp = max(0.5, (spot - s + 300 + random.random() * 80) * 0.85)
                pe_ltp = max(0.5, (s - spot + 300 + random.random() * 80) * 0.85)
                ce_iv  = round(12 + dist / 200 + random.random() * 5, 1)
                pe_iv  = round(13 + dist / 200 + random.random() * 5, 1)

                data[expiry][s] = {
                    "ce": {
                        "oi": ce_oi, "chgOI": ce_chg,
                        "vol": int(ce_oi * (0.06 + random.random() * 0.12)),
                        "ltp": round(ce_ltp, 2),
                        "iv": ce_iv, "bid": round(ce_ltp * 0.98, 2),
                        "ask": round(ce_ltp * 1.02, 2),
                    },
                    "pe": {
                        "oi": pe_oi, "chgOI": pe_chg,
                        "vol": int(pe_oi * (0.06 + random.random() * 0.12)),
                        "ltp": round(pe_ltp, 2),
                        "iv": pe_iv, "bid": round(pe_ltp * 0.98, 2),
                        "ask": round(pe_ltp * 1.02, 2),
                    },
                }

        return {
            "spot":      float(spot),
            "expiries":  expiries,
            "data":      data,
            "timestamp": datetime.now().isoformat(),
            "source":    "fallback",
        }