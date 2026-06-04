import pandas as pd
import yfinance as yf
import gspread
import json
import os

from datetime import datetime
from google.oauth2.service_account import Credentials

# --------------------------
# GOOGLE SHEETS CONNECTION
# --------------------------

creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])

scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    creds_dict,
    scopes=scopes
)

client = gspread.authorize(creds)

sheet_id = os.environ["GOOGLE_SHEET_ID"]

spreadsheet = client.open_by_key(sheet_id)
worksheet = spreadsheet.worksheet("Daily_MRS")

# --------------------------
# LOAD SYMBOLS
# --------------------------

symbols = pd.read_csv("symbols.csv")["Symbol"].tolist()

results = []

# --------------------------
# NIFTY DATA
# --------------------------

nifty = yf.download(
    "^NSEI",
    period="3mo",
    auto_adjust=True,
    progress=False
)

if len(nifty) < 30:
    raise Exception("Unable to download NIFTY data")

nifty_return = (
    float(nifty["Close"].iloc[-1]) /
    float(nifty["Close"].iloc[-30]) - 1
) * 100

# --------------------------
# SCAN STOCKS
# --------------------------

for symbol in symbols:

    try:

        print(f"Processing {symbol}")

        df = yf.download(
            symbol,
            period="6mo",
            auto_adjust=True,
            progress=False
        )

        if len(df) < 90:
            print(f"Skipping {symbol} - insufficient data")
            continue

        close = df["Close"]
        volume = df["Volume"]

        # Relative Strength
        stock_return = (
            float(close.iloc[-1]) /
            float(close.iloc[-30]) - 1
        ) * 100

        relative_strength = stock_return - nifty_return

        # Volume Persistence
        vol5 = float(volume.tail(5).mean())
        vol60 = float(volume.tail(60).mean())

        if vol60 == 0:
            volume_ratio = 0
        else:
            volume_ratio = vol5 / vol60

        # Attention Acceleration
        ret20 = (
            float(close.iloc[-1]) /
            float(close.iloc[-20]) - 1
        ) * 100

        volatility = float(
            close.pct_change().tail(90).std()
        )

        if volatility == 0:
            attention_acceleration = 0
        else:
            attention_acceleration = ret20 / volatility

        # Final Score
        score = (
            0.30 * relative_strength +
            40 * volume_ratio +
            0.30 * attention_acceleration
        )

        results.append([
            datetime.today().strftime("%Y-%m-%d"),
            symbol,
            0,
            round(volume_ratio, 2),
            round(relative_strength, 2),
            round(score, 2),
            0
        ])

        print(f"Success: {symbol}")

    except Exception as e:

        print(f"ERROR: {symbol} -> {e}")

# --------------------------
# SORT & RANK
# --------------------------

results = sorted(
    results,
    key=lambda x: x[5],
    reverse=True
)

for rank, row in enumerate(results, start=1):
    row[6] = rank

# --------------------------
# WRITE TO SHEET
# --------------------------

for row in results:
    worksheet.append_row(row)

print(f"{len(results)} rows written")
