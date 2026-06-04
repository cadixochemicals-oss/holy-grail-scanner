import pandas as pd
import yfinance as yf
import gspread
import json
import os

from datetime import datetime
from google.oauth2.service_account import Credentials

# ==========================================
# GOOGLE SHEET CONNECTION
# ==========================================

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

print("Connected to Daily_MRS")

# ==========================================
# SYMBOLS
# ==========================================

symbols = pd.read_csv("symbols.csv")["Symbol"].tolist()

print("Symbols loaded:", len(symbols))

# ==========================================
# NIFTY DATA
# ==========================================

nifty = yf.download(
    "^NSEI",
    period="1y",
    auto_adjust=True,
    progress=False
)

print("NIFTY rows:", len(nifty))

if len(nifty) < 50:
    raise Exception("NIFTY data not downloaded")

nifty_close = nifty["Close"].squeeze()

nifty_return_30 = (
    nifty_close.iloc[-1] /
    nifty_close.iloc[-30] - 1
) * 100

print("NIFTY 30D Return:", round(float(nifty_return_30), 2))

# ==========================================
# SCAN
# ==========================================

results = []

for symbol in symbols:

    try:

        print("=" * 50)
        print("Processing:", symbol)

        df = yf.download(
            symbol,
            period="1y",
            auto_adjust=True,
            progress=False
        )

        print("Rows downloaded:", len(df))

        if df.empty:
            print("EMPTY DATA")
            continue

        if len(df) < 50:
            print("TOO FEW ROWS")
            continue

        close = df["Close"].squeeze()
        volume = df["Volume"].squeeze()

        current_price = float(close.iloc[-1])

        # ----------------------
        # Relative Strength
        # ----------------------

        stock_return_30 = (
            close.iloc[-1] /
            close.iloc[-30] - 1
        ) * 100

        relative_strength = (
            stock_return_30 - nifty_return_30
        )

        # ----------------------
        # Volume Ratio
        # ----------------------

        vol5 = volume.tail(5).mean()
        vol60 = volume.tail(60).mean()

        volume_ratio = 0

        if vol60 > 0:
            volume_ratio = vol5 / vol60

        # ----------------------
        # 52 Week High Distance
        # ----------------------

        high_52w = close.max()

        distance_52w = (
            current_price / high_52w
        ) * 100

        # ----------------------
        # Attention Event
        # ----------------------

        attention_event = 0

        daily_return = (
            close.iloc[-1] /
            close.iloc[-2] - 1
        ) * 100

        if daily_return > 5:
            attention_event = 1

        if volume_ratio > 3:
            attention_event = 1

        # ----------------------
        # Attention Score
        # ----------------------

        attention_score = (
            volume_ratio * 20 +
            relative_strength * 3 +
            (distance_52w - 80) * 2 +
            attention_event * 25
        )

        row = [
            datetime.today().strftime("%Y-%m-%d"),
            symbol,
            round(float(volume_ratio), 2),
            round(float(relative_strength), 2),
            round(float(distance_52w), 2),
            attention_event,
            round(float(attention_score), 2),
            0
        ]

        results.append(row)

        print("ADDED:", symbol)

    except Exception as e:

        print("ERROR:", symbol)
        print(str(e))

# ==========================================
# SORT
# ==========================================

print("Total results before ranking:", len(results))

results = sorted(
    results,
    key=lambda x: x[6],
    reverse=True
)

for rank, row in enumerate(results, start=1):
    row[7] = rank

# ==========================================
# WRITE TO SHEET
# ==========================================

for row in results:
    worksheet.append_row(row)

print("ROWS WRITTEN:", len(results))
