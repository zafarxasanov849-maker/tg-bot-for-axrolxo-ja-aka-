"""Seminar funnel data-collection handler."""
from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from states import SeminarStates
from handlers._base import (
    ask_screenshot,
    build_raw_row,
    check_anomaly_and_proceed,
    handle_screenshot_upload,
    parse_positive_number,
    sheets_service,
)

router = Router()

FUNNEL = "Seminar"


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


@router.message(SeminarStates.ad_spend)
async def sem_ad_spend(message: Message, state: FSMContext, role: str) -> None:
    value = await _num(message, state, "ad_spend")
    if value is None:
        return
    await check_anomaly_and_proceed(
        message, state, FUNNEL, "ad_spend", value,
        SeminarStates.registrations,
        "Ro'yxatdan o'tganlar soni (Registrations):",
        SeminarStates.anomaly_explanation,
    )


@router.message(SeminarStates.anomaly_explanation)
async def sem_anomaly_explanation(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.update_data(anomaly_explanation=message.text, anomaly_flag=True)
    state_map = {
        SeminarStates.registrations.__state__: SeminarStates.registrations,
        SeminarStates.show_up.__state__: SeminarStates.show_up,
        SeminarStates.deposits.__state__: SeminarStates.deposits,
        SeminarStates.sales.__state__: SeminarStates.sales,
        SeminarStates.full_payments.__state__: SeminarStates.full_payments,
    }
    next_state = state_map.get(data.get("anomaly_next_state"), SeminarStates.registrations)
    await state.set_state(next_state)
    await message.answer(data.get("anomaly_next_prompt", "Davom eting:"))


@router.message(SeminarStates.registrations)
async def sem_registrations(message: Message, state: FSMContext, role: str) -> None:
    value = await _num(message, state, "registrations")
    if value is None:
        return
    await check_anomaly_and_proceed(
        message, state, FUNNEL, "registrations", value,
        SeminarStates.show_up,
        "Kelganlar soni (Show-up Count):",
        SeminarStates.anomaly_explanation,
    )


@router.message(SeminarStates.show_up)
async def sem_show_up(message: Message, state: FSMContext, role: str) -> None:
    value = await _num(message, state, "show_up")
    if value is None:
        return
    await check_anomaly_and_proceed(
        message, state, FUNNEL, "show_up", value,
        SeminarStates.deposits,
        "Depozit to'laganlar soni (Deposits):",
        SeminarStates.anomaly_explanation,
    )


@router.message(SeminarStates.deposits)
async def sem_deposits(message: Message, state: FSMContext, role: str) -> None:
    value = await _num(message, state, "deposits")
    if value is None:
        return
    await check_anomaly_and_proceed(
        message, state, FUNNEL, "deposits", value,
        SeminarStates.sales,
        "Sotuvlar soni (Sales):",
        SeminarStates.anomaly_explanation,
    )


@router.message(SeminarStates.sales)
async def sem_sales(message: Message, state: FSMContext, role: str) -> None:
    value = await _num(message, state, "sales_count")
    if value is None:
        return
    await check_anomaly_and_proceed(
        message, state, FUNNEL, "sales_count", value,
        SeminarStates.full_payments,
        "To'liq to'lovlar soni (Full Payments):",
        SeminarStates.anomaly_explanation,
    )


@router.message(SeminarStates.full_payments)
async def sem_full_payments(message: Message, state: FSMContext, role: str) -> None:
    value = await _num(message, state, "full_payments")
    if value is None:
        return
    await state.set_state(SeminarStates.screenshot)
    await ask_screenshot(message)


@router.message(SeminarStates.screenshot)
async def sem_screenshot(message: Message, state: FSMContext, role: str) -> None:
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
            "registrations": data.get("registrations", 0),
            "show_up": data.get("show_up", 0),
            "deposits": data.get("deposits", 0),
            "sales_count": data.get("sales_count", 0),
            "full_payments": data.get("full_payments", 0),
        },
        screenshot_url=url,
        anomaly_flag=bool(data.get("anomaly_flag", False)),
        anomaly_explanation=data.get("anomaly_explanation", ""),
    )

    await sheets_service.append_raw(row)
    await sheets_service.rebuild_daily_summary()
    await state.clear()

    ad_spend = float(data.get("ad_spend", 0))
    registrations = int(data.get("registrations", 0))
    sales_count = int(data.get("sales_count", 0))
    show_up = int(data.get("show_up", 0))

    show_rate = round(show_up / registrations * 100, 1) if registrations else 0
    conv_rate = round(sales_count / show_up * 100, 1) if show_up else 0
    cac = round(ad_spend / sales_count, 0) if sales_count else 0

    await message.answer(
        "✅ *Seminar hisobot saqlandi!*\n\n"
        f"💸 Ad Spend: `{ad_spend:,.0f}` so'm\n"
        f"📋 Registrations: `{registrations}`\n"
        f"🧑‍🤝‍🧑 Show-up: `{show_up}` ({show_rate}%)\n"
        f"💰 Sales: `{sales_count}`\n"
        f"📊 Conv Rate: `{conv_rate}%` | CAC: `{cac:,.0f}` so'm\n\n"
        "Yangi hisobot uchun /start bosing.",
        parse_mode="Markdown",
    )
