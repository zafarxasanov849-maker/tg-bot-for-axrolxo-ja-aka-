"""Lead Magnet funnel data-collection handler."""
from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from states import LeadMagnetStates
from handlers._base import (
    ask_screenshot,
    build_raw_row,
    check_anomaly_and_proceed,
    handle_screenshot_upload,
    parse_positive_number,
    sheets_service,
)

router = Router()

FUNNEL = "Lead_Magnet"


async def _num(message: Message, state: FSMContext, key: str) -> float | None:
    try:
        value, corrected = parse_positive_number(message.text)
    except (ValueError, TypeError):
        await message.answer("❌ Iltimos, raqam kiriting.")
        return None
    await state.update_data(**{key: value})
    if corrected:
        await message.answer(
            f"⚠️ Manfiy qiymat kiritdingiz. Avtomatik tuzatildi: *{value}*",
            parse_mode="Markdown",
        )
    return value


@router.message(LeadMagnetStates.ad_spend)
async def lm_ad_spend(message: Message, state: FSMContext, role: str) -> None:
    value = await _num(message, state, "ad_spend")
    if value is None:
        return
    await check_anomaly_and_proceed(
        message, state, FUNNEL, "ad_spend", value,
        LeadMagnetStates.lp_views,
        "Landing Page ko'rishlar soni (LP Views):",
        LeadMagnetStates.anomaly_explanation,
    )


@router.message(LeadMagnetStates.anomaly_explanation)
async def lm_anomaly_explanation(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.update_data(anomaly_explanation=message.text, anomaly_flag=True)
    next_state_str = data.get("anomaly_next_state")
    state_map = {
        LeadMagnetStates.lp_views.__state__: LeadMagnetStates.lp_views,
        LeadMagnetStates.new_leads.__state__: LeadMagnetStates.new_leads,
        LeadMagnetStates.contacted.__state__: LeadMagnetStates.contacted,
    }
    next_state = state_map.get(next_state_str, LeadMagnetStates.lp_views)
    await state.set_state(next_state)
    await message.answer(data.get("anomaly_next_prompt", "Davom eting:"))


@router.message(LeadMagnetStates.lp_views)
async def lm_lp_views(message: Message, state: FSMContext, role: str) -> None:
    value = await _num(message, state, "lp_views")
    if value is None:
        return
    await check_anomaly_and_proceed(
        message, state, FUNNEL, "lp_views", value,
        LeadMagnetStates.new_leads,
        "Yangi lidlar soni (New Leads):",
        LeadMagnetStates.anomaly_explanation,
    )


@router.message(LeadMagnetStates.new_leads)
async def lm_new_leads(message: Message, state: FSMContext, role: str) -> None:
    value = await _num(message, state, "new_leads")
    if value is None:
        return
    await check_anomaly_and_proceed(
        message, state, FUNNEL, "new_leads", value,
        LeadMagnetStates.contacted,
        "Bog'lanilgan lidlar soni (Contacted):",
        LeadMagnetStates.anomaly_explanation,
    )


@router.message(LeadMagnetStates.contacted)
async def lm_contacted(message: Message, state: FSMContext, role: str) -> None:
    value = await _num(message, state, "contacted")
    if value is None:
        return
    await state.set_state(LeadMagnetStates.screenshot)
    await ask_screenshot(message)


@router.message(LeadMagnetStates.screenshot)
async def lm_screenshot(message: Message, state: FSMContext, role: str) -> None:
    url = ""
    if message.photo:
        url = await handle_screenshot_upload(message, state)
        await message.answer(f"✅ Screenshot saqlandi: {url}" if url else "✅ Screenshot qabul qilindi.")
    else:
        await message.answer("⚠️ Screenshot topilmadi, matn sifatida davom etilmoqda.")

    data = await state.get_data()
    row = build_raw_row(
        user_id=message.from_user.id,
        role=role,
        funnel_type=FUNNEL,
        data={
            "ad_spend": data.get("ad_spend", 0),
            "lp_views": data.get("lp_views", 0),
            "new_leads": data.get("new_leads", 0),
            "contacted": data.get("contacted", 0),
        },
        screenshot_url=url,
        anomaly_flag=bool(data.get("anomaly_flag", False)),
        anomaly_explanation=data.get("anomaly_explanation", ""),
    )

    await sheets_service.append_raw(row)
    await sheets_service.rebuild_daily_summary()
    await state.clear()

    ad_spend = float(data.get("ad_spend", 0))
    new_leads = int(data.get("new_leads", 0))
    cpl = round(ad_spend / new_leads, 0) if new_leads else 0

    await message.answer(
        "✅ *Lead Magnet hisobot saqlandi!*\n\n"
        f"💸 Ad Spend: `{ad_spend:,.0f}` so'm\n"
        f"👥 New Leads: `{new_leads}`\n"
        f"📞 Contacted: `{int(data.get('contacted', 0))}`\n"
        f"📊 CPL: `{cpl:,.0f}` so'm\n\n"
        "Yangi hisobot uchun /start bosing.",
        parse_mode="Markdown",
    )
