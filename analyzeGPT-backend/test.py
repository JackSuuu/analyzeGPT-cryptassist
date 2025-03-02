import requests
import pandas as pd

# Set parameters
symbol = "BTCUSDT"
interval = "1h"
limit = 100  # Number of data points

# Binance API URL
url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"

# Fetch data
response = requests.get(url)
data = response.json()

# Convert to DataFrame
df = pd.DataFrame(data, columns=[
    "Timestamp", "Open", "High", "Low", "Close", "Volume", 
    "CloseTime", "QuoteAssetVolume", "Trades", "TakerBuyBase", "TakerBuyQuote", "Ignore"
])

# Convert timestamp
df["Timestamp"] = pd.to_datetime(df["Timestamp"], unit='ms')

# Save to CSV
df.to_csv("binance_data.csv", index=False)

print("CSV file saved!")