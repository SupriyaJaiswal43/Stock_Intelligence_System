import requests
from config import Config
from database import Alert, SessionLocal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Notifier:

    @staticmethod
    def _send_telegram(message: str) -> bool:
        try:
            url = (
                f"https://api.telegram.org/bot"
                f"{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
            )
            payload = {
                "chat_id": Config.TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
            }
            res = requests.post(url, json=payload, timeout=10)
            return res.status_code == 200
        except Exception as e:
            logger.error(f"[Telegram] Send failed: {e}")
            return False

    @staticmethod
    def _save_alert(symbol: str, message: str, alert_type: str):
        try:
            db = SessionLocal()
            db.add(Alert(
                symbol=symbol,
                message=message,
                alert_type=alert_type,
            ))
            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"[Store] Alert save failed: {e}")

    @staticmethod
    def send_trade_alert(
        symbol: str,
        action: str,
        price: float,
        quantity: float,
        reason: str,
        confidence: float,
    ):
        emoji = "🟢" if action == "BUY" else "🔴"
        mode = "📄 PAPER" if Config.PAPER_MODE else "💰 REAL"
        message = (
            f"{emoji} <b>{action} EXECUTED</b> {mode}\n\n"
            f"📊 <b>Stock:</b> {symbol}\n"
            f"💵 <b>Price:</b> {price}\n"
            f"📦 <b>Quantity:</b> {quantity}\n"
            f"🤖 <b>AI Confidence:</b> {confidence}%\n\n"
            f"📝 <b>Reason:</b>\n{reason}"
        )
        Notifier._send_telegram(message)
        Notifier._save_alert(symbol, message, action)

    @staticmethod
    def send_sell_alert(symbol: str, price: float, reason: str):
        message = (
            f"🔴 <b>SELL ALERT</b>\n\n"
            f"📊 <b>Stock:</b> {symbol}\n"
            f"💵 <b>Current Price:</b> {price}\n\n"
            f"⚠️ <b>Reason:</b>\n{reason}"
        )
        Notifier._send_telegram(message)
        Notifier._save_alert(symbol, message, "SELL")

    @staticmethod
    def send_portfolio_update(portfolio: dict):
        pnl = portfolio["total_pnl"]
        pnl_pct = portfolio["total_pnl_pct"]
        emoji = "📈" if pnl >= 0 else "📉"
        pnl_emoji = "✅" if pnl >= 0 else "❌"

        holdings_text = ""
        for h in portfolio["holdings"][:10]:
            h_emoji = "🟢" if h["pnl_pct"] >= 0 else "🔴"
            holdings_text += (
                f"{h_emoji} {h['symbol']}: {h['pnl_pct']:+.1f}% "
                f"(P&L: {h['pnl']:+.0f})\n"
            )

        message = (
            f"{emoji} <b>PORTFOLIO UPDATE</b>\n\n"
            f"💰 <b>Invested:</b> {portfolio['total_invested']}\n"
            f"📊 <b>Current Value:</b> {portfolio['total_current_value']}\n"
            f"{pnl_emoji} <b>Total P&L:</b> {pnl:+.2f} ({pnl_pct:+.1f}%)\n\n"
            f"<b>Holdings:</b>\n{holdings_text}"
        )
        Notifier._send_telegram(message)

    @staticmethod
    def send_warning(symbol: str, message: str):
        full_msg = f"⚠️ <b>WARNING: {symbol}</b>\n\n{message}"
        Notifier._send_telegram(full_msg)
        Notifier._save_alert(symbol, message, "WARNING")

    @staticmethod
    def send_daily_summary(scan_results: list):
        buy_list = [r for r in scan_results if r["action"] == "BUY"]
        sell_list = [r for r in scan_results if r["action"] == "SELL"]

        buy_text = "\n".join([
            f"🟢 {r['symbol']} ({r['confidence']:.0f}%)"
            for r in buy_list[:5]
        ]) or "None"

        sell_text = "\n".join([
            f"🔴 {r['symbol']} ({r['confidence']:.0f}%)"
            for r in sell_list[:5]
        ]) or "None"

        message = (
            f"📊 <b>DAILY SCAN SUMMARY</b>\n"
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"<b>BUY Signals ({len(buy_list)}):</b>\n{buy_text}\n\n"
            f"<b>SELL Signals ({len(sell_list)}):</b>\n{sell_text}\n\n"
            f"<b>Scanned:</b> {len(scan_results)} stocks"
        )
        Notifier._send_telegram(message)