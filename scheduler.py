from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config import Config
from ai_engine import AIEngine
from trader import Trader
from notifier import Notifier

import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="Asia/Kolkata")


# ─────────────────────────────────────────────
# Scan Stocks & Execute Decisions
# ─────────────────────────────────────────────
def scan_and_decide():

    logger.info("[Scheduler] Starting market scan...")

    results = []

    for symbol in Config.WATCHLIST:

        try:
            result = AIEngine.analyze_stock(symbol)

            if not result:
                continue

            results.append(result)

            action = result.get("action")
            confidence = result.get("confidence", 0)

            # BUY
            if (
                action == "BUY"
                and confidence >= Config.BUY_CONFIDENCE_THRESHOLD
            ):

                Trader.buy_stock(
                    symbol,
                    Config.MAX_INVESTMENT_PER_STOCK,
                    result
                )

            # SELL
            elif action == "SELL":

                portfolio = Trader.get_portfolio_value()

                holding_symbols = [
                    h["symbol"] for h in portfolio["holdings"]
                ]

                if symbol in holding_symbols:

                    Trader.sell_stock(
                        symbol,
                        result.get("reason", "AI signal")
                    )

        except Exception as e:
            logger.error(f"[Scheduler] Error for {symbol}: {e}")

    try:
        Notifier.send_daily_summary(results)
    except Exception as e:
        logger.warning(f"Notification Error: {e}")

    logger.info(
        f"[Scheduler] Scan completed. "
        f"{len(results)} stocks analyzed."
    )


# ─────────────────────────────────────────────
# Portfolio Check
# ─────────────────────────────────────────────
def check_portfolio_pnl():

    try:

        portfolio = Trader.get_portfolio_value()

        for holding in portfolio["holdings"]:

            if holding["pnl_pct"] <= Config.SELL_THRESHOLD:

                Notifier.send_warning(
                    holding["symbol"],
                    (
                        f"Stock dropped "
                        f"{holding['pnl_pct']:.1f}% "
                        f"from buy price."
                    )
                )

    except Exception as e:
        logger.error(f"P&L Check Error: {e}")


# ─────────────────────────────────────────────
# Daily Portfolio Report
# ─────────────────────────────────────────────
def send_portfolio_report():

    try:

        portfolio = Trader.get_portfolio_value()

        Notifier.send_portfolio_update(portfolio)

    except Exception as e:
        logger.error(f"Portfolio Report Error: {e}")


# ─────────────────────────────────────────────
# Setup Scheduler
# ─────────────────────────────────────────────
def setup_scheduler():

    # Market Scan
    scheduler.add_job(
        scan_and_decide,
        IntervalTrigger(
            minutes=Config.SCAN_INTERVAL_MINUTES
        ),
        id="market_scan",
        name="Market Scan",
        replace_existing=True,
    )

    # Portfolio P&L Check
    scheduler.add_job(
        check_portfolio_pnl,
        IntervalTrigger(minutes=30),
        id="pnl_check",
        name="PnL Check",
        replace_existing=True,
    )

    # Daily Report
    scheduler.add_job(
        send_portfolio_report,
        CronTrigger(
            hour=16,
            minute=0,
            timezone="Asia/Kolkata"
        ),
        id="daily_report",
        name="Daily Report",
        replace_existing=True,
    )

    scheduler.start()

    logger.info("[Scheduler] All jobs started.")

    return scheduler