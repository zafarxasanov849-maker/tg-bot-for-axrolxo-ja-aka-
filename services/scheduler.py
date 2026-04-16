"""
APScheduler-based reminder system.

20:00 (local time) → nudge each reporter who hasn't submitted today.
21:00 (local time) → escalate missing reports to FOUNDER.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

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
    FINAL_NUDGE_HOUR,
    FINAL_NUDGE_MINUTE,
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

    scheduler.add_job(
        _final_nudge,
        CronTrigger(hour=FINAL_NUDGE_HOUR, minute=FINAL_NUDGE_MINUTE, timezone=TIMEZONE),
        args=[bot, sheets],
        id="final_nudge",
        replace_existing=True,
    )

    # 09:00 — kunlik hisobot Founder ga
    scheduler.add_job(
        _daily_report,
        CronTrigger(hour=9, minute=0, timezone=TIMEZONE),
        args=[bot, sheets],
        id="daily_report",
        replace_existing=True,
    )

    # Dushanba 09:00 — haftalik hisobot
    scheduler.add_job(
        _weekly_report,
        CronTrigger(day_of_week="mon", hour=9, minute=0, timezone=TIMEZONE),
        args=[bot, sheets],
        id="weekly_report",
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


async def _final_nudge(bot: Bot, sheets) -> None:
    """23:50 — oxirgi eslatma. Kiritmaganlar + Founder ga xabar."""
    today = date.today().isoformat()
    submitted_ids = await sheets.get_submitted_reporter_ids(today)

    missing = [(name, uid) for name, uid in REPORTERS.items() if uid not in submitted_ids]
    if not missing:
        return

    # Kiritmaganlarga shaxsiy xabar
    for name, uid in missing:
        try:
            await bot.send_message(
                uid,
                f"🚨 *Oxirgi eslatma! 23:50*\n\n"
                f"Bugun ({today}) hisobotingiz hali kiritilmagan!\n"
                f"Kun tugashidan oldin kiriting 👇\n\n"
                f"/start",
                parse_mode="Markdown",
            )
        except Exception as exc:
            logger.warning("Could not final-nudge %s: %s", name, exc)

    # Founder ga ham xabar
    names_str = "\n".join(f"  • {n}" for n, _ in missing)
    try:
        await bot.send_message(
            FOUNDER_ID,
            f"🚨 *23:50 — Hisobot kiritilmadi!*\n"
            f"Sana: {today}\n\n"
            f"Quyidagilar hali hisobot bermagandi:\n{names_str}\n\n"
            f"Tez orada kiritishlari kerak.",
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.warning("Could not notify founder at final nudge: %s", exc)


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


def _fmt(n) -> str:
    try:
        v = float(n)
        if v >= 1_000_000:
            return f"{v/1_000_000:.1f}M"
        if v >= 1_000:
            return f"{v/1_000:.0f}K"
        return f"{v:,.0f}"
    except (TypeError, ValueError):
        return "—"


async def _daily_report(bot: Bot, sheets) -> None:
    """09:00 — kecha (yesterday) kunlik hisobot Founder ga."""
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    try:
        ss = sheets._connect()
        ws = ss.worksheet("Daily_Summary")
        records = ws.get_all_records()
        row = next((r for r in records if r.get("date") == yesterday), None)
        if not row:
            return
        await bot.send_message(
            FOUNDER_ID,
            f"☀️ *Kunlik hisobot* — {yesterday}\n\n"
            f"💸 Ad Spend: `{_fmt(row.get('total_ad_spend'))}` so'm\n"
            f"👥 Leads: `{_fmt(row.get('total_leads'))}`\n"
            f"💰 Sotuvlar: `{_fmt(row.get('total_sales'))}`\n"
            f"💵 Daromad: `{_fmt(row.get('total_revenue'))}` so'm\n"
            f"📈 CAC: `{_fmt(row.get('blended_cac'))}` so'm\n"
            f"🏆 Avg LTV: `{_fmt(row.get('avg_ltv'))}` so'm\n\n"
            f"🎯 VSL: `{row.get('vsl_conv_rate', 0)}%` | "
            f"LM: `{row.get('lm_conv_rate', 0)}%` | "
            f"Seminar: `{row.get('seminar_conv_rate', 0)}%`",
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.warning("Daily report error: %s", exc)


async def _weekly_report(bot: Bot, sheets) -> None:
    """Dushanba 09:00 — haftalik summary."""
    today = date.today()
    week_ago = (today - timedelta(days=7)).isoformat()
    try:
        ss = sheets._connect()
        ws = ss.worksheet("Daily_Summary")
        records = [r for r in ws.get_all_records() if r.get("date", "") >= week_ago]
        if not records:
            return

        def s(f):
            return sum(float(r.get(f, 0) or 0) for r in records)

        spend = s("total_ad_spend")
        leads = s("total_leads")
        sales = s("total_sales")
        revenue = s("total_revenue")
        cac = round(spend / sales, 0) if sales else 0
        days = len(records)

        await bot.send_message(
            FOUNDER_ID,
            f"📅 *Haftalik hisobot* (oxirgi 7 kun)\n\n"
            f"💸 Jami Ad Spend: `{_fmt(spend)}` so'm\n"
            f"👥 Jami Leads: `{_fmt(leads)}`\n"
            f"💰 Jami Sotuvlar: `{_fmt(sales)}`\n"
            f"💵 Jami Daromad: `{_fmt(revenue)}` so'm\n"
            f"📈 O'rtacha CAC: `{_fmt(cac)}` so'm\n\n"
            f"📆 Kunlik o'rtacha sotuv: `{_fmt(sales/days if days else 0)}`\n"
            f"📆 Kunlik o'rtacha daromad: `{_fmt(revenue/days if days else 0)}` so'm",
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.warning("Weekly report error: %s", exc)


def start_scheduler(bot: Bot, sheets) -> AsyncIOScheduler:
    scheduler = _build_scheduler(bot, sheets)
    scheduler.start()
    logger.info("Scheduler started (tz=%s)", TIMEZONE)
    return scheduler
