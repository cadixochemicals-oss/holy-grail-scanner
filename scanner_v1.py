import pandas as pd
import numpy as np
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

# NIFTY proxy
nifty = yf.download("^NSEI", period="3mo", auto_adjust=True, progress=False)

nifty_return = (
    nifty["Close"].iloc[-1] /
    nifty["Close"].iloc[-30] - 1
) * 100

# --------------------------
# SCAN
# --------------------------

for symbol in symbols:

    try:

        df = yf.download(
            symbol,
            period="6mo",
            auto_adjust=True,
            progress=False
        )

        if len(df) < 90:
            continue

        # Relative Strength
        stock_return = (
            df["Close"].iloc[-1] /
            df["Close"].iloc[-30] - 1
        ) * 100

        relative_strength = stock_return - nifty_return

        # Volume Persistence
        vol5 = df["Volume"].tail(5).mean()
        vol60 = df["Volume"].tail(60).mean()

        volume_ratio = vol5 / vol60 if vol60 > 0 else 0

        # Attention Acceleration
        ret20 = (
            df["Close"].iloc[-1] /
            df["Close"].iloc[-20] - 1
        ) * 100

        volatility = (
            df["Close"]
            .pct_change()
            .tail(90)
            .std()
        )

        attention_acceleration = (
            ret20 / volatility
            if volatility > 0
            else 0
        )

        # Score
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

    except Exception as e:
        print(symbol, e)

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
