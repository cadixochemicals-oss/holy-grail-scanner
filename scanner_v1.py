import pandas as pd
import yfinance as yf
import gspread
import json
import os

from datetime import datetime
from google.oauth2.service_account import Credentials

# --------------------------
# GOOGLE SHEETS
# --------------------------

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

# --------------------------
# SYMBOLS
# --------------------------

symbols = pd.read_csv("symbols.csv")["Symbol"].tolist()

results = []

# --------------------------
# NIFTY
# --------------------------

nifty = yf.download(
    "^NSEI",
    period="3mo",
    progress=False,
    auto_adjust=True
)

print("NIFTY columns:", nifty.columns)

nifty_close = nifty["Close"].squeeze()

nifty_return = (
    nifty_close.iloc[-1] /
    nifty_close.iloc[-30] - 1
) * 100

# --------------------------
# STOCK LOOP
# --------------------------

for symbol in symbols:

    try:

        print(f"Processing {symbol}")

        df = yf.download(
            symbol,
            period="6mo",
            progress=False,
            auto_adjust=True
        )

        if len(df) < 90:
            print(f"Skipping {symbol}")
            continue

        close = df["Close"].squeeze()
        volume = df["Volume"].squeeze()

        stock_return = (
            close.iloc[-1] /
            close.iloc[-30] - 1
        ) * 100

        relative_strength = stock_return - nifty_return

        vol5 = volume.tail(5).mean()
        vol60 = volume.tail(60).mean()

        volume_ratio = 0

        if vol60 != 0:
            volume_ratio = vol5 / vol60

        ret20 = (
            close.iloc[-1] /
            close.iloc[-20] - 1
        ) * 100

        volatility = (
            close.pct_change()
            .tail(90)
            .std()
        )

        attention_acceleration = 0

        if volatility != 0:
            attention_acceleration = ret20 / volatility

        score = (
            0.30 * relative_strength +
            40 * volume_ratio +
            0.30 * attention_acceleration
        )

        results.append([
            datetime.today().strftime("%Y-%m-%d"),
            symbol,
            0,
            round(float(volume_ratio), 2),
            round(float(relative_strength), 2),
            round(float(score), 2),
            0
        ])

        print(f"SUCCESS {symbol}")

    except Exception as e:

        print(f"ERROR {symbol}: {e}")

# --------------------------
# RANK
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
