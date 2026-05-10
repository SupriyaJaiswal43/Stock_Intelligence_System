import pandas as pd
import ta
import numpy as np
from data_fetcher import DataFetcher
import logging

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:

    @staticmethod
    def analyze(symbol: str) -> dict:
        """
        Run full technical analysis.
        Returns a dict with all indicators + overall score (0-100).
        """
        df = DataFetcher.get_stock_data(symbol, period="3mo")
        if df.empty or len(df) < 30:
            return {"score": 0, "signal": "INSUFFICIENT_DATA", "indicators": {}}

        # Ensure columns exist (yfinance vs others)
        df.columns = [c.title() for c in df.columns]
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"] if "Volume" in df.columns else pd.Series([0]*len(df))

        signals = {}
        score_components = []

        # ── RSI ─────────────────────────────────────────
        try:
            rsi_series = ta.rsi(close, length=14)
            rsi = float(rsi_series.iloc[-1]) if rsi_series is not None else 50
            signals["rsi"] = round(rsi, 2)
            if rsi < 30:
                score_components.append(85)   # oversold = buy
            elif rsi < 45:
                score_components.append(65)
            elif rsi > 70:
                score_components.append(20)   # overbought = sell
            elif rsi > 55:
                score_components.append(40)
            else:
                score_components.append(50)
        except Exception:
            signals["rsi"] = 50

        # ── MACD ────────────────────────────────────────
        try:
            macd_df = ta.macd(close)
            if macd_df is not None and not macd_df.empty:
                macd_val = float(macd_df.iloc[-1, 0])
                signal_val = float(macd_df.iloc[-1, 1])
                signals["macd"] = round(macd_val, 4)
                signals["macd_signal"] = round(signal_val, 4)
                if macd_val > signal_val:
                    score_components.append(70)   # bullish crossover
                else:
                    score_components.append(30)
        except Exception:
            pass

        # ── Bollinger Bands ─────────────────────────────
        try:
            bb = ta.bbands(close, length=20)
            if bb is not None and not bb.empty:
                lower = float(bb.iloc[-1, 0])
                upper = float(bb.iloc[-1, 2])
                current = float(close.iloc[-1])
                signals["bb_lower"] = round(lower, 2)
                signals["bb_upper"] = round(upper, 2)
                signals["current_price"] = round(current, 2)
                pct_b = (current - lower) / (upper - lower) * 100
                if pct_b < 20:
                    score_components.append(80)   # near lower band = buy
                elif pct_b > 80:
                    score_components.append(20)   # near upper band = sell
                else:
                    score_components.append(50)
        except Exception:
            pass

        # ── EMA Trend ───────────────────────────────────
        try:
            ema20 = ta.ema(close, length=20)
            ema50 = ta.ema(close, length=50)
            if ema20 is not None and ema50 is not None:
                e20 = float(ema20.iloc[-1])
                e50 = float(ema50.iloc[-1])
                current = float(close.iloc[-1])
                signals["ema20"] = round(e20, 2)
                signals["ema50"] = round(e50, 2)
                if current > e20 > e50:
                    score_components.append(80)   # strong uptrend
                elif current > e20:
                    score_components.append(65)
                elif current < e20 < e50:
                    score_components.append(20)   # strong downtrend
                else:
                    score_components.append(40)
        except Exception:
            pass

        # ── Volume Spike ────────────────────────────────
        try:
            avg_vol = float(volume.tail(20).mean())
            latest_vol = float(volume.iloc[-1])
            signals["volume_ratio"] = round(latest_vol / avg_vol, 2) if avg_vol > 0 else 1
            if signals["volume_ratio"] > 1.5:
                score_components.append(70)   # high volume = momentum
            else:
                score_components.append(50)
        except Exception:
            pass

        # ── ATR (Volatility) ────────────────────────────
        try:
            atr = ta.atr(high, low, close, length=14)
            if atr is not None:
                signals["atr"] = round(float(atr.iloc[-1]), 2)
        except Exception:
            pass

        # ── Price Change % ──────────────────────────────
        try:
            price_1d = float(close.pct_change(1).iloc[-1] * 100)
            price_5d = float(close.pct_change(5).iloc[-1] * 100)
            price_1m = float(close.pct_change(22).iloc[-1] * 100)
            signals["change_1d"] = round(price_1d, 2)
            signals["change_5d"] = round(price_5d, 2)
            signals["change_1m"] = round(price_1m, 2)
        except Exception:
            pass

        # ── Final Score ─────────────────────────────────
        final_score = round(np.mean(score_components), 1) if score_components else 50

        if final_score >= 70:
            signal = "BUY"
        elif final_score <= 35:
            signal = "SELL"
        else:
            signal = "HOLD"

        return {
            "score": final_score,
            "signal": signal,
            "indicators": signals,
            "data_points": len(df),
        }
