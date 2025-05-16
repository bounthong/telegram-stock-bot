import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for servers/headless use
import matplotlib.pyplot as plt
import os
import pandas as pd
import time
from stock_api import fetch_stock_data

def generate_chart(symbol):
    data = fetch_stock_data(symbol)
    if not data:
        return None

    # Extract closing prices
    try:
        if symbol.upper() in ["USDT", "BTC", "ETH"]:
            df = pd.DataFrame.from_dict(data, orient="index")["4a. close (USD)"].astype(float)
        else:
            df = pd.DataFrame.from_dict(data, orient="index")["4. close"].astype(float)
    except KeyError:
        return None  # If structure is unexpected

    # Sort and slice the last 30 days
    df = df.sort_index()[-30:]

    # Ensure output directory exists
    charts_dir = "charts"
    os.makedirs(charts_dir, exist_ok=True)

    # Unique chart path to avoid file conflicts
    timestamp = int(time.time())
    chart_path = os.path.join(charts_dir, f"{symbol}_{timestamp}.png")

    # Plot
    plt.figure(figsize=(10, 5))
    plt.plot(df.index, df.values, marker='o', linestyle='-', color='blue', label=f"{symbol} Price")
    plt.title(f"{symbol} Price Chart (Last 30 Days)")
    plt.xlabel("Date")
    plt.ylabel("Price (USD)")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(chart_path)
    plt.close()

    return chart_path
