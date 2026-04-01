"""
Shared helpers used across all funnel handlers.
"""
from __future__ import annotations

import logging
from datetime import date, datetime

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from services.anomaly_detector import AnomalyDetector
from services.google_api import GoogleDriveService, GoogleSheetsService

logger = logging.getLogger(__name__)

sheets_service = GoogleSheetsService()
drive_service = GoogleDriveService()
anomaly_detector = AnomalyDetector(sheets_service)


def parse_positive_number(text: str) -> tuple[float, bool]:
    """
    Parse a number from user text.
    Returns (value, was_corrected).
    was_corrected is True if abs() was applied.
    """
    text = text.strip().replace(",", ".").replace(" ", "")
    value = float(text)
    if value < 0:
        return abs(value), True
    return value, False


async def ask_screenshot(message: Message) -> None:
    await message.answer(
        "📸 Iltimos, dalil sifatida *screenshot* yuboring "
        "(reklama kabineti, CRM yoki boshqa tizimdan).",
        parse_mode="Markdown",
    )


async def handle_screenshot_upload(
    message: Message, state: FSMContext, context_key: str = "screenshot_url"
) -> str:
    """
    Download the photo from the message, upload to GDrive, return URL.
    """
    if not message.photo:
        return ""
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    file_bytes = await message.bot.download_file(file.file_path)
    today = date.today().isoformat()
    filename = f"screenshot_{today}_{photo.file_unique_id}.jpg"
    url = await drive_service.upload_screenshot(file_bytes.read(), filename)
    await state.update_data(**{context_key: url})
    return url


async def check_anomaly_and_proceed(
    message: Message,
    state: FSMContext,
    funnel_type: str,
    field: str,
    value: float,
    next_state,
    next_prompt: str,
    anomaly_state,
) -> None:
    """
    Runs anomaly check; if triggered asks for explanation, else advances state.
    """
    is_anomaly, avg, dev_pct = await anomaly_detector.check(funnel_type, field, value)
    if is_anomaly:
        await state.update_data(
            anomaly_field=field,
            anomaly_value=value,
            anomaly_avg=avg,
            anomaly_dev_pct=dev_pct,
            anomaly_next_state=next_state.__state__,
            anomaly_next_prompt=next_prompt,
        )
        await state.set_state(anomaly_state)
        await message.answer(
            f"⚠️ *Anomaliya aniqlandi!*\n\n"
            f"Kiritilgan qiymat: *{value}*\n"
            f"7 kunlik o'rtacha: *{avg}*\n"
            f"Og'ish: *{dev_pct}%*\n\n"
            f"Iltimos, bu farqni izohlang:",
            parse_mode="Markdown",
        )
    else:
        await state.set_state(next_state)
        await message.answer(next_prompt)


def build_raw_row(
    user_id: int,
    role: str,
    funnel_type: str,
    data: dict,
    screenshot_url: str = "",
    anomaly_flag: bool = False,
    anomaly_explanation: str = "",
) -> dict:
    now = datetime.utcnow()
    return {
        "timestamp": now.isoformat(),
        "date": date.today().isoformat(),
        "reporter_id": user_id,
        "reporter_role": role,
        "funnel_type": funnel_type,
        **data,
        "screenshot_url": screenshot_url,
        "anomaly_flag": "1" if anomaly_flag else "0",
        "anomaly_explanation": anomaly_explanation,
    }
