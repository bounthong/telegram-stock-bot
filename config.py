import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
CACHE_DURATION_STOCKS = 1800  # 30 minutes
CACHE_DURATION_CRYPTO = 60    # 1 minute
ALERT_CHECK_INTERVAL = 60     # Default alert check interval in seconds
FPS = 60