"""VSL funnel data-collection handler."""
from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from states import VSLStates
from handlers._base import (
    ask_screenshot,
    build_raw_row,
    check_anomaly_and_proceed,
    handle_screenshot_upload,
    parse_positive_number,
    sheets_service,
)

router = Router()

FUNNEL = "VSL"

# ── Helpers ─────────────────────────────────────────────────────────────────

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

# ── States ───────────────────────────────────────────────────────────────────

@router.message(VSLStates.ad_spend)
async def vsl_ad_spend(message: Message, state: FSMContext, role: str) -> None:
    value = await _num(message, state, "ad_spend")
    if value is None:
        return
    await check_anomaly_and_proceed(
        message, state, FUNNEL, "ad_spend", value,
        VSLStates.page_views,
        "VSL sahifasi ko'rishlar soni (Page Views):",
        VSLStates.anomaly_explanation,
    )


@router.message(VSLStates.anomaly_explanation)
async def vsl_anomaly_explanation(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.update_data(anomaly_explanation=message.text, anomaly_flag=True)
    next_state_str = data.get("anomaly_next_state")
    next_prompt = data.get("anomaly_next_prompt", "Davom eting:")

    # Map string back to state
    state_map = {
        VSLStates.page_views.__state__: VSLStates.page_views,
        VSLStates.video_start.__state__: VSLStates.video_start,
        VSLStates.watch_50.__state__: VSLStates.watch_50,
        VSLStates.watch_100.__state__: VSLStates.watch_100,
        VSLStates.cta_clicks.__state__: VSLStates.cta_clicks,
    }
    next_state = state_map.get(next_state_str, VSLStates.page_views)
    await state.set_state(next_state)
    await message.answer(next_prompt)


@router.message(VSLStates.page_views)
async def vsl_page_views(message: Message, state: FSMContext, role: str) -> None:
    value = await _num(message, state, "page_views")
    if value is None:
        return
    await check_anomaly_and_proceed(
        message, state, FUNNEL, "page_views", value,
        VSLStates.video_start,
        "Video boshlashlar soni (Video Start):",
        VSLStates.anomaly_explanation,
    )


@router.message(VSLStates.video_start)
async def vsl_video_start(message: Message, state: FSMContext, role: str) -> None:
    value = await _num(message, state, "video_start")
    if value is None:
        return
    await check_anomaly_and_proceed(
        message, state, FUNNEL, "video_start", value,
        VSLStates.watch_50,
        "50% tomosha qilganlar soni:",
        VSLStates.anomaly_explanation,
    )


@router.message(VSLStates.watch_50)
async def vsl_watch_50(message: Message, state: FSMContext, role: str) -> None:
    value = await _num(message, state, "watch_50")
    if value is None:
        return
    await check_anomaly_and_proceed(
        message, state, FUNNEL, "watch_50", value,
        VSLStates.watch_100,
        "100% tomosha qilganlar soni:",
        VSLStates.anomaly_explanation,
    )


@router.message(VSLStates.watch_100)
async def vsl_watch_100(message: Message, state: FSMContext, role: str) -> None:
    value = await _num(message, state, "watch_100")
    if value is None:
        return
    await check_anomaly_and_proceed(
        message, state, FUNNEL, "watch_100", value,
        VSLStates.cta_clicks,
        "CTA bosishlar soni (CTA Clicks):",
        VSLStates.anomaly_explanation,
    )


@router.message(VSLStates.cta_clicks)
async def vsl_cta_clicks(message: Message, state: FSMContext, role: str) -> None:
    value = await _num(message, state, "cta_clicks")
    if value is None:
        return
    await state.set_state(VSLStates.screenshot)
    await ask_screenshot(message)


@router.message(VSLStates.screenshot)
async def vsl_screenshot(message: Message, state: FSMContext, role: str) -> None:
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
            "page_views": data.get("page_views", 0),
            "video_start": data.get("video_start", 0),
            "watch_50": data.get("watch_50", 0),
            "watch_100": data.get("watch_100", 0),
            "cta_clicks": data.get("cta_clicks", 0),
        },
        screenshot_url=url,
        anomaly_flag=bool(data.get("anomaly_flag", False)),
        anomaly_explanation=data.get("anomaly_explanation", ""),
    )

    await sheets_service.append_raw(row)
    await sheets_service.rebuild_daily_summary()
    await state.clear()

    ad_spend = float(data.get("ad_spend", 0))
    page_views = int(data.get("page_views", 0))
    cta_clicks = int(data.get("cta_clicks", 0))
    cpl = round(ad_spend / cta_clicks, 0) if cta_clicks else 0

    await message.answer(
        "✅ *VSL hisobot saqlandi!*\n\n"
        f"💸 Ad Spend: `{ad_spend:,.0f}` so'm\n"
        f"👁 Page Views: `{page_views}`\n"
        f"🖱 CTA Clicks: `{cta_clicks}`\n"
        f"📊 CPL: `{cpl:,.0f}` so'm\n\n"
        "Yangi hisobot uchun /start bosing.",
        parse_mode="Markdown",
    )
