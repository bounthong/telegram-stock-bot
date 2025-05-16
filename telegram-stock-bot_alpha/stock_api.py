import requests
import pandas as pd
import logging
import time
from config import ALPHA_VANTAGE_API_KEY

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Rate limiting and caching
REQUESTS_PER_MINUTE = 5
request_timestamps = []
CACHE = {}  # Format: {symbol: (data, timestamp)}
CACHE_DURATION = 300  # Cache for 5 minutes

def fetch_stock_data(symbol):
    global request_timestamps, CACHE

    # Check cache
    if symbol in CACHE:
        data, timestamp = CACHE[symbol]
        if time.time() - timestamp < CACHE_DURATION:
            logger.debug(f"Returning cached data for {symbol}")
            return data
        else:
            logger.debug(f"Cache expired for {symbol}")
            del CACHE[symbol]

    # Rate limiting
    current_time = time.time()
    request_timestamps = [t for t in request_timestamps if current_time - t < 60]
    if len(request_timestamps) >= REQUESTS_PER_MINUTE:
        sleep_time = 60 - (current_time - request_timestamps[0])
        if sleep_time > 0:
            logger.warning(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds.")
            return "Rate limit exceeded, please try again in a minute."
        request_timestamps = []

    # Determine endpoint based on symbol
    if symbol.upper() in ["USDT", "BTC", "ETH"]:  # Add more crypto symbols as needed
        url = f"https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol={symbol.upper()}&market=USD&apikey={ALPHA_VANTAGE_API_KEY}"
    else:
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol.upper()}&apikey={ALPHA_VANTAGE_API_KEY}"

    logger.debug(f"Sending request to: {url}")
    try:
        response = requests.get(url)
        request_timestamps.append(time.time())
        logger.debug(f"Response status: {response.status_code}, Response text: {response.text}")
        if response.status_code != 200:
            logger.error(f"HTTP error for {symbol}: Status {response.status_code}, Response: {response.text}")
            return None
        data = response.json()
        if symbol.upper() in ["USDT", "BTC", "ETH"]:
            if "Time Series (Digital Currency Daily)" not in data:
                logger.error(f"Failed to fetch crypto data for {symbol}: {data}")
                return None
            return data["Time Series (Digital Currency Daily)"]
        else:
            if "Time Series (Daily)" not in data:
                logger.error(f"Failed to fetch data for {symbol}: {data}")
                return None
            return data["Time Series (Daily)"]
    except requests.RequestException as e:
        logger.error(f"Request failed for {symbol}: {e}")
        return None

def get_current_price(symbol):
    data = fetch_stock_data(symbol)
    if isinstance(data, str):
        return data
    if not data:
        return None
    latest_date = max(data.keys())
    if symbol.upper() in ["USDT", "BTC", "ETH"]:
        return float(data[latest_date]["4a. close (USD)"])
    else:
        return float(data[latest_date]["4. close"])

def calculate_moving_averages(symbol, days):
    data = fetch_stock_data(symbol)
    if isinstance(data, str):
        return data
    if not data:
        return None
    df = pd.DataFrame.from_dict(data, orient="index")
    if symbol.upper() in ["USDT", "BTC", "ETH"]:
        df["4a. close (USD)"] = df["4a. close (USD)"].astype(float)
        ma = df["4a. close (USD)"].rolling(window=days).mean().iloc[-1]
    else:
        df["4. close"] = df["4. close"].astype(float)
        ma = df["4. close"].rolling(window=days).mean().iloc[-1]
    logger.info(f"Moving Average ({days} days) for {symbol}: {ma}")
    return ma