"""
APScheduler-based reminder system.

20:00 (local time) → nudge each reporter who hasn't submitted today.
21:00 (local time) → escalate missing reports to FOUNDER.
"""
from __future__ import annotations

import logging
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot

from config import (
    FOUNDER_ID,
    MARKETING_ID,
    SALES_ID,
    DIRECT_MANAGER_ID,
    NUDGE_HOUR,
    ESCALATE_HOUR,
    TIMEZONE,
    SPREADSHEET_ID,
)

logger = logging.getLogger(__name__)

# Maps role display name → user id
REPORTERS: dict[str, int] = {
    "Marketing (To'lqin)": MARKETING_ID,
    "Sales (Aziz)": SALES_ID,
    "Direct Manager": DIRECT_MANAGER_ID,
}


def _build_scheduler(bot: Bot, sheets) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)

    scheduler.add_job(
        _nudge_missing,
        CronTrigger(hour=NUDGE_HOUR, minute=0, timezone=TIMEZONE),
        args=[bot, sheets],
        id="nudge",
        replace_existing=True,
    )

    scheduler.add_job(
        _escalate_missing,
        CronTrigger(hour=ESCALATE_HOUR, minute=0, timezone=TIMEZONE),
        args=[bot, sheets],
        id="escalate",
        replace_existing=True,
    )

    return scheduler


async def _missing_reporters(sheets) -> list[str]:
    today = date.today().isoformat()
    raw = await sheets._get_today_reporters(today)
    missing = []
    for name in REPORTERS:
        if name not in raw:
            missing.append(name)
    return missing


async def _nudge_missing(bot: Bot, sheets) -> None:
    today = date.today().isoformat()
    submitted_ids = await sheets.get_submitted_reporter_ids(today)

    for name, uid in REPORTERS.items():
        if uid not in submitted_ids:
            try:
                await bot.send_message(
                    uid,
                    f"⏰ *Eslatma!*\n"
                    f"Bugun ({today}) hisobotingizni hali topshirmadingiz.\n"
                    f"Iltimos, /start bosib hisobot yuboring.",
                    parse_mode="Markdown",
                )
                logger.info("Nudged %s (%s)", name, uid)
            except Exception as exc:
                logger.warning("Could not nudge %s: %s", name, exc)


async def _escalate_missing(bot: Bot, sheets) -> None:
    today = date.today().isoformat()
    submitted_ids = await sheets.get_submitted_reporter_ids(today)

    missing_names = [
        name for name, uid in REPORTERS.items() if uid not in submitted_ids
    ]

    if not missing_names:
        return

    names_str = "\n".join(f"  • {n}" for n in missing_names)
    try:
        await bot.send_message(
            FOUNDER_ID,
            f"🚨 *Hisobot topshirilmadi!*\n"
            f"Sana: {today}\n\n"
            f"Quyidagilar hisobot bermadi:\n{names_str}",
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.warning("Could not escalate to founder: %s", exc)


def start_scheduler(bot: Bot, sheets) -> AsyncIOScheduler:
    scheduler = _build_scheduler(bot, sheets)
    scheduler.start()
    logger.info("Scheduler started (tz=%s)", TIMEZONE)
    return scheduler
