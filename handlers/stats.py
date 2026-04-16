"""/bugun va /hafta komandlari."""
from __future__ import annotations

from datetime import date, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from handlers._base import sheets_service

router = Router()


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


@router.message(Command("bugun"))
async def cmd_bugun(message: Message, role: str) -> None:
    today = date.today().isoformat()
    try:
        ss = sheets_service._connect()
        ws = ss.worksheet("Daily_Summary")
        records = ws.get_all_records()
        row = next((r for r in records if r.get("date") == today), None)

        if not row:
            await message.answer(
                f"📊 *Bugungi hisobot* ({today})\n\n"
                "Hali ma'lumot kiritilmagan.",
                parse_mode="Markdown",
            )
            return

        await message.answer(
            f"📊 *Bugungi KPI* — {today}\n\n"
            f"💸 Ad Spend: `{_fmt(row.get('total_ad_spend'))}` so'm\n"
            f"👥 Leads: `{_fmt(row.get('total_leads'))}`\n"
            f"💰 Sotuvlar: `{_fmt(row.get('total_sales'))}`\n"
            f"💵 Daromad: `{_fmt(row.get('total_revenue'))}` so'm\n"
            f"📈 CAC: `{_fmt(row.get('blended_cac'))}` so'm\n"
            f"🏆 Avg LTV: `{_fmt(row.get('avg_ltv'))}` so'm\n\n"
            f"🎯 VSL konversiya: `{row.get('vsl_conv_rate', 0)}%`\n"
            f"🧲 Lead Magnet: `{row.get('lm_conv_rate', 0)}%`\n"
            f"🎓 Seminar: `{row.get('seminar_conv_rate', 0)}%`",
            parse_mode="Markdown",
        )
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")


@router.message(Command("mening_hisobotim"))
async def cmd_my_report(message: Message, role: str) -> None:
    today = date.today().isoformat()
    try:
        ss = sheets_service._connect()
        ws = ss.worksheet("Raw_Data")
        records = ws.get_all_records()
        my_records = [r for r in records if str(r.get("reporter_id")) == str(message.from_user.id)]
        today_records = [r for r in my_records if r.get("date") == today]
        total_days = len(set(r.get("date") for r in my_records))

        if not my_records:
            await message.answer("Siz hali hech qanday hisobot topshirmadingiz.", parse_mode="Markdown")
            return

        status = "✅ Bugun kiritilgan" if today_records else "❌ Bugun hali kiritilmagan"
        funnels = ", ".join(set(r.get("funnel_type","") for r in today_records)) if today_records else "—"

        await message.answer(
            f"👤 *Mening hisobotim*\n\n"
            f"Bugun: {status}\n"
            f"Kiritilgan funnel: {funnels}\n\n"
            f"📆 Jami hisobot kunlari: *{total_days}*\n"
            f"📋 Jami yozuvlar: *{len(my_records)}*\n\n"
            f"Yangi hisobot: /start",
            parse_mode="Markdown",
        )
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")


@router.message(Command("hafta"))
async def cmd_hafta(message: Message, role: str) -> None:
    try:
        ss = sheets_service._connect()
        ws = ss.worksheet("Daily_Summary")
        records = ws.get_all_records()

        today = date.today()
        week_ago = (today - timedelta(days=7)).isoformat()
        week_records = [r for r in records if r.get("date", "") >= week_ago]

        if not week_records:
            await message.answer("Oxirgi 7 kunda ma'lumot yo'q.")
            return

        def s(field):
            return sum(float(r.get(field, 0) or 0) for r in week_records)

        total_spend = s("total_ad_spend")
        total_leads = s("total_leads")
        total_sales = s("total_sales")
        total_revenue = s("total_revenue")
        avg_cac = round(total_spend / total_sales, 0) if total_sales else 0

        await message.answer(
            f"📅 *Haftalik hisobot* (oxirgi 7 kun)\n\n"
            f"💸 Jami Ad Spend: `{_fmt(total_spend)}` so'm\n"
            f"👥 Jami Leads: `{_fmt(total_leads)}`\n"
            f"💰 Jami Sotuvlar: `{_fmt(total_sales)}`\n"
            f"💵 Jami Daromad: `{_fmt(total_revenue)}` so'm\n"
            f"📈 O'rtacha CAC: `{_fmt(avg_cac)}` so'm\n\n"
            f"📆 Kunlik o'rtacha sotuv: `{_fmt(total_sales/7)}`\n"
            f"📆 Kunlik o'rtacha daromad: `{_fmt(total_revenue/7)}` so'm",
            parse_mode="Markdown",
        )
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")
