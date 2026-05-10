
import yfinance as yf
import requests
import finnhub
import pandas as pd
from twelvedata import TDClient
from config import Config
import logging


# ─────────────────────────────────────────────
# Dummy Cache Functions (No Database Needed)
# ─────────────────────────────────────────────
def cache_get(key):
    return None


def cache_set(key, value, ttl=300):
    pass


# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# API Clients
# ─────────────────────────────────────────────
finnhub_client = finnhub.Client(
    api_key=Config.FINNHUB_KEY
)

td_client = TDClient(
    apikey=Config.TWELVE_DATA_KEY
)


# ─────────────────────────────────────────────
# Data Fetcher Class
# ─────────────────────────────────────────────
class DataFetcher:

    @staticmethod
    def get_stock_data(
        symbol: str,
        period: str = "3mo"
    ) -> pd.DataFrame:
        """
        Fetch OHLCV stock data.

        Priority:
        1. yfinance
        2. Twelve Data
        3. Alpha Vantage
        """

        cache_key = f"stock:{symbol}:{period}"

        cached = cache_get(cache_key)

        if cached:
            return pd.DataFrame(cached)

        # ─────────────────────────
        # 1️⃣ Yahoo Finance
        # ─────────────────────────
        try:

            ticker = yf.Ticker(symbol)

            df = ticker.history(period=period)

            if not df.empty:

                cache_set(
                    cache_key,
                    df.reset_index().to_dict("records"),
                    ttl=300
                )

                logger.info(
                    f"[yfinance] {symbol} data fetched"
                )

                return df

        except Exception as e:

            logger.warning(
                f"[yfinance] {symbol} failed: {e}"
            )

        # ─────────────────────────
        # 2️⃣ Twelve Data
        # ─────────────────────────
        try:

            ts = td_client.time_series(
                symbol=symbol,
                interval="1day",
                outputsize=90
            )

            df = ts.as_pandas()

            if not df.empty:

                cache_set(
                    cache_key,
                    df.reset_index().to_dict("records"),
                    ttl=300
                )

                logger.info(
                    f"[TwelveData] {symbol} data fetched"
                )

                return df

        except Exception as e:

            logger.warning(
                f"[TwelveData] {symbol} failed: {e}"
            )

        # ─────────────────────────
        # 3️⃣ Alpha Vantage
        # ─────────────────────────
        try:

            url = (
                "https://www.alphavantage.co/query"
                f"?function=TIME_SERIES_DAILY"
                f"&symbol={symbol}"
                f"&outputsize=compact"
                f"&apikey={Config.ALPHA_VANTAGE_KEY}"
            )

            response = requests.get(
                url,
                timeout=10
            )

            data = response.json()

            ts_data = data.get(
                "Time Series (Daily)",
                {}
            )

            if ts_data:

                rows = []

                for date, values in list(ts_data.items())[:90]:

                    rows.append({
                        "Date": date,
                        "Open": float(values["1. open"]),
                        "High": float(values["2. high"]),
                        "Low": float(values["3. low"]),
                        "Close": float(values["4. close"]),
                        "Volume": float(values["5. volume"]),
                    })

                df = pd.DataFrame(rows)

                df.set_index("Date", inplace=True)

                cache_set(
                    cache_key,
                    df.reset_index().to_dict("records"),
                    ttl=300
                )

                logger.info(
                    f"[AlphaVantage] {symbol} data fetched"
                )

                return df

        except Exception as e:

            logger.warning(
                f"[AlphaVantage] {symbol} failed: {e}"
            )

        logger.error(
            f"All data sources failed for {symbol}"
        )

        return pd.DataFrame()

    # ─────────────────────────────────────────
    # Current Price
    # ─────────────────────────────────────────
    @staticmethod
    def get_current_price(symbol: str) -> float:

        # Finnhub First
        try:

            quote = finnhub_client.quote(symbol)

            if quote and quote.get("c", 0) > 0:

                return float(quote["c"])

        except Exception as e:

            logger.warning(
                f"[Finnhub] price {symbol}: {e}"
            )

        # Yahoo Finance Fallback
        try:

            ticker = yf.Ticker(symbol)

            info = ticker.fast_info

            return float(info.last_price)

        except Exception as e:

            logger.warning(
                f"[yfinance] price {symbol}: {e}"
            )

        return 0.0

    # ─────────────────────────────────────────
    # Company Info
    # ─────────────────────────────────────────
    @staticmethod
    def get_company_info(symbol: str) -> dict:

        try:

            ticker = yf.Ticker(symbol)

            info = ticker.info

            return {
                "name": info.get("longName", symbol),
                "sector": info.get("sector", "Unknown"),
                "industry": info.get("industry", "Unknown"),
                "market_cap": info.get("marketCap", 0),
                "country": info.get("country", "Unknown"),
            }

        except Exception:

            return {
                "name": symbol,
                "sector": "Unknown",
                "industry": "Unknown",
                "market_cap": 0,
                "country": "Unknown",
            }

    # ─────────────────────────────────────────
    # Bulk Prices
    # ─────────────────────────────────────────
    @staticmethod
    def get_bulk_prices(symbols: list) -> dict:

        prices = {}

        for symbol in symbols:

            prices[symbol] = (
                DataFetcher.get_current_price(symbol)
            )

        return prices

