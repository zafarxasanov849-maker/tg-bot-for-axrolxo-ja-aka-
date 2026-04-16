# KPI & LTV Tracking System — To'liq Hujjat

**Loyiha:** Tizimchiman kursi — KPI va LTV kuzatish tizimi  
**Server:** DigitalOcean Ubuntu 24.04 — `159.223.20.28`  
**Domen:** `https://rahbarlarkursi.duckdns.org`  
**Sana:** 2026-04-16

---

## 1. TIZIM ARXITEKTURASI

```
Telegram Bot (aiogram 3.x)
        │
        ├── Handlers (FSM orqali ma'lumot yig'ish)
        │       ├── VSL Voronkasi
        │       ├── Lead Magnet Voronkasi
        │       ├── Seminar Voronkasi
        │       └── Sotuv / LTV
        │
        ├── Middleware (AuthMiddleware — faqat whitelist foydalanuvchilar)
        │
        ├── Services
        │       ├── GoogleSheetsService (gspread 6.x, service_account auth)
        │       ├── GoogleDriveService (screenshot yuklash)
        │       ├── AnomalyDetector (30% chegara)
        │       └── APScheduler (eslatma va hisobotlar)
        │
        └── Dashboard (Flask 3.x — port 8080)
                ├── Login sahifasi (session-based)
                ├── Dashboard (Chart.js grafiklari)
                ├── Telegram Mini App (/miniapp)
                └── REST API (/api/summary, /api/ltv, ...)

Google Sheets (4 tab):
        ├── Raw_Data        — barcha kiritilgan ma'lumotlar
        ├── Funnel_Performance — voronka samaradorligi
        ├── LTV_Cohort      — mijoz LTV ma'lumotlari
        └── Daily_Summary   — kunlik jamlangan hisobot
```

---

## 2. FOYDALANUVCHI ROLLARI

| Rol | Huquq |
|-----|-------|
| `FOUNDER` | Barcha voronkalar, barcha hisobotlar |
| `MARKETING` | VSL, Lead Magnet, Seminar voronkalari |
| `SALES` | Seminar, Sotuv/LTV voronkalari |
| `DIRECT_MANAGER` | Faqat hisobotlarni ko'rish |

Har bir rol `.env` faylidagi Telegram User ID orqali aniqlanadi:

```
FOUNDER_ID=...
MARKETING_ID=...
SALES_ID=...
DIRECT_MANAGER_ID=...
```

---

## 3. BOT KOMANDALAR

| Komanda | Tavsif |
|---------|--------|
| `/start` | Asosiy menyu — voronka tanlash |
| `/bugun` | Bugungi KPI kartasi (Ad Spend, Leads, Sales, Revenue, CAC, LTV) |
| `/hafta` | Oxirgi 7 kunlik jamlangan hisobot |
| `/mening_hisobotim` | Shaxsiy statistika — necha kun, necha yozuv kiritilgan |

---

## 4. VORONKALAR VA MAYDONLAR

### 4.1 VSL Voronkasi
| Maydon | Tavsif |
|--------|--------|
| `ad_spend` | Reklama xarajati (so'm) |
| `page_views` | Sahifa ko'rishlar soni |
| `video_start` | Video boshlashlar |
| `watch_50` | 50% tomosha |
| `watch_100` | 100% tomosha |
| `cta_clicks` | CTA tugmasi bosilishlar |

**Konversiya:** `cta_clicks / page_views × 100%`

---

### 4.2 Lead Magnet Voronkasi
| Maydon | Tavsif |
|--------|--------|
| `ad_spend` | Reklama xarajati (so'm) |
| `lp_views` | Landing page ko'rishlar |
| `new_leads` | Yangi leadlar soni |
| `contacted` | Bog'lanilgan leadlar |

**Konversiya:** `new_leads / lp_views × 100%`

---

### 4.3 Seminar Voronkasi
| Maydon | Tavsif |
|--------|--------|
| `ad_spend` | Reklama xarajati (so'm) |
| `registrations` | Ro'yxatdan o'tganlar |
| `show_up` | Kelganlar |
| `deposits` | Depozit to'laganlar |
| `sales_count` | Sotuvlar soni |
| `full_payments` | To'liq to'lovlar |

**Kelish konversiyasi:** `show_up / registrations × 100%`  
**Yopish konversiyasi:** `sales_count / show_up × 100%`

---

### 4.4 Sotuv / LTV
| Maydon | Tavsif |
|--------|--------|
| `customer_id` | Mijoz ID (telefon yoki Telegram username) |
| `funnel_source` | Qaysi voronkadan kelgan (VSL / Lead_Magnet / Seminar) |
| `tariff_type` | Tarif nomi |
| `price` | To'lov miqdori (so'm) |
| `customer_type` | new / returning |
| `lead_status` | cold / warm / hot |

LTV avtomatik yangilanadi: takroriy xarid bo'lsa `total_revenue` va `purchase_count` qo'shiladi.

---

## 5. ANOMALIYA ANIQLAGICHI

`services/anomaly_detector.py` — har bir kiritilgan raqamni oxirgi 7 kun o'rtachasi bilan solishtiradi.

- **Chegara:** ±30% (`ANOMALY_THRESHOLD = 0.30`)
- Anomaliya bo'lsa: `anomaly_flag = TRUE`, `anomaly_explanation` da sabab yoziladi
- Bot hisobot qabul qilishdan oldin Founder ga ogohlantirish yuboradi

---

## 6. SCHEDULER (AVTOMATIK ESLATMALAR)

Barcha vaqtlar **Asia/Tashkent** vaqt mintaqasida:

| Vaqt | Vazifa |
|------|--------|
| **20:00** | Hisobot bermaganlar ga shaxsiy eslatma |
| **21:00** | Founder ga eskalatsiya (kim bermagan) |
| **23:50** | Oxirgi eslatma — ham xodimga, ham Founder ga |
| **09:00** | Kechagi kunlik hisobot Founder ga (avtomatik) |
| **Dushanba 09:00** | Haftalik summary Founder ga |

---

## 7. GOOGLE SHEETS TUZILISHI

**Spreadsheet ID:** `.env` faylida `SPREADSHEET_ID`

### Tab 1: `Raw_Data`
Barcha kiritilgan yozuvlar. Ustunlar:
```
timestamp, date, reporter_id, reporter_role, funnel_type,
ad_spend, page_views, video_start, watch_50, watch_100, cta_clicks,
lp_views, new_leads, contacted,
registrations, show_up, deposits, sales_count, full_payments,
customer_id, funnel_source, tariff_type, price, customer_type, lead_status,
screenshot_url, anomaly_flag, anomaly_explanation
```

### Tab 2: `Funnel_Performance`
```
date, funnel_type, ad_spend, leads_or_views, cpl, conversions, cac, conv_rate_pct
```

### Tab 3: `LTV_Cohort`
```
customer_id, first_funnel, first_purchase_date, total_revenue, purchase_count, ltv
```

### Tab 4: `Daily_Summary`
```
date, total_ad_spend, total_leads, total_sales, total_revenue,
blended_cac, avg_ltv, vsl_conv_rate, lm_conv_rate, seminar_conv_rate
```

---

## 8. WEB DASHBOARD

**URL:** `https://rahbarlarkursi.duckdns.org`  
**Login:** `rahbarlarkursi` / `zafar1234`

### KPI Kartalar (tepada):
- Jami Sotuv
- Jami Daromad
- Jami Leads
- Jami Ad Spend
- Blended CAC (Cost per Acquisition)
- O'rtacha LTV
- Umumiy ROI (daromad / xarajat)

### Grafik 1: Daromad dinamikasi (chiziqli)
### Grafik 2: Leads & Sotuvlar (ustunli)
### Grafik 3: Ad Spend vs CAC (ikki o'qli chiziqli)
### Grafik 4: Konversiya % — VSL / Lead Magnet / Seminar

### Funnel Taqqoslash bo'limi:
Har bir voronka uchun alohida: Ad Spend, metrikalar, konversiya %, ROI

### LTV Jadval:
Barcha mijozlar: ID, manba, 1-xarid sanasi, jami daromad, xaridlar soni, LTV

### Filtrlar:
- Sana oralig'i (dan — gacha)
- CSV Export (Excel uchun UTF-8 BOM bilan)

---

## 9. TELEGRAM MINI APP

**URL:** `https://rahbarlarkursi.duckdns.org/miniapp`  
**Ochilish:** Telegram botdagi "📊 Raqamlarni kiritish (Mini App)" tugmasi orqali

4 ta forma (voronka tanlash bilan):
1. VSL — 6 ta maydon
2. Lead Magnet — 5 ta maydon
3. Seminar — 6 ta maydon
4. Sotuv/LTV — 6 ta maydon

Ma'lumot `/api/submit` ga POST so'rov orqali Google Sheets ga saqlanadi.

---

## 10. REST API ENDPOINTLAR

| Endpoint | Method | Tavsif |
|----------|--------|--------|
| `/api/summary` | GET | Kunlik summary (so'nggi 30 kun yoki filtr bilan) |
| `/api/ltv` | GET | LTV Cohort ma'lumotlari |
| `/api/funnel_comparison` | GET | Funnel taqqoslash va ROI |
| `/api/export` | GET | CSV yuklab olish |
| `/api/raw` | GET | So'nggi 50 ta Raw_Data yozuvi |
| `/api/submit` | POST | Mini App dan ma'lumot saqlash |
| `/api/history/<user_id>` | GET | Foydalanuvchi tarixi (so'nggi 10) |

Barcha GET endpointlar `?from=2025-01-01&to=2025-01-31` filtrini qo'llab-quvvatlaydi.

---

## 11. FAYL TUZILISHI

```
/opt/kpi-bot/
├── main.py                    # Bot entry point
├── config.py                  # Barcha sozlamalar
├── .env                       # Maxfiy kalitlar (git ga kirmaydi)
├── service_account.json       # Google Service Account kaliti
├── requirements.txt           # Python kutubxonalar
│
├── handlers/
│   ├── __init__.py
│   ├── _base.py               # Shared sheets_service instance
│   ├── common.py              # /start, funnel tanlash
│   ├── stats.py               # /bugun, /hafta, /mening_hisobotim
│   ├── vsl.py                 # VSL FSM handler
│   ├── lead_magnet.py         # Lead Magnet FSM handler
│   ├── seminar.py             # Seminar FSM handler
│   └── sales.py               # Sotuv/LTV FSM handler
│
├── states/
│   ├── vsl_states.py
│   ├── lead_magnet_states.py
│   ├── seminar_states.py
│   └── sales_states.py
│
├── middlewares/
│   ├── __init__.py
│   └── auth.py                # AuthMiddleware — whitelist tekshiruv
│
├── services/
│   ├── __init__.py
│   ├── google_api.py          # GoogleSheetsService, GoogleDriveService
│   ├── anomaly_detector.py    # ±30% anomaliya tekshiruv
│   └── scheduler.py           # APScheduler — eslatmalar va hisobotlar
│
└── dashboard/
    ├── app.py                 # Flask web app
    ├── templates/
    │   ├── dashboard.html     # Asosiy dashboard
    │   ├── login.html         # Login sahifasi
    │   └── miniapp.html       # Telegram Mini App
    └── static/
        ├── dashboard.css      # Qorong'i tema (bg: #0f1117, accent: #F5A623)
        └── dashboard.js       # Chart.js grafiklari, API chaqiruvlar
```

---

## 12. SERVER BOSHQARUVI

### Systemd xizmatlari

**Bot:**
```bash
sudo systemctl status kpi-bot
sudo systemctl restart kpi-bot
sudo systemctl stop kpi-bot
sudo journalctl -u kpi-bot -f        # Jonli loglar
```

**Dashboard:**
```bash
sudo systemctl status kpi-dashboard
sudo systemctl restart kpi-dashboard
sudo journalctl -u kpi-dashboard -f
```

**Nginx:**
```bash
sudo systemctl status nginx
sudo nginx -t                         # Konfiguratsiyani tekshirish
sudo systemctl reload nginx
```

### SSL sertifikat yangilash
```bash
sudo certbot renew --dry-run          # Tekshirish
sudo certbot renew                    # Yangilash
```

### Server IP dan ulanish
```bash
ssh root@159.223.20.28
cd /opt/kpi-bot
```

---

## 13. .ENV FAYL TUZILISHI

```env
BOT_TOKEN=...                    # Telegram Bot token (@BotFather dan)
FOUNDER_ID=...                   # Founder Telegram User ID
MARKETING_ID=...                 # Marketing xodim ID
SALES_ID=...                     # Sales xodim ID
DIRECT_MANAGER_ID=...            # Direct Manager ID
SPREADSHEET_ID=...               # Google Sheets ID (URL dan)
SERVICE_ACCOUNT_FILE=service_account.json
GDRIVE_FOLDER_ID=...             # Google Drive folder ID (ixtiyoriy)
DASHBOARD_USER=rahbarlarkursi    # Dashboard login
DASHBOARD_PASS=zafar1234         # Dashboard parol
DASHBOARD_SECRET=...             # Flask session secret key
```

---

## 14. MUHIM MA'LUMOTLAR JADVALI

| Narsa | Qiymat |
|-------|--------|
| Server IP | `159.223.20.28` |
| Domen | `rahbarlarkursi.duckdns.org` |
| Dashboard URL | `https://rahbarlarkursi.duckdns.org` |
| Mini App URL | `https://rahbarlarkursi.duckdns.org/miniapp` |
| Dashboard login | `rahbarlarkursi` |
| Dashboard parol | `zafar1234` |
| Bot fayllari | `/opt/kpi-bot/` |
| Bot venv | `/opt/kpi-bot/venv/` |
| Nginx config | `/etc/nginx/sites-available/kpi` |
| SSL sertifikat | `/etc/letsencrypt/live/rahbarlarkursi.duckdns.org/` |
| Service account | `metrics-bot@cool-ship-463908-j3.iam.gserviceaccount.com` |
| Google Cloud Project | `cool-ship-463908-j3` |

---

## 15. TIZIMNI QAYTA ISHGA TUSHIRISH (YANGI SERVERDA)

```bash
# 1. Python muhitini yaratish
python3 -m venv /opt/kpi-bot/venv
source /opt/kpi-bot/venv/bin/activate
pip install -r requirements.txt

# 2. .env faylini to'ldirish
nano /opt/kpi-bot/.env

# 3. Service account kalitini joylashtirish
# service_account.json ni /opt/kpi-bot/ ga ko'chirish

# 4. Systemd xizmatlarini faollashtirish
sudo systemctl enable kpi-bot kpi-dashboard
sudo systemctl start kpi-bot kpi-dashboard

# 5. Nginx va SSL
sudo certbot --nginx -d rahbarlarkursi.duckdns.org
sudo systemctl reload nginx
```

---

*Hujjat yaratilgan: 2026-04-16*
