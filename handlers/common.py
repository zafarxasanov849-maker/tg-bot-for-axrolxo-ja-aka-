"""
/start — entry point for all users.
Shows funnel selection keyboard.
"""
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    CallbackQuery,
)

router = Router()

FUNNEL_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📹 VSL Voronkasi", callback_data="funnel:vsl")],
        [InlineKeyboardButton(text="🧲 Lead Magnet", callback_data="funnel:lead_magnet")],
        [InlineKeyboardButton(text="🎓 Seminar", callback_data="funnel:seminar")],
        [InlineKeyboardButton(text="💰 Sotuv / LTV", callback_data="funnel:sales")],
    ]
)

ROLE_ALLOWED: dict[str, list[str]] = {
    "vsl": ["FOUNDER", "MARKETING"],
    "lead_magnet": ["FOUNDER", "MARKETING"],
    "seminar": ["FOUNDER", "MARKETING", "SALES"],
    "sales": ["FOUNDER", "SALES"],
}


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, role: str) -> None:
    await state.clear()
    await message.answer(
        f"Salom! Rolingiz: *{role}*\n\n"
        "Qaysi voronka bo'yicha hisobot berasiz?",
        reply_markup=FUNNEL_KEYBOARD,
        parse_mode="Markdown",
    )


@router.callback_query(lambda c: c.data and c.data.startswith("funnel:"))
async def funnel_selected(
    callback: CallbackQuery, state: FSMContext, role: str
) -> None:
    funnel = callback.data.split(":")[1]
    allowed = ROLE_ALLOWED.get(funnel, [])

    if role not in allowed:
        await callback.answer(
            "⛔ Siz bu bo'limga ma'lumot kira olmaysiz.", show_alert=True
        )
        return

    await callback.answer()
    await state.update_data(funnel_type=funnel)

    # Delegate to the appropriate handler by setting state
    if funnel == "vsl":
        from states import VSLStates
        await state.set_state(VSLStates.ad_spend)
        await callback.message.edit_text(
            "📹 *VSL Voronkasi*\n\nReklama xarajati (Ad Spend) ni kiriting (so'm):",
            parse_mode="Markdown",
        )
    elif funnel == "lead_magnet":
        from states import LeadMagnetStates
        await state.set_state(LeadMagnetStates.ad_spend)
        await callback.message.edit_text(
            "🧲 *Lead Magnet Voronkasi*\n\nReklama xarajati (Ad Spend) ni kiriting (so'm):",
            parse_mode="Markdown",
        )
    elif funnel == "seminar":
        from states import SeminarStates
        await state.set_state(SeminarStates.ad_spend)
        await callback.message.edit_text(
            "🎓 *Seminar Voronkasi*\n\nReklama xarajati (Ad Spend) ni kiriting (so'm):",
            parse_mode="Markdown",
        )
    elif funnel == "sales":
        from states import SalesStates
        await state.set_state(SalesStates.customer_id)
        await callback.message.edit_text(
            "💰 *Sotuv & LTV*\n\nMijoz ID (telefon raqam yoki Telegram username):",
            parse_mode="Markdown",
        )
