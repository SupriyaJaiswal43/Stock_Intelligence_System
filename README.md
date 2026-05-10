# 🤖 Global Stock AI Agent

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API keys
```bash
cp .env.example .env
# Edit .env with your actual API keys
```

### 3. Setup PostgreSQL
```bash
createdb stockagent
# Update DATABASE_URL in .env
```

### 4. Run

```bash
# Start full agent (continuous)
python main.py

# One-time scan
python main.py scan

# Check portfolio
python main.py portfolio

# Analyze single stock
python main.py analyze AAPL
python main.py analyze TCS.NS

# AI portfolio health report
python main.py health
```

## API Keys — Where to Get

| Key | Website | Free? |
|-----|---------|-------|
| ALPHA_VANTAGE_KEY | alphavantage.co | ✅ Free |
| TWELVE_DATA_KEY | twelvedata.com | ✅ Free |
| FINNHUB_KEY | finnhub.io | ✅ Free |
| NEWS_API_KEY | newsapi.org | ✅ Free |
| GNEWS_API_KEY | gnews.io | ✅ Free |
| MARKETAUX_KEY | marketaux.com | ✅ Free |
| GROQ_API_KEY | groq.com | ✅ Free |
| TELEGRAM_BOT_TOKEN | @BotFather on Telegram | ✅ Free |
| ALPACA_API_KEY | alpacamarkets.com | ✅ Free (paper) |

## How It Works

```
Every 15 minutes:
1. Fetch stock prices (yfinance → TwelveData → AlphaVantage)
2. Calculate technical indicators (RSI, MACD, EMA, Bollinger Bands)
3. Fetch latest news from 4 sources
4. AI (OpenAI/Groq) makes BUY/SELL/HOLD decision
5. Execute trades (paper or real)
6. Send Telegram alert
```

## PAPER_MODE=true
All trades are simulated. No real money is used.
Set PAPER_MODE=false only when you're ready for real trading.
