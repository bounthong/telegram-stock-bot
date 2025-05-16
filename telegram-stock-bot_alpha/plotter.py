import matplotlib
matplotlib.use("Agg")  # Set non-interactive backend before importing pyplot
import matplotlib.pyplot as plt
import os
import pandas as pd
from stock_api import fetch_stock_data

def generate_chart(symbol):
    data = fetch_stock_data(symbol)
    if not data:
        return None
    df = pd.DataFrame.from_dict(data, orient="index")["4. close"].astype(float)
    df = df.sort_index()[-30:]  # Last 30 days
    plt.figure(figsize=(10, 5))
    plt.plot(df.index, df.values, label=f"{symbol} Price")
    plt.title(f"{symbol} Stock Price (Last 30 Days)")
    plt.xlabel("Date")
    plt.ylabel("Price (USD)")
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    chart_path = f"{symbol}_chart.png"
    plt.savefig(chart_path)
    plt.close()
    return chart_path