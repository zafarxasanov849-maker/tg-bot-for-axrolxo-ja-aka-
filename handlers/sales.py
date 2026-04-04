"""Sales & LTV tracking handler."""
from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    CallbackQuery,
)

from states import SalesStates
from handlers._base import (
    ask_screenshot,
    build_raw_row,
    handle_screenshot_upload,
    parse_positive_number,
    sheets_service,
)
from config import FOUNDER_ID

router = Router()

FUNNEL_SOURCE_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📹 VSL", callback_data="src:VSL")],
        [InlineKeyboardButton(text="🧲 Lead Magnet", callback_data="src:Lead_Magnet")],
        [InlineKeyboardButton(text="🎓 Seminar", callback_data="src:Seminar")],
        [InlineKeyboardButton(text="🔄 Organik / Referral", callback_data="src:Organic")],
    ]
)

CUSTOMER_TYPE_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🆕 Yangi mijoz", callback_data="ct:new")],
        [InlineKeyboardButton(text="🔁 Upsell", callback_data="ct:upsell")],
        [InlineKeyboardButton(text="♻️ Qayta xaridor (Recurring)", callback_data="ct:recurring")],
    ]
)

# Tizimchiman kursi aniq tariflari
TARIFF_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(
            text="⭐ Standart — 24 000 000 so'm",
            callback_data="tariff:Standart:24000000",
        )],
        [InlineKeyboardButton(
            text="💎 Premium — 30 000 000 so'm",
            callback_data="tariff:Premium:30000000",
        )],
        [InlineKeyboardButton(
            text="✏️ Boshqa summa (qo'lda kiritish)",
            callback_data="tariff:custom:0",
        )],
    ]
)

# Lead holati (kvalifikatsiya natijasi)
LEAD_STATUS_KB = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Issiq — Audit taklif qilindi", callback_data="ls:hot")],
        [InlineKeyboardButton(text="🌡 Iliq — Nurturing kerak", callback_data="ls:warm")],
        [InlineKeyboardButton(text="❄️ Sovuq — Tayyor emas", callback_data="ls:cold")],
    ]
)


@router.message(SalesStates.customer_id)
async def sales_customer_id(message: Message, state: FSMContext, role: str) -> None:
    await state.update_data(customer_id=message.text.strip())
    await state.set_state(SalesStates.funnel_source)
    await message.answer(
        "Mijoz qaysi voronkadan keldi?",
        reply_markup=FUNNEL_SOURCE_KB,
    )


@router.callback_query(lambda c: c.data and c.data.startswith("src:"))
async def sales_funnel_source(callback: CallbackQuery, state: FSMContext, role: str) -> None:
    source = callback.data.split(":")[1]
    await state.update_data(funnel_source=source)
    await state.set_state(SalesStates.tariff_type)
    await callback.answer()
    await callback.message.edit_text(
        "Tarif turini tanlang:",
        reply_markup=TARIFF_KB,
    )


@router.callback_query(lambda c: c.data and c.data.startswith("tariff:"))
async def sales_tariff_callback(callback: CallbackQuery, state: FSMContext, role: str) -> None:
    parts = callback.data.split(":")
    tariff_name = parts[1]
    tariff_price = parts[2]
    await callback.answer()

    if tariff_name == "custom":
        await state.set_state(SalesStates.price)
        await callback.message.edit_text("Sotuv summasini kiriting (so'm):")
    else:
        await state.update_data(tariff_type=tariff_name, price=float(tariff_price))
        await state.set_state(SalesStates.customer_type)
        await callback.message.edit_text(
            f"Tarif: *{tariff_name}* — `{int(tariff_price):,}` so'm\n\nMijoz turi:",
            reply_markup=CUSTOMER_TYPE_KB,
            parse_mode="Markdown",
        )


@router.message(SalesStates.tariff_type)
async def sales_tariff_type(message: Message, state: FSMContext, role: str) -> None:
    await state.update_data(tariff_type=message.text.strip())
    await state.set_state(SalesStates.price)
    await message.answer("Sotuv summasi (so'm):")


@router.message(SalesStates.price)
async def sales_price(message: Message, state: FSMContext, role: str) -> None:
    try:
        value, corrected = parse_positive_number(message.text)
    except (ValueError, TypeError):
        await message.answer("❌ Iltimos, raqam kiriting.")
        return
    await state.update_data(price=value)
    if corrected:
        await message.answer(
            f"⚠️ Manfiy qiymat kiritdingiz. Avtomatik tuzatildi: *{value}*",
            parse_mode="Markdown",
        )
    await state.set_state(SalesStates.customer_type)
    await message.answer(
        "Mijoz turi:",
        reply_markup=CUSTOMER_TYPE_KB,
    )


@router.callback_query(lambda c: c.data and c.data.startswith("ct:"))
async def sales_customer_type(
    callback: CallbackQuery, state: FSMContext, role: str
) -> None:
    ct_map = {"new": "Yangi", "upsell": "Upsell", "recurring": "Recurring"}
    ct = callback.data.split(":")[1]
    await state.update_data(customer_type=ct)
    await state.set_state(SalesStates.lead_status)
    await callback.answer()
    await callback.message.edit_text(
        f"Mijoz turi: *{ct_map.get(ct, ct)}*\n\nLead holati (kvalifikatsiya):",
        reply_markup=LEAD_STATUS_KB,
        parse_mode="Markdown",
    )


@router.callback_query(lambda c: c.data and c.data.startswith("ls:"))
async def sales_lead_status(
    callback: CallbackQuery, state: FSMContext, role: str
) -> None:
    ls_map = {"hot": "Issiq", "warm": "Iliq", "cold": "Sovuq"}
    ls = callback.data.split(":")[1]
    await state.update_data(lead_status=ls)
    await state.set_state(SalesStates.screenshot)
    await callback.answer()
    await callback.message.edit_text(
        f"Lead holati: *{ls_map.get(ls, ls)}*", parse_mode="Markdown"
    )
    await ask_screenshot(callback.message)


@router.message(SalesStates.screenshot)
async def sales_screenshot(message: Message, state: FSMContext, role: str) -> None:
    url = ""
    if message.photo:
        url = await handle_screenshot_upload(message, state)
        await message.answer(f"✅ Screenshot saqlandi: {url}" if url else "✅ Screenshot qabul qilindi.")
    else:
        await message.answer("⚠️ Screenshot topilmadi, davom etilmoqda.")

    data = await state.get_data()
    ls_map = {"hot": "Issiq", "warm": "Iliq", "cold": "Sovuq"}
    row = build_raw_row(
        user_id=message.from_user.id,
        role=role,
        funnel_type="Sales",
        data={
            "customer_id": data.get("customer_id", ""),
            "funnel_source": data.get("funnel_source", ""),
            "tariff_type": data.get("tariff_type", ""),
            "price": data.get("price", 0),
            "customer_type": data.get("customer_type", ""),
            "lead_status": data.get("lead_status", ""),
        },
        screenshot_url=url,
    )

    await sheets_service.append_raw(row)
    await sheets_service.upsert_ltv_cohort({
        "customer_id": data.get("customer_id"),
        "funnel_source": data.get("funnel_source"),
        "price": data.get("price", 0),
    })
    await sheets_service.rebuild_daily_summary()
    await state.clear()

    price = float(data.get("price", 0))
    ct_map = {"new": "Yangi", "upsell": "Upsell", "recurring": "Recurring"}
    ls_labels = {"hot": "Issiq", "warm": "Iliq", "cold": "Sovuq"}
    ct_label = ct_map.get(data.get("customer_type", ""), data.get("customer_type", ""))
    ls_label = ls_labels.get(data.get("lead_status", ""), data.get("lead_status", ""))

    # Notify founder of new sale
    try:
        await message.bot.send_message(
            FOUNDER_ID,
            f"💰 *Yangi sotuv qayd etildi!*\n\n"
            f"👤 Mijoz ID: `{data.get('customer_id')}`\n"
            f"📌 Manba: {data.get('funnel_source')}\n"
            f"🎯 Tarif: {data.get('tariff_type')}\n"
            f"💵 Summa: `{price:,.0f}` so'm\n"
            f"🏷 Tur: {ct_label}\n"
            f"🌡 Lead holati: {ls_label}",
            parse_mode="Markdown",
        )
    except Exception:
        pass

    await message.answer(
        "✅ *Sotuv qayd etildi!*\n\n"
        f"👤 Mijoz: `{data.get('customer_id')}`\n"
        f"📌 Manba: {data.get('funnel_source')}\n"
        f"🎯 Tarif: {data.get('tariff_type')}\n"
        f"💵 Summa: `{price:,.0f}` so'm\n"
        f"🏷 Tur: {ct_label}\n"
        f"🌡 Lead holati: {ls_label}\n\n"
        "LTV Cohort jadvaliga qo'shildi.\n"
        "Yangi hisobot uchun /start bosing.",
        parse_mode="Markdown",
    )
