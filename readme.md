# Telegram Stock Bot

A Telegram bot that fetches stock data, performs analysis, and provides visual price charts.

## Features

* Get current stock/crypto prices (e.g., AAPL, BTC)
* Calculate 7-day & 14-day moving averages
* Set customizable price alerts
* Display 30-day price charts with Matplotlib
* Interactive menu with Telegram inline buttons

## Project Structure

* **bot.py** — Main Telegram bot logic and handlers
* **config.py** — API keys and config constants
* **stock\_api.py** — Fetch and cache stock/crypto data from Alpha Vantage
* **plotter.py** — Generates price charts (improved filename handling & crypto support)
* **alerts.py** — In-memory alert management
* **requirements.txt** — Dependencies (includes `nest_asyncio` for Windows event loop fix)
* **README.md** — Project overview and setup instructions

## Setup

1. **Clone repo**

   ```bash
   git clone <your-repo-url>
   cd stock_telegram_bot
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv venv
   # macOS/Linux:
   source venv/bin/activate
   # Windows:
   venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API keys**

   * Get Alpha Vantage API key from [alphavantage.co](https://www.alphavantage.co/)
   * Create a Telegram bot and get token via [BotFather](https://t.me/BotFather)
   * Create `.env` file:

     ```
     ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key
     TELEGRAM_BOT_TOKEN=your_telegram_bot_token
     ```

5. **Run the bot**

   ```bash
   python bot.py
   ```

## Testing

* Add your bot to a Telegram group or chat privately
* Send `/start` to display the interactive menu
* Test commands like `/price`, `/ma`, `/alert`, and `/chart`

## Deployment Notes

* Deploy on services like Render or Heroku for 24/7 operation
* Make sure to set environment variables (`ALPHA_VANTAGE_API_KEY`, `TELEGRAM_BOT_TOKEN`) in your deployment config


