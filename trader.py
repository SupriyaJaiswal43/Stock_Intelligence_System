import alpaca_trade_api as tradeapi
from config import Config
from database import Portfolio, SessionLocal
from notifier import Notifier
import logging

logger = logging.getLogger(__name__)

# Alpaca client (US stocks)
alpaca = tradeapi.REST(
    Config.ALPACA_API_KEY,
    Config.ALPACA_SECRET,
    Config.ALPACA_BASE_URL,
    api_version="v2"
)


class Trader:

    @staticmethod
    def _is_indian_stock(symbol: str) -> bool:
        return symbol.endswith(".NS") or symbol.endswith(".BO")

    @staticmethod
    def buy_stock(symbol: str, amount: float, ai_result: dict) -> bool:
        """Execute a BUY order. amount = INR/USD to invest (not quantity)."""
        price = ai_result.get("current_price", 0)
        if price <= 0:
            logger.error(f"[TRADE] Invalid price for {symbol}")
            return False

        quantity = round(amount / price, 4)
        if quantity <= 0:
            return False

        logger.info(
            f"[TRADE] BUY {quantity} x {symbol} @ {price} "
            f"(PAPER={Config.PAPER_MODE})"
        )

        success = False

        if Trader._is_indian_stock(symbol):
            success = Trader._buy_upstox(symbol, quantity, price)
        else:
            success = Trader._buy_alpaca(symbol, quantity)

        if success:
            db = SessionLocal()
            db.add(Portfolio(
                symbol=symbol,
                quantity=quantity,
                buy_price=price,
                current_price=price,
                invested_amount=amount,
                market="IN" if Trader._is_indian_stock(symbol) else "US",
            ))
            db.commit()
            db.close()

            Notifier.send_trade_alert(
                symbol, "BUY", price, quantity,
                ai_result.get("reason", ""),
                ai_result.get("confidence", 0),
            )
            logger.info(f"[TRADE] BUY success: {symbol}")

        return success

    @staticmethod
    def sell_stock(symbol: str, reason: str = "") -> bool:
        """Sell all active holdings of a stock."""
        db = SessionLocal()
        holdings = db.query(Portfolio).filter_by(
            symbol=symbol, is_active=True
        ).all()

        if not holdings:
            db.close()
            logger.warning(f"[TRADE] No holdings found for {symbol}")
            return False

        total_qty = sum(h.quantity for h in holdings)
        current_price = holdings[0].current_price

        success = False
        if Trader._is_indian_stock(symbol):
            success = Trader._sell_upstox(symbol, total_qty, current_price)
        else:
            success = Trader._sell_alpaca(symbol, total_qty)

        if success:
            # Mark all matching rows inactive and persist
            store = db._data
            for row in store["portfolio"]:
                if row["symbol"] == symbol and row.get("is_active"):
                    row["is_active"] = False
            db.commit()
            Notifier.send_sell_alert(symbol, current_price, reason)
            logger.info(f"[TRADE] SELL success: {symbol}")

        db.close()
        return success

    # ── Alpaca ───────────────────────────────────────────────

    @staticmethod
    def _buy_alpaca(symbol: str, quantity: float) -> bool:
        try:
            if Config.PAPER_MODE:
                logger.info(f"[PAPER] ALPACA BUY {quantity} x {symbol}")
                return True
            alpaca.submit_order(
                symbol=symbol,
                qty=quantity,
                side="buy",
                type="market",
                time_in_force="day",
            )
            return True
        except Exception as e:
            logger.error(f"[Alpaca BUY] {symbol}: {e}")
            return False

    @staticmethod
    def _sell_alpaca(symbol: str, quantity: float) -> bool:
        try:
            if Config.PAPER_MODE:
                logger.info(f"[PAPER] ALPACA SELL {quantity} x {symbol}")
                return True
            alpaca.submit_order(
                symbol=symbol,
                qty=quantity,
                side="sell",
                type="market",
                time_in_force="day",
            )
            return True
        except Exception as e:
            logger.error(f"[Alpaca SELL] {symbol}: {e}")
            return False

    # ── Upstox ───────────────────────────────────────────────

    @staticmethod
    def _buy_upstox(symbol: str, quantity: float, price: float) -> bool:
        try:
            if Config.PAPER_MODE:
                logger.info(f"[PAPER] UPSTOX BUY {quantity} x {symbol}")
                return True
            import upstox_client
            configuration = upstox_client.Configuration()
            configuration.access_token = Config.UPSTOX_API_KEY
            api_instance = upstox_client.OrderApi(
                upstox_client.ApiClient(configuration)
            )
            order = upstox_client.PlaceOrderRequest(
                quantity=int(quantity),
                product="D",
                validity="DAY",
                price=0,
                tag="stockagent",
                instrument_token=symbol,
                order_type="MARKET",
                transaction_type="BUY",
                disclosed_quantity=0,
                trigger_price=0,
                is_amo=False,
            )
            api_instance.place_order(order, "2.0")
            return True
        except Exception as e:
            logger.error(f"[Upstox BUY] {symbol}: {e}")
            return False

    @staticmethod
    def _sell_upstox(symbol: str, quantity: float, price: float) -> bool:
        try:
            if Config.PAPER_MODE:
                logger.info(f"[PAPER] UPSTOX SELL {quantity} x {symbol}")
                return True
            import upstox_client
            configuration = upstox_client.Configuration()
            configuration.access_token = Config.UPSTOX_API_KEY
            api_instance = upstox_client.OrderApi(
                upstox_client.ApiClient(configuration)
            )
            order = upstox_client.PlaceOrderRequest(
                quantity=int(quantity),
                product="D",
                validity="DAY",
                price=0,
                tag="stockagent",
                instrument_token=symbol,
                order_type="MARKET",
                transaction_type="SELL",
                disclosed_quantity=0,
                trigger_price=0,
                is_amo=False,
            )
            api_instance.place_order(order, "2.0")
            return True
        except Exception as e:
            logger.error(f"[Upstox SELL] {symbol}: {e}")
            return False

    # ── Portfolio value ───────────────────────────────────────

    @staticmethod
    def get_portfolio_value() -> dict:
        """Return current portfolio with live prices and P&L."""
        from data_fetcher import DataFetcher

        db = SessionLocal()
        holdings = db.query(Portfolio).filter_by(is_active=True).all()
        db.close()

        total_invested = 0
        total_current = 0
        items = []

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
            })
            total_invested += h.invested_amount
            total_current += current * h.quantity

        return {
            "holdings": items,
            "total_invested": round(total_invested, 2),
            "total_current_value": round(total_current, 2),
            "total_pnl": round(total_current - total_invested, 2),
            "total_pnl_pct": round(
                (total_current - total_invested) / total_invested * 100
                if total_invested > 0 else 0,
                2,
            ),
        }