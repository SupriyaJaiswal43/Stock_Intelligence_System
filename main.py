"""
Global Stock AI Agent
=====================
Run: python main.py

Commands:
  python main.py                  → Start agent (continuous mode)
  python main.py scan             → Run one manual scan
  python main.py portfolio        → Show portfolio
  python main.py analyze AAPL     → Analyze one stock
"""

import sys
import time
import logging

# Database removed
# from database import init_db

from scheduler import setup_scheduler
from ai_engine import AIEngine
from trader import Trader
from portfolio import PortfolioManager
from notifier import Notifier
from config import Config


# ──────────────────────────────────────────────────────
# Dummy DB Function (No Database Needed)
# ──────────────────────────────────────────────────────
def init_db():
    """Dummy database initializer."""
    pass


# ──────────────────────────────────────────────────────
# Logging Setup
# ──────────────────────────────────────────────────────
import io

# Force UTF-8 on Windows console so emojis don't crash the logger
_stream_handler = logging.StreamHandler(
    io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
)
_stream_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("agent.log", encoding="utf-8"),
        _stream_handler,
    ],
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────
# Main Agent Loop
# ──────────────────────────────────────────────────────
def run_agent():
    """Main AI Agent loop."""
    
    logger.info("=" * 60)
    logger.info("🚀 Global Stock AI Agent Starting...")
    logger.info(f"📄 PAPER MODE: {Config.PAPER_MODE}")
    logger.info(f"📋 Watchlist: {len(Config.WATCHLIST)} stocks")
    logger.info(f"⏱ Scan every: {Config.SCAN_INTERVAL_MINUTES} minutes")
    logger.info("=" * 60)

    # No DB but keeping function call safe
    init_db()

    # Telegram Notification
    try:
        Notifier._send_telegram(
            f"🤖 <b>Stock AI Agent Started</b>\n\n"
            f"📋 Watching {len(Config.WATCHLIST)} stocks\n"
            f"⏱ Scanning every {Config.SCAN_INTERVAL_MINUTES} minutes\n"
            f"📄 Paper Mode: {Config.PAPER_MODE}"
        )
    except Exception as e:
        logger.warning(f"Telegram notification failed: {e}")

    # Start Scheduler
    try:
        sched = setup_scheduler()
        logger.info("✅ Scheduler Started")
    except Exception as e:
        logger.error(f"Scheduler Error: {e}")
        return

    try:
        while True:
            time.sleep(60)

    except (KeyboardInterrupt, SystemExit):
        sched.shutdown()
        logger.info("🛑 Agent stopped by user.")


# ──────────────────────────────────────────────────────
# Manual Scan
# ──────────────────────────────────────────────────────
def run_manual_scan():
    """Run one-time scan of all watchlist stocks."""

    init_db()

    results = []

    print("\n" + "=" * 60)
    print(f"📊 Scanning {len(Config.WATCHLIST)} Stocks")
    print("=" * 60 + "\n")

    for symbol in Config.WATCHLIST:

        try:
            result = AIEngine.analyze_stock(symbol)

            if not result:
                continue

            results.append(result)

            action = result.get("action", "HOLD")
            confidence = result.get("confidence", 0)
            price = result.get("current_price", 0)

            indicator = (
                "🟢" if action == "BUY"
                else "🔴" if action == "SELL"
                else "🟡"
            )

            print(
                f"{indicator} "
                f"{symbol:15s} | "
                f"{action:5s} | "
                f"Confidence: {confidence}% | "
                f"Price: {price}"
            )

        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")

    print("\n✅ Scan Completed\n")

    try:
        Notifier.send_daily_summary(results)
    except Exception as e:
        logger.warning(f"Summary notification failed: {e}")


# ──────────────────────────────────────────────────────
# Analyze Single Stock
# ──────────────────────────────────────────────────────
def analyze_single(symbol: str):
    """Analyze a single stock."""

    init_db()

    print("\n" + "=" * 60)
    print(f"📈 Analyzing {symbol}")
    print("=" * 60 + "\n")

    try:
        result = AIEngine.analyze_stock(symbol)

        if not result:
            print("❌ No analysis result found.")
            return

        print(f"📌 Symbol      : {result.get('symbol')}")
        print(f"📌 Action      : {result.get('action')}")
        print(f"📌 Confidence  : {result.get('confidence')}%")
        print(f"📌 Price       : {result.get('current_price', 0)}")
        print(f"📌 Tech Score  : {result.get('technical_score', 0)}")

        print("\n🧠 Reason:\n")
        print(result.get("reason", "No reason available."))

        indicators = result.get("indicators", {})

        if indicators:
            print("\n📊 Indicators:\n")

            for key, value in indicators.items():
                print(f"  {key}: {value}")

        print("\n✅ Analysis Complete\n")

    except Exception as e:
        logger.error(f"Analysis failed for {symbol}: {e}")


# ──────────────────────────────────────────────────────
# Main Entry
# ──────────────────────────────────────────────────────
if __name__ == "__main__":

    args = sys.argv[1:]

    if not args:
        run_agent()

    elif args[0] == "scan":
        run_manual_scan()

    elif args[0] == "portfolio":
        try:
            PortfolioManager.print_portfolio()
        except Exception as e:
            logger.error(f"Portfolio Error: {e}")

    elif args[0] == "analyze" and len(args) > 1:
        analyze_single(args[1].upper())

    elif args[0] == "health":
        try:
            PortfolioManager.generate_health_report()
        except Exception as e:
            logger.error(f"Health Report Error: {e}")

    else:
        print(__doc__)