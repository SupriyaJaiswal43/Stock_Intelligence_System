# Database-Free Core Files for Global Stock AI Agent

## 1. news_fetcher.p
import requests
import finnhub
from config import Config
import logging


# Dummy Cache Functions

def cache_get(key):
    return None


def cache_set(key, value, ttl=300):
    pass


logger = logging.getLogger(__name__)

finnhub_client = finnhub.Client(
    api_key=Config.FINNHUB_KEY
)


class NewsFetcher:

    @staticmethod
    def get_stock_news(symbol: str, company_name: str = "") -> list:

        all_news = []

        # Finnhub News
        try:
            from datetime import datetime, timedelta

            today = datetime.now().strftime("%Y-%m-%d")
            week_ago = (
                datetime.now() - timedelta(days=7)
            ).strftime("%Y-%m-%d")

            news = finnhub_client.company_news(
                symbol,
                _from=week_ago,
                to=today
            )

            for item in news[:5]:
                all_news.append({
                    "title": item.get("headline", ""),
                    "summary": item.get("summary", ""),
                    "source": "finnhub",
                    "url": item.get("url", ""),
                })

        except Exception as e:
            logger.warning(f"[Finnhub news] {symbol}: {e}")

        # NewsAPI
        try:

            query = (
                company_name
                if company_name
                else symbol.replace(".NS", "")
            )

            url = (
                f"https://newsapi.org/v2/everything"
                f"?q={query}&language=en&sortBy=publishedAt"
                f"&pageSize=5&apiKey={Config.NEWS_API_KEY}"
            )

            res = requests.get(url, timeout=10).json()

            for article in res.get("articles", []):
                all_news.append({
                    "title": article.get("title", ""),
                    "summary": article.get("description", ""),
                    "source": "newsapi",
                    "url": article.get("url", ""),
                })

        except Exception as e:
            logger.warning(f"[NewsAPI] {symbol}: {e}")

        return all_news[:10]

    @staticmethod
    def get_market_sentiment(symbol: str) -> dict:

        try:

            sentiment = finnhub_client.news_sentiment(symbol)

            return {
                "buzz_score": sentiment.get("buzz", {}).get("buzz", 0),
                "news_score": sentiment.get("companyNewsScore", 0),
                "sector_avg": sentiment.get(
                    "sectorAverageBullishPercent",
                    0
                ),
                "bullish_pct": sentiment.get(
                    "sentiment",
                    {}
                ).get("bullishPercent", 0),
                "bearish_pct": sentiment.get(
                    "sentiment",
                    {}
                ).get("bearishPercent", 0),
            }

        except Exception as e:

            logger.warning(
                f"[Finnhub sentiment] {symbol}: {e}"
            )

            return {
                "buzz_score": 0,
                "news_score": 0,
                "bullish_pct": 0,
                "bearish_pct": 0,
            }



