from database import Portfolio, AIDecision, SessionLocal
from data_fetcher import DataFetcher
from ai_engine import AIEngine
from notifier import Notifier
import logging

logger = logging.getLogger(__name__)


class PortfolioManager:

    @staticmethod
    def get_full_portfolio() -> dict:
        db = SessionLocal()
        holdings = db.query(Portfolio).filter_by(is_active=True).all()
        db.close()

        items = []
        total_invested = 0
        total_value = 0

        for h in holdings:
            current = DataFetcher.get_current_price(h.symbol)
            pnl = (current - h.buy_price) * h.quantity
            pnl_pct = (
                (current - h.buy_price) / h.buy_price * 100
                if h.buy_price > 0 else 0
            )
            items.append({
                "symbol": h.symbol,
                "quantity": h.quantity,
                "buy_price": h.buy_price,
                "current_price": current,
                "invested_amount": h.invested_amount,
                "current_value": current * h.quantity,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "market": h.market,
                "bought_at": str(h.bought_at),
            })
            total_invested += h.invested_amount
            total_value += current * h.quantity

        return {
            "holdings": items,
            "total_invested": round(total_invested, 2),
            "total_value": round(total_value, 2),
            "total_pnl": round(total_value - total_invested, 2),
            "total_pnl_pct": round(
                (total_value - total_invested) / total_invested * 100
                if total_invested > 0 else 0,
                2,
            ),
            "count": len(items),
        }

    @staticmethod
    def get_ai_decision_history(limit: int = 20) -> list:
        db = SessionLocal()
        decisions = (
            db.query(AIDecision)
            .order_by(AIDecision.created_at)   # _Query handles desc internally
            .limit(limit)
            .all()
        )
        db.close()
        return [
            {
                "symbol": d.symbol,
                "action": d.action,
                "confidence": d.confidence,
                "reason": d.reason,
                "price": d.price_at_decision,
                "technical_score": d.technical_score,
                "created_at": str(d.created_at),
            }
            for d in decisions
        ]

    @staticmethod
    def generate_health_report():
        portfolio = PortfolioManager.get_full_portfolio()
        if not portfolio["holdings"]:
            Notifier._send_telegram(
                "📭 Portfolio is empty. No holdings yet."
            )
            return

        health = AIEngine.analyze_portfolio_health(portfolio["holdings"])
        Notifier.send_portfolio_update(portfolio)
        Notifier._send_telegram(
            f"🤖 <b>AI Health Assessment:</b>\n{health}"
        )

    @staticmethod
    def print_portfolio():
        p = PortfolioManager.get_full_portfolio()
        print("\n" + "=" * 50)
        print(f"  PORTFOLIO SUMMARY ({p['count']} holdings)")
        print("=" * 50)
        for h in p["holdings"]:
            sign = "+" if h["pnl_pct"] >= 0 else ""
            print(
                f"  {h['symbol']:20s} | Qty: {h['quantity']:8.2f} | "
                f"P&L: {sign}{h['pnl_pct']:.1f}% ({sign}{h['pnl']:.0f})"
            )
        print("-" * 50)
        print(f"  Total Invested : {p['total_invested']}")
        print(f"  Current Value  : {p['total_value']}")
        sign = "+" if p["total_pnl"] >= 0 else ""
        print(
            f"  Total P&L      : {sign}{p['total_pnl']} "
            f"({sign}{p['total_pnl_pct']:.1f}%)"
        )
        print("=" * 50 + "\n")