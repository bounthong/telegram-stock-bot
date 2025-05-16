Telegram Stock Bot
A Telegram bot that fetches stock data, performs analysis, and provides visualizations.
Features

Get the current stock price for any symbol (e.g., AAPL for Apple).
Calculate 7-day and 14-day moving averages.
Set price alerts (e.g., notify if a stock exceeds a threshold).
Display a 30-day price chart using Matplotlib.
Interactive menu with Telegram buttons.

Project Structure

bot.py: Main bot script handling Telegram interactions.
config.py: Configuration settings (API keys, tokens).
stock_api.py: Fetches and processes stock data from Alpha Vantage.
plotter.py: Generates price charts.
alerts.py: Manages price alerts in memory.
requirements.txt: Lists project dependencies.
README.md: Installation and usage guide.

Setup

Clone the Repository:git clone <your-repo-url>
cd stock_telegram_bot


Create a Virtual Environment:python -m venv venv
source venv/bin/activate  # On macOS/Linux
venv\Scripts\activate     # On Windows


Install Dependencies:pip install -r requirements.txt


Configure API Keys:
Get an Alpha Vantage API key from alphavantage.co.
Create a Telegram bot via BotFather to get a token.
Create a .env file with:ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token




Run the Bot:python bot.py



Testing

Add the bot to a Telegram group or chat directly.
Send /start to access the menu.
Test features like fetching prices, setting alerts, and viewing charts.

Deployment

Deploy on a service like Render or Heroku for continuous operation.
Set environment variables for ALPHA_VANTAGE_API_KEY and TELEGRAM_BOT_TOKEN.

