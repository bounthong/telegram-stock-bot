import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")  # Optional, defaults to empty if not set
DATA_API = os.environ.get("DATA_API", "alpha_vantage").lower()  # Default to Alpha Vantage

FPS = 60