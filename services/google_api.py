"""
Google Sheets & Google Drive integration.
All writes are appended to Raw_Data and the derived sheets are recalculated
via formula-based tabs (Funnel_Performance, LTV_Cohort, Daily_Summary).
"""
from __future__ import annotations

import asyncio
import io
import logging
from datetime import date, datetime
from typing import Any

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from config import (
    GDRIVE_FOLDER_ID,
    SERVICE_ACCOUNT_FILE,
    SHEET_DAILY_SUMMARY,
    SHEET_FUNNEL_PERFORMANCE,
    SHEET_LTV_COHORT,
    SHEET_RAW_DATA,
    SPREADSHEET_ID,
)

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Raw_Data column order
RAW_HEADERS = [
    "timestamp", "date", "reporter_id", "reporter_role",
    "funnel_type",
    # VSL
    "ad_spend", "page_views", "video_start", "watch_50", "watch_100", "cta_clicks",
    # Lead Magnet
    "lp_views", "new_leads", "contacted",
    # Seminar
    "registrations", "show_up", "deposits", "sales_count", "full_payments",
    # Sales / LTV
    "customer_id", "funnel_source", "tariff_type", "price",
    "customer_type", "lead_status",
    # Meta
    "screenshot_url", "anomaly_flag", "anomaly_explanation",
]


def _get_credentials() -> Credentials:
    return Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)


class GoogleSheetsService:
    def __init__(self) -> None:
        self._client: gspread.Client | None = None
        self._spreadsheet: gspread.Spreadsheet | None = None

    def _connect(self) -> gspread.Spreadsheet:
        if self._spreadsheet is None:
            creds = _get_credentials()
            self._client = gspread.authorize(creds)
            self._spreadsheet = self._client.open_by_key(SPREADSHEET_ID)
        return self._spreadsheet

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    async def ensure_tabs(self) -> None:
        """Create missing tabs and write headers on first run."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._ensure_tabs_sync)

    def _ensure_tabs_sync(self) -> None:
        ss = self._connect()
        existing = {ws.title for ws in ss.worksheets()}

        tabs_headers: dict[str, list[str]] = {
            SHEET_RAW_DATA: RAW_HEADERS,
            SHEET_FUNNEL_PERFORMANCE: [
                "date", "funnel_type", "ad_spend", "leads_or_views",
                "cpl", "conversions", "cac", "conv_rate_pct",
            ],
            SHEET_LTV_COHORT: [
                "customer_id", "first_funnel", "first_purchase_date",
                "total_revenue", "purchase_count", "ltv",
            ],
            SHEET_DAILY_SUMMARY: [
                "date", "total_ad_spend", "total_leads", "total_sales",
                "total_revenue", "blended_cac", "avg_ltv",
                "vsl_conv_rate", "lm_conv_rate", "seminar_conv_rate",
            ],
        }

        for title, headers in tabs_headers.items():
            if title not in existing:
                ws = ss.add_worksheet(title=title, rows=5000, cols=len(headers))
                ws.append_row(headers, value_input_option="RAW")
                logger.info("Created tab: %s", title)

    async def append_raw(self, row: dict[str, Any]) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._append_raw_sync, row)

    def _append_raw_sync(self, row: dict[str, Any]) -> None:
        ss = self._connect()
        ws = ss.worksheet(SHEET_RAW_DATA)
        values = [str(row.get(h, "")) for h in RAW_HEADERS]
        ws.append_row(values, value_input_option="USER_ENTERED")

    async def get_last_7_days(self, funnel_type: str, field: str) -> list[float]:
        """Return the last 7 non-empty values for an anomaly check."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._get_last_7_sync, funnel_type, field
        )

    def _get_last_7_sync(self, funnel_type: str, field: str) -> list[float]:
        ss = self._connect()
        ws = ss.worksheet(SHEET_RAW_DATA)
        records = ws.get_all_records()

        values: list[float] = []
        for r in reversed(records):
            if r.get("funnel_type") == funnel_type:
                val = r.get(field)
                try:
                    fval = float(val)
                    if fval > 0:
                        values.append(fval)
                except (TypeError, ValueError):
                    pass
            if len(values) == 7:
                break
        return values

    async def upsert_ltv_cohort(self, sale: dict[str, Any]) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._upsert_ltv_sync, sale)

    def _upsert_ltv_sync(self, sale: dict[str, Any]) -> None:
        ss = self._connect()
        ws = ss.worksheet(SHEET_LTV_COHORT)
        records = ws.get_all_records()

        cid = str(sale["customer_id"])
        price = float(sale.get("price", 0))
        today = date.today().isoformat()

        for i, r in enumerate(records, start=2):  # row 1 = header
            if str(r.get("customer_id")) == cid:
                new_total = float(r.get("total_revenue", 0)) + price
                new_count = int(r.get("purchase_count", 0)) + 1
                ws.update(f"D{i}", [[new_total]])
                ws.update(f"E{i}", [[new_count]])
                ws.update(f"F{i}", [[round(new_total / new_count, 2)]])
                return

        # New customer
        ws.append_row([
            cid,
            sale.get("funnel_source", ""),
            today,
            price,
            1,
            price,
        ], value_input_option="USER_ENTERED")

    async def get_submitted_reporter_ids(self, target_date: str) -> set[int]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_submitted_ids_sync, target_date)

    def _get_submitted_ids_sync(self, target_date: str) -> set[int]:
        ss = self._connect()
        ws = ss.worksheet(SHEET_RAW_DATA)
        records = ws.get_all_records()
        ids: set[int] = set()
        for r in records:
            if r.get("date") == target_date:
                try:
                    ids.add(int(r["reporter_id"]))
                except (ValueError, TypeError):
                    pass
        return ids

    async def rebuild_daily_summary(self, target_date: str | None = None) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._rebuild_summary_sync, target_date)

    def _rebuild_summary_sync(self, target_date: str | None) -> None:
        ss = self._connect()
        raw_ws = ss.worksheet(SHEET_RAW_DATA)
        summary_ws = ss.worksheet(SHEET_DAILY_SUMMARY)

        td = target_date or date.today().isoformat()
        records = [r for r in raw_ws.get_all_records() if r.get("date") == td]

        if not records:
            return

        def safe_float(v: Any) -> float:
            try:
                return float(v) if v != "" else 0.0
            except (ValueError, TypeError):
                return 0.0

        total_spend = sum(safe_float(r.get("ad_spend")) for r in records)
        total_leads = sum(safe_float(r.get("new_leads")) for r in records)
        total_sales = sum(safe_float(r.get("sales_count")) for r in records)
        total_revenue = sum(safe_float(r.get("price")) for r in records)

        blended_cac = round(total_spend / total_sales, 2) if total_sales else 0

        ltv_ws = ss.worksheet(SHEET_LTV_COHORT)
        ltv_records = ltv_ws.get_all_records()
        avg_ltv = 0.0
        if ltv_records:
            ltvs = [safe_float(r.get("ltv")) for r in ltv_records]
            avg_ltv = round(sum(ltvs) / len(ltvs), 2)

        def conv(funnel: str, num_field: str, den_field: str) -> float:
            frs = [r for r in records if r.get("funnel_type") == funnel]
            num = sum(safe_float(r.get(num_field)) for r in frs)
            den = sum(safe_float(r.get(den_field)) for r in frs)
            return round(num / den * 100, 2) if den else 0.0

        vsl_conv = conv("VSL", "cta_clicks", "page_views")
        lm_conv = conv("Lead_Magnet", "new_leads", "lp_views")
        sem_conv = conv("Seminar", "sales_count", "registrations")

        # Check if date row already exists
        existing = summary_ws.get_all_records()
        for i, r in enumerate(existing, start=2):
            if r.get("date") == td:
                summary_ws.update(
                    f"B{i}:J{i}",
                    [[total_spend, total_leads, total_sales, total_revenue,
                      blended_cac, avg_ltv, vsl_conv, lm_conv, sem_conv]],
                )
                return

        summary_ws.append_row(
            [td, total_spend, total_leads, total_sales, total_revenue,
             blended_cac, avg_ltv, vsl_conv, lm_conv, sem_conv],
            value_input_option="USER_ENTERED",
        )


class GoogleDriveService:
    def __init__(self) -> None:
        self._service = None

    def _get_service(self):
        if self._service is None:
            creds = _get_credentials()
            self._service = build("drive", "v3", credentials=creds)
        return self._service

    async def upload_screenshot(
        self, file_bytes: bytes, filename: str, mime_type: str = "image/jpeg"
    ) -> str:
        """Upload bytes to GDrive and return a shareable URL."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._upload_sync, file_bytes, filename, mime_type
        )

    def _upload_sync(
        self, file_bytes: bytes, filename: str, mime_type: str
    ) -> str:
        svc = self._get_service()
        metadata = {"name": filename, "parents": [GDRIVE_FOLDER_ID]}
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type)
        file = (
            svc.files()
            .create(body=metadata, media_body=media, fields="id, webViewLink")
            .execute()
        )
        # Make it readable by anyone with the link
        svc.permissions().create(
            fileId=file["id"],
            body={"type": "anyone", "role": "reader"},
        ).execute()
        return file.get("webViewLink", "")
