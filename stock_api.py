import requests
import pandas as pd
import logging
import time
from datetime import datetime, timedelta
from config import ALPHA_VANTAGE_API_KEY, CACHE_DURATION_STOCKS, CACHE_DURATION_CRYPTO

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Rate limiting
REQUESTS_PER_MINUTE = 5
DAILY_REQUEST_LIMIT = 25  # Daily limit for API requests for free account at Alpha Vantage
request_timestamps = []  # Per-minute tracking
daily_request_timestamps = []  # Daily tracking
CACHE = {}  # Format: {symbol: (data, timestamp)}

def fetch_stock_data(symbol, max_retries=3):
    global request_timestamps, daily_request_timestamps, CACHE

    # Check cache
    cache_duration = CACHE_DURATION_CRYPTO if symbol.upper() in ["USDT", "BTC", "ETH"] else CACHE_DURATION_STOCKS
    if symbol in CACHE:
        data, timestamp = CACHE[symbol]
        if time.time() - timestamp < cache_duration:
            logger.debug(f"Returning cached data for {symbol}")
            return data
        else:
            logger.debug(f"Cache expired for {symbol}")
            del CACHE[symbol]

    # Rate limiting (daily)
    current_time = time.time()
    daily_request_timestamps = [t for t in daily_request_timestamps if current_time - t < 86400]  # 24 hours
    if len(daily_request_timestamps) >= DAILY_REQUEST_LIMIT:
        logger.error("Daily API rate limit exceeded.")
        return "Daily API limit exceeded. Please try again tomorrow."

    # Rate limiting (per minute)
    request_timestamps = [t for t in request_timestamps if current_time - t < 60]
    if len(request_timestamps) >= REQUESTS_PER_MINUTE:
        sleep_time = 60 - (current_time - request_timestamps[0])
        if sleep_time > 0:
            logger.warning(f"Per-minute rate limit reached. Sleeping for {sleep_time:.2f} seconds.")
            time.sleep(sleep_time)
        request_timestamps = []

    # Determine endpoint based on symbol
    if symbol.upper() in ["USDT", "BTC", "ETH"]:
        url = f"https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol={symbol.upper()}&market=USD&apikey={ALPHA_VANTAGE_API_KEY}"
    else:
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol.upper()}&apikey={ALPHA_VANTAGE_API_KEY}"

    logger.debug(f"Sending request to: {url}")
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            request_timestamps.append(time.time())
            daily_request_timestamps.append(time.time())
            response.raise_for_status()
            logger.debug(f"Response status: {response.status_code}, Response text: {response.text}")
            data = response.json()

            # Validate response
            if symbol.upper() in ["USDT", "BTC", "ETH"]:
                if "Time Series (Digital Currency Daily)" not in data:
                    logger.error(f"Failed to fetch crypto data for {symbol}: {data}")
                    return None
                time_series = data["Time Series (Digital Currency Daily)"]
            else:
                if "Time Series (Daily)" not in data:
                    logger.error(f"Failed to fetch data for {symbol}: {data}")
                    return None
                time_series = data["Time Series (Daily)"]

            # Check for stale data
            latest_date = max(time_series.keys())
            date_obj = datetime.strptime(latest_date, "%Y-%m-%d")
            if datetime.now() - date_obj > timedelta(days=2):
                logger.warning(f"Data for {symbol} is stale: {latest_date}")
                return None

            # Cache the result
            CACHE[symbol] = (time_series, time.time())
            return time_series
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt + 1} failed for {symbol}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
            else:
                logger.error(f"All retries failed for {symbol}")
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