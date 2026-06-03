import os
import json
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

# Read credentials from GitHub Secret
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

worksheet.append_row([
    datetime.now().strftime("%Y-%m-%d"),
    "TEST",
    0,
    1.0,
    0,
    100,
    1
])

print("Row added successfully")
