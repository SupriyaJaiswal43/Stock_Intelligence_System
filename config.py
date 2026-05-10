# import os
# from dotenv import load_dotenv

# load_dotenv()

# class Config:
#     # Market Data
#     ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")
#     TWELVE_DATA_KEY = os.getenv("TWELVE_DATA_KEY")
#     FINNHUB_KEY = os.getenv("FINNHUB_KEY")

#     # News
#     NEWS_API_KEY = os.getenv("NEWS_API_KEY")
#     GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
#     MARKETAUX_KEY = os.getenv("MARKETAUX_KEY")

#     # AI
#     OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
#     GROQ_API_KEY = os.getenv("GROQ_API_KEY")

#     # Telegram
#     TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
#     TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

#     # Trading
#     UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY")
#     UPSTOX_SECRET = os.getenv("UPSTOX_SECRET")
#     ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
#     ALPACA_SECRET = os.getenv("ALPACA_SECRET")
#     ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

#     # Database
#     DATABASE_URL = os.getenv("DATABASE_URL")
#     REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

#     # Settings
#     PAPER_MODE = os.getenv("PAPER_MODE", "true").lower() == "true"
#     SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL_MINUTES", 15))
#     MAX_INVESTMENT_PER_STOCK = float(os.getenv("MAX_INVESTMENT_PER_STOCK", 1000))
#     SELL_THRESHOLD = float(os.getenv("SELL_THRESHOLD", -5))
#     BUY_CONFIDENCE_THRESHOLD = float(os.getenv("BUY_CONFIDENCE_THRESHOLD", 75))

#     # Global watchlist — Indian + US stocks
#     WATCHLIST = [
#         # Indian Stocks (NSE)
#         "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
#         "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "WIPRO.NS", "KOTAKBANK.NS",
#         "LT.NS", "AXISBANK.NS", "MARUTI.NS", "ASIANPAINT.NS", "TITAN.NS",
#         # US Stocks
#         "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
#         "TSLA", "META", "NFLX", "AMD", "INTC",
#         # Global ETFs
#         "SPY", "QQQ", "GLD", "VTI"
#     ]

#     WATCHLIST = [
#         # Indian Large Cap
#         "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
#         "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "WIPRO.NS", "KOTAKBANK.NS",
#         "LT.NS", "AXISBANK.NS", "MARUTI.NS", "ASIANPAINT.NS", "TITAN.NS",
#         "BAJFINANCE.NS", "HCLTECH.NS", "SUNPHARMA.NS", "ULTRACEMCO.NS", "NESTLEIND.NS",
#         "POWERGRID.NS", "NTPC.NS", "ONGC.NS", "TATAMOTORS.NS", "ADANIENT.NS",
#         # US Tech
#         "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
#         "TSLA", "META", "NFLX", "AMD", "INTC",
#         "ORCL", "CRM", "ADBE", "QCOM", "AVGO",
#         # US Finance & Others
#         "JPM", "BAC", "GS", "V", "MA",
#         "WMT", "COST", "PG", "JNJ", "UNH",
#         # Global ETFs
#         "SPY", "QQQ", "GLD", "VTI", "EEM",
#     ]
    






import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Market Data
    ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")
    TWELVE_DATA_KEY = os.getenv("TWELVE_DATA_KEY")
    FINNHUB_KEY = os.getenv("FINNHUB_KEY")

    # News
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
    GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
    MARKETAUX_KEY = os.getenv("MARKETAUX_KEY")

    # AI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    # Trading
    UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY")
    UPSTOX_SECRET = os.getenv("UPSTOX_SECRET")
    ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
    ALPACA_SECRET = os.getenv("ALPACA_SECRET")
    ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Settings
    PAPER_MODE = os.getenv("PAPER_MODE", "true").lower() == "true"
    SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL_MINUTES", 15))
    MAX_INVESTMENT_PER_STOCK = float(os.getenv("MAX_INVESTMENT_PER_STOCK", 1000))
    SELL_THRESHOLD = float(os.getenv("SELL_THRESHOLD", -5))
    BUY_CONFIDENCE_THRESHOLD = float(os.getenv("BUY_CONFIDENCE_THRESHOLD", 75))

    WATCHLIST = [
        # Indian Large Cap (NSE)
        "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
        "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "WIPRO.NS", "KOTAKBANK.NS",
        "LT.NS", "AXISBANK.NS", "MARUTI.NS", "ASIANPAINT.NS", "TITAN.NS",
        "BAJFINANCE.NS", "HCLTECH.NS", "SUNPHARMA.NS", "ULTRACEMCO.NS", "NESTLEIND.NS",
        "POWERGRID.NS", "NTPC.NS", "ONGC.NS", "TATAMOTORS.NS", "ADANIENT.NS",
        "TECHM.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "BAJAJFINSV.NS",
        "HINDALCO.NS", "JSWSTEEL.NS", "TATASTEEL.NS", "COALINDIA.NS", "VEDL.NS",
        "GRASIM.NS", "BRITANNIA.NS", "DABUR.NS", "MARICO.NS", "GODREJCP.NS",
        "PIDILITIND.NS", "BERGEPAINT.NS", "HAVELLS.NS", "VOLTAS.NS", "WHIRLPOOL.NS",
        "INDUSINDBK.NS", "BANDHANBNK.NS", "FEDERALBNK.NS", "IDFCFIRSTB.NS", "PNB.NS",
        "BANKBARODA.NS", "CANBK.NS", "UNIONBANK.NS", "INDIANB.NS", "MAHABANK.NS",
        "HDFCLIFE.NS", "SBILIFE.NS", "ICICIGI.NS", "LICI.NS", "NIACL.NS",
        "ITC.NS", "TATACONSUM.NS", "VBL.NS", "UBL.NS", "MCDOWELL-N.NS",
        "ZOMATO.NS", "NYKAA.NS", "PAYTM.NS", "POLICYBZR.NS", "DELHIVERY.NS",
        "IRCTC.NS", "IRFC.NS", "RVNL.NS", "RAILVIKAS.NS", "CONCOR.NS",
        "ADANIPORTS.NS", "ADANIGREEN.NS", "ADANITRANS.NS", "ADANIPOWER.NS", "AWL.NS",
        "TATAPOWER.NS", "TORNTPOWER.NS", "CESC.NS", "JSPL.NS", "SAIL.NS",
        "APOLLOHOSP.NS", "MAXHEALTH.NS", "FORTIS.NS", "NARAYANHC.NS", "METROPOLIS.NS",
        "PERSISTENT.NS", "MPHASIS.NS", "LTIM.NS", "COFORGE.NS", "OFSS.NS",

        # US Tech
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
        "TSLA", "META", "NFLX", "AMD", "INTC",
        "ORCL", "CRM", "ADBE", "QCOM", "AVGO",
        "UBER", "LYFT", "SNAP", "PINS", "TWTR",
        "PLTR", "SNOW", "NET", "DDOG", "ZS",

        # US Finance
        "JPM", "BAC", "GS", "V", "MA",
        "WMT", "COST", "PG", "JNJ", "UNH",
        "MS", "WFC", "C", "AXP", "BLK",

        # Global ETFs
        "SPY", "QQQ", "GLD", "VTI", "EEM",
    ]
    