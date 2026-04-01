# KPI & LTV Tracking Bot

Production-ready Telegram bot for multi-funnel business intelligence.  
Stack: **Python 3.10+** · **aiogram 3.x** · **Google Sheets API** · **APScheduler**

---

## Directory Structure

```
.
├── main.py                      # Entry point
├── config.py                    # All env-based settings
├── requirements.txt
├── .env.example                 # Copy to .env and fill in
├── service_account.json         # Google Service Account key (DO NOT commit)
│
├── handlers/
│   ├── __init__.py
│   ├── common.py                # /start + funnel selector
│   ├── _base.py                 # Shared helpers (anomaly, upload, row builder)
│   ├── vsl.py                   # VSL funnel FSM
│   ├── lead_magnet.py           # Lead Magnet funnel FSM
│   ├── seminar.py               # Seminar funnel FSM
│   └── sales.py                 # Sales & LTV FSM
│
├── states/
│   ├── vsl_states.py
│   ├── lead_magnet_states.py
│   ├── seminar_states.py
│   └── sales_states.py
│
├── middlewares/
│   └── auth.py                  # Whitelist + role injection
│
└── services/
    ├── google_api.py            # Sheets + Drive integration
    ├── anomaly_detector.py      # 7-day average watchdog
    └── scheduler.py             # APScheduler reminders (20:00 & 21:00)
```

---

## 1. Google Cloud Setup (Service Account)

### Step 1 — Create a Google Cloud Project
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click **"New Project"** → give it a name → **Create**

### Step 2 — Enable APIs
In your project, go to **APIs & Services → Library** and enable:
- **Google Sheets API**
- **Google Drive API**

### Step 3 — Create a Service Account
1. Go to **APIs & Services → Credentials**
2. Click **"Create Credentials" → Service Account**
3. Give it a name (e.g., `kpi-bot`) → **Create and Continue**
4. Role: **Editor** → **Done**
5. Click the service account email → **Keys tab** → **Add Key → JSON**
6. Download the JSON file and rename it `service_account.json`
7. Place it in the project root (same folder as `main.py`)

### Step 4 — Share the Spreadsheet
1. Create a new Google Spreadsheet
2. Copy its ID from the URL:  
   `https://docs.google.com/spreadsheets/d/`**`SPREADSHEET_ID`**`/edit`
3. Click **Share** → paste the service account email (found in `service_account.json` under `client_email`) → give **Editor** access

### Step 5 — Create a Google Drive Folder for Screenshots
1. Create a folder in Google Drive
2. Share it with the same service account email (Editor access)
3. Copy the folder ID from its URL

---

## 2. Environment Configuration

```bash
cp .env.example .env
```

Fill in `.env`:

```env
BOT_TOKEN=7123456789:AAF...         # From @BotFather
FOUNDER_ID=123456789                # Your Telegram numeric ID
MARKETING_ID=987654321
SALES_ID=111222333
DIRECT_MANAGER_ID=444555666

SPREADSHEET_ID=1BxiMVs0XRA...       # From the spreadsheet URL
SERVICE_ACCOUNT_FILE=service_account.json
GDRIVE_FOLDER_ID=1A2B3C...          # From the Drive folder URL
```

To find your Telegram ID, message [@userinfobot](https://t.me/userinfobot).

---

## 3. Installation & Run

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## 4. Google Sheets Data Structure

The bot auto-creates four tabs on first run:

| Tab | Purpose |
|-----|---------|
| `Raw_Data` | Every single entry with full timestamp |
| `Funnel_Performance` | CPL, CAC, conversion % per funnel per day |
| `LTV_Cohort` | Customer lifetime value, purchase count, first funnel |
| `Daily_Summary` | Founder's daily flash report feed |

---

## 5. Looker Studio — Live LTV & ROI Dashboard

### Connect Google Sheets to Looker Studio
1. Go to [lookerstudio.google.com](https://lookerstudio.google.com)
2. Click **"Create" → Data Source**
3. Select **Google Sheets** connector
4. Choose your spreadsheet → select the `Daily_Summary` tab → **Connect**
5. Set field types:
   - `date` → **Date (YYYY-MM-DD)**
   - All numeric fields → **Number**
6. Click **"Create Report"**

### Recommended Charts
| Chart | Dimensions | Metrics |
|-------|-----------|---------|
| Time series | `date` | `total_revenue`, `total_ad_spend` |
| Scorecard | — | `avg_ltv`, `blended_cac` |
| Bar chart | `date` | `vsl_conv_rate`, `lm_conv_rate`, `seminar_conv_rate` |
| Table | `customer_id` (from LTV_Cohort) | `ltv`, `purchase_count` |

For LTV Cohort analysis, add a second data source pointing to `LTV_Cohort` tab.

---

## 6. Production Deployment (systemd)

```ini
# /etc/systemd/system/kpi-bot.service
[Unit]
Description=KPI LTV Tracking Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/kpi-bot
ExecStart=/opt/kpi-bot/venv/bin/python main.py
Restart=always
RestartSec=5
EnvironmentFile=/opt/kpi-bot/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable kpi-bot
sudo systemctl start kpi-bot
sudo journalctl -u kpi-bot -f   # View logs
```

---

## 7. Role Permissions

| Action | FOUNDER | MARKETING | SALES | DIRECT_MANAGER |
|--------|---------|-----------|-------|----------------|
| VSL report | ✅ | ✅ | ❌ | ❌ |
| Lead Magnet report | ✅ | ✅ | ❌ | ❌ |
| Seminar report | ✅ | ✅ | ✅ | ❌ |
| Sales / LTV | ✅ | ❌ | ✅ | ❌ |
| Flash report (notification) | ✅ | ❌ | ❌ | ❌ |

---

## 8. Bot Features Summary

- **Multi-funnel FSM**: VSL → Lead Magnet → Seminar → Sales
- **Auto-correction**: Negative inputs converted via `abs()` with notification
- **Evidence-based reporting**: Screenshots uploaded to Google Drive, URL stored in Sheets
- **AI Watchdog**: Compares entry vs 7-day average; >30% deviation triggers explanation prompt
- **Automated nudging**: 20:00 reminder to reporters; 21:00 escalation to Founder
- **LTV Cohort**: Tracks total spend per customer across purchases
- **Looker Studio ready**: Clean date (YYYY-MM-DD) and numeric formats throughout
