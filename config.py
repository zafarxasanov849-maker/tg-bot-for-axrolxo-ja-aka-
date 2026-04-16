import os
from pathlib import Path
from dotenv import load_dotenv

# Always load .env from the same directory as this file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Role → Telegram user ID mapping
FOUNDER_ID = int(os.getenv("FOUNDER_ID", 0))
MARKETING_ID = int(os.getenv("MARKETING_ID", 0))
SALES_ID = int(os.getenv("SALES_ID", 0))
DIRECT_MANAGER_ID = int(os.getenv("DIRECT_MANAGER_ID", 0))

WHITELIST: dict[int, str] = {
    FOUNDER_ID: "FOUNDER",
    MARKETING_ID: "MARKETING",
    SALES_ID: "SALES",
    DIRECT_MANAGER_ID: "DIRECT_MANAGER",
}

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
_sa_file = os.getenv("SERVICE_ACCOUNT_FILE", "service_account.json")
SERVICE_ACCOUNT_FILE = str(BASE_DIR / _sa_file) if not os.path.isabs(_sa_file) else _sa_file
GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID")

# Sheet tab names
SHEET_RAW_DATA = "Raw_Data"
SHEET_FUNNEL_PERFORMANCE = "Funnel_Performance"
SHEET_LTV_COHORT = "LTV_Cohort"
SHEET_DAILY_SUMMARY = "Daily_Summary"

# Anomaly detection threshold (30%)
ANOMALY_THRESHOLD = 0.30

# Scheduler times (UTC+5 → UTC offset handled in scheduler)
NUDGE_HOUR = 20   # 20:00 local
ESCALATE_HOUR = 21  # 21:00 local
TIMEZONE = "Asia/Tashkent"
