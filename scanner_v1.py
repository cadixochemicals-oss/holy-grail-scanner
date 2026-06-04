import pandas as pd
import yfinance as yf
import gspread
import json
import os

from datetime import datetime
from google.oauth2.service_account import Credentials

# ---------------------------------
# GOOGLE SHEETS
# ---------------------------------

creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])

creds = Credentials.from_service_account_info(
    creds_dict,
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)

client = gspread.authorize(creds)

spreadsheet = client.open_by_key(
    os.environ["GOOGLE_SHEET_ID"]
)

worksheet = spreadsheet.worksheet("Daily_MRS")

# ---------------------------------
# LOAD SYMBOLS
# ---------------------------------

symbols = pd.read_csv("symbols.csv")["Symbol"].tolist()

# ---------------------------------
# NIFTY
# ---------------------------------

nifty = yf.download(
    "^NSEI",
    period="1y",
    auto_adjust=True,
    progress=False
)

nifty_close = nifty["Close"].squeeze()

nifty_return_30 = (
    nifty_close.iloc[-1] /
    nifty_close.iloc[-30] - 1
) * 100

# ---------------------------------
# SCAN
# ---------------------------------

results = []

for symbol in symbols:

    try:

        print(f"Processing {symbol}")

        df = yf.download(
            symbol,
            period="1y",
            auto_adjust=True,
            progress=False
        )

        if len(df) < 252:
            continue

        close = df["Close"].squeeze()
        volume = df["Volume"].squeeze()

        current_price = close.iloc[-1]

        # -----------------------------
        # Relative Strength
        # -----------------------------

        stock_return_30 = (
            close.iloc[-1] /
            close.iloc[-30] - 1
        ) * 100

        relative_strength = (
            stock_return_30 - nifty_return_30
        )

        # -----------------------------
        # Volume Ratio
        # -----------------------------

        vol5 = volume.tail(5).mean()
        vol60 = volume.tail(60).mean()

        volume_ratio = 0

        if vol60 > 0:
            volume_ratio = vol5 / vol60

        # -----------------------------
        # Distance From 52 Week High
        # -----------------------------

        high_52w = close.max()

        distance_52w = (
            current_price / high_52w
        ) * 100

        # -----------------------------
        # Attention Event
        # -----------------------------

        attention_event = 0

        daily_return = (
            close.iloc[-1] /
            close.iloc[-2] - 1
        ) * 100

        if daily_return > 5:
            attention_event = 1

        if volume_ratio > 3:
            attention_event = 1

        # -----------------------------
        # Attention Score
        # -----------------------------

        attention_score = (
            volume_ratio * 20 +
            relative_strength * 3 +
            (distance_52w - 80) * 2 +
            attention_event * 25
        )

        results.append([
            datetime.today().strftime("%Y-%m-%d"),
            symbol,
            round(float(volume_ratio), 2),
            round(float(relative_strength), 2),
            round(float(distance_52w), 2),
            attention_event,
            round(float(attention_score), 2),
            0
        ])

    except Exception as e:

        print(f"ERROR {symbol}: {e}")

# ---------------------------------
# SORT
# ---------------------------------

results = sorted(
    results,
    key=lambda x: x[6],
    reverse=True
)

for rank, row in enumerate(results, start=1):
    row[7] = rank

# ---------------------------------
# WRITE TO SHEET
# ---------------------------------

for row in results:
    worksheet.append_row(row)

print(f"{len(results)} rows written")
