import openai
from groq import Groq
from config import Config
from data_fetcher import DataFetcher
from analyzer import TechnicalAnalyzer
from news_fetcher import NewsFetcher
import json
import logging

logger = logging.getLogger(__name__)

openai.api_key = Config.OPENAI_API_KEY


groq_client = Groq(
    api_key=Config.GROQ_API_KEY
)


class AIEngine:

    @staticmethod
    def _build_prompt(
        symbol: str,
        tech: dict,
        news: list,
        sentiment: dict,
        price: float,
    ) -> str:

        news_text = "\n".join([
            f"- {n['title']}"
            for n in news[:8]
        ])

        return f"""
You are an expert stock market analyst.

STOCK: {symbol}
CURRENT PRICE: {price}

TECHNICAL SCORE: {tech['score']}
SIGNAL: {tech['signal']}

NEWS:
{news_text}

Return ONLY valid JSON:

{{
  "action": "BUY" or "SELL" or "HOLD",
  "confidence": 0-100,
  "reason": "short explanation",
  "risk_level": "LOW" or "MEDIUM" or "HIGH",
  "target_price": number,
  "stop_loss": number
}}
"""

    @staticmethod
    def _call_openai(prompt: str):

        try:

            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.3,
                max_tokens=300,
            )

            text = response.choices[0].message.content.strip()

            return json.loads(text)

        except Exception as e:
            logger.warning(f"[OpenAI] failed: {e}")
            return None

    @staticmethod
    def _call_groq(prompt: str):

        try:

            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.3,
                max_tokens=300,
            )

            text = response.choices[0].message.content.strip()

            text = (
                text.replace("```json", "")
                .replace("```", "")
                .strip()
            )

            return json.loads(text)

        except Exception as e:
            logger.warning(f"[Groq] failed: {e}")
            return None

    @staticmethod
    def analyze_stock(symbol: str) -> dict:

        logger.info(f"[AI] Analyzing {symbol}...")

        price = DataFetcher.get_current_price(symbol)

        if price == 0:
            return {
                "action": "HOLD",
                "confidence": 0,
                "reason": "Price unavailable",
            }

        tech = TechnicalAnalyzer.analyze(symbol)

        company_info = DataFetcher.get_company_info(symbol)

        news = NewsFetcher.get_stock_news(
            symbol,
            company_info.get("name", "")
        )

        sentiment = NewsFetcher.get_market_sentiment(symbol)

        prompt = AIEngine._build_prompt(
            symbol,
            tech,
            news,
            sentiment,
            price,
        )

        result = AIEngine._call_groq(prompt)

        if not result:
            result = AIEngine._call_openai(prompt)

        if not result:
            result = {
                "action": tech.get("signal", "HOLD"),
                "confidence": tech.get("score", 50),
                "reason": "Technical analysis fallback",
                "risk_level": "MEDIUM",
                "target_price": price * 1.05,
                "stop_loss": price * 0.95,
            }

        result["symbol"] = symbol
        result["current_price"] = float(price)
        result["technical_score"] = float(
            tech.get("score", 0)
        )

        result["indicators"] = tech.get(
            "indicators",
            {}
        )

        # ── Save decision → feeds dashboard /api/stocks ──
        try:
            from database import SessionLocal, AIDecision
            db = SessionLocal()
            db.add(AIDecision(
                symbol=symbol,
                action=result.get("action", "HOLD"),
                confidence=float(result.get("confidence", 0)),
                reason=result.get("reason", ""),
                price_at_decision=float(price),
                technical_score=float(tech.get("score", 0)),
            ))
            db.commit()
            db.close()
        except Exception as e:
            logger.warning(f"[AI] Decision save failed: {e}")

        logger.info(
            f"[AI] {symbol}: "
            f"{result['action']} "
            f"({result['confidence']}%)"
        )

        return result