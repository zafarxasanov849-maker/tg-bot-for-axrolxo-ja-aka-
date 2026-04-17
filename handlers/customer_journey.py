"""
/mijoz — individual customer journey tracking.
Reporter logs which stage a customer is at and which campaign they came from.
"""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from handlers._base import sheets_service

router = Router()


class CJStates(StatesGroup):
    customer_id  = State()
    link_token   = State()
    funnel_type  = State()
    stage        = State()
    notes        = State()


FUNNEL_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📹 VSL",          callback_data="cj_funnel:VSL")],
    [InlineKeyboardButton(text="🧲 Lead Magnet",  callback_data="cj_funnel:Lead_Magnet")],
    [InlineKeyboardButton(text="🎓 Seminar",       callback_data="cj_funnel:Seminar")],
    [InlineKeyboardButton(text="💰 To'g'ridan sotuv", callback_data="cj_funnel:Direct")],
])

STAGE_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="👁 Reklamani ko'rdi",         callback_data="cj_stage:ad_viewed")],
    [InlineKeyboardButton(text="🖱 Havolani bosdi",            callback_data="cj_stage:link_clicked")],
    [InlineKeyboardButton(text="▶️ Video ko'rdi (VSL)",        callback_data="cj_stage:video_watched")],
    [InlineKeyboardButton(text="📋 Lead bo'ldi",               callback_data="cj_stage:lead_captured")],
    [InlineKeyboardButton(text="📝 Seminar ro'yxat",           callback_data="cj_stage:seminar_registered")],
    [InlineKeyboardButton(text="🎓 Seminarga keldi",           callback_data="cj_stage:seminar_attended")],
    [InlineKeyboardButton(text="💬 Bog'lanildi (contacted)",   callback_data="cj_stage:contacted")],
    [InlineKeyboardButton(text="💰 Depozit to'ladi",           callback_data="cj_stage:deposited")],
    [InlineKeyboardButton(text="✅ Xarid qildi",               callback_data="cj_stage:purchased")],
    [InlineKeyboardButton(text="❌ Rad etdi / Ketdi",          callback_data="cj_stage:dropped_off")],
])

STAGE_LABELS: dict[str, str] = {
    "ad_viewed":            "👁 Reklamani ko'rdi",
    "link_clicked":         "🖱 Havolani bosdi",
    "video_watched":        "▶️ Video ko'rdi",
    "lead_captured":        "📋 Lead bo'ldi",
    "seminar_registered":   "📝 Seminar ro'yxat",
    "seminar_attended":     "🎓 Seminarga keldi",
    "contacted":            "💬 Bog'lanildi",
    "deposited":            "💰 Depozit",
    "purchased":            "✅ Xarid",
    "dropped_off":          "❌ Ketdi",
}

# Ordered stages for progress calculation
STAGE_ORDER = [
    "ad_viewed", "link_clicked", "video_watched", "lead_captured",
    "seminar_registered", "seminar_attended", "contacted",
    "deposited", "purchased",
]


@router.message(Command("mijoz"))
async def cmd_mijoz(message: Message, state: FSMContext, role: str) -> None:
    await state.set_state(CJStates.customer_id)
    await message.answer(
        "👤 *Mijoz kuzatuv*\n\n"
        "Mijoz ID ni kiriting (telefon raqam yoki Telegram username):",
        parse_mode="Markdown",
    )


@router.message(CJStates.customer_id)
async def cj_customer_id(message: Message, state: FSMContext, role: str) -> None:
    await state.update_data(customer_id=message.text.strip())

    try:
        links = sheets_service.get_tracking_links_sync()
    except Exception:
        links = []

    if links:
        rows = [
            [InlineKeyboardButton(
                text=f"🔗 {lnk['name']} ({lnk['source']})",
                callback_data=f"cj_link:{lnk['token']}",
            )]
            for lnk in links
        ]
        rows.append([InlineKeyboardButton(
            text="— Noma'lum / To'g'ridan",
            callback_data="cj_link:direct",
        )])
        kb = InlineKeyboardMarkup(inline_keyboard=rows)
        await state.set_state(CJStates.link_token)
        await message.answer("Mijoz qaysi havoladan keldi?", reply_markup=kb)
    else:
        await state.update_data(link_token="direct")
        await state.set_state(CJStates.funnel_type)
        await message.answer("Qaysi funnel bo'yicha?", reply_markup=FUNNEL_KB)


@router.callback_query(lambda c: c.data and c.data.startswith("cj_link:"))
async def cj_link_cb(callback: CallbackQuery, state: FSMContext, role: str) -> None:
    token = callback.data.split(":", 1)[1]
    await state.update_data(link_token=token)
    await state.set_state(CJStates.funnel_type)
    await callback.answer()
    await callback.message.edit_text("Qaysi funnel bo'yicha?", reply_markup=FUNNEL_KB)


@router.callback_query(lambda c: c.data and c.data.startswith("cj_funnel:"))
async def cj_funnel_cb(callback: CallbackQuery, state: FSMContext, role: str) -> None:
    funnel = callback.data.split(":", 1)[1]
    await state.update_data(funnel_type=funnel)
    await state.set_state(CJStates.stage)
    await callback.answer()
    await callback.message.edit_text("Mijoz hozir qaysi bosqichda?", reply_markup=STAGE_KB)


@router.callback_query(lambda c: c.data and c.data.startswith("cj_stage:"))
async def cj_stage_cb(callback: CallbackQuery, state: FSMContext, role: str) -> None:
    stage = callback.data.split(":", 1)[1]
    await state.update_data(stage=stage)
    await state.set_state(CJStates.notes)
    await callback.answer()
    await callback.message.edit_text(
        f"Bosqich: *{STAGE_LABELS.get(stage, stage)}*\n\n"
        "📝 Izoh yozing (yoki `—` deb yuboring):",
        parse_mode="Markdown",
    )


@router.message(CJStates.notes)
async def cj_notes(message: Message, state: FSMContext, role: str) -> None:
    notes = "" if message.text.strip() == "—" else message.text.strip()
    data  = await state.get_data()
    await state.clear()

    await sheets_service.log_customer_stage(
        reporter_id  = message.from_user.id,
        customer_id  = data["customer_id"],
        link_token   = data.get("link_token", "direct"),
        funnel_type  = data.get("funnel_type", ""),
        stage        = data["stage"],
        notes        = notes,
    )

    stage_label = STAGE_LABELS.get(data["stage"], data["stage"])
    await message.answer(
        "✅ *Mijoz bosqichi saqlandi!*\n\n"
        f"👤 Mijoz: `{data['customer_id']}`\n"
        f"🔗 Havola: `{data.get('link_token', 'direct')}`\n"
        f"📊 Funnel: `{data.get('funnel_type', '—')}`\n"
        f"📍 Bosqich: {stage_label}\n"
        f"📝 Izoh: {notes or '—'}\n\n"
        "Dashboard → 🔗 Tracking bo'limida ko'rish mumkin.",
        parse_mode="Markdown",
    )
