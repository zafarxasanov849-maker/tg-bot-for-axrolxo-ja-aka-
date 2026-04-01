"""
KPI & LTV Tracking Bot — entry point.

Run:
    python main.py
"""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from middlewares import AuthMiddleware
from handlers import (
    common_router,
    vsl_router,
    lead_magnet_router,
    seminar_router,
    sales_router,
)
from services.google_api import GoogleSheetsService
from services.scheduler import start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Middleware (auth + role injection)
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    # Routers — order matters: common first, then funnel-specific
    dp.include_router(common_router)
    dp.include_router(vsl_router)
    dp.include_router(lead_magnet_router)
    dp.include_router(seminar_router)
    dp.include_router(sales_router)

    # Ensure Google Sheets tabs exist
    sheets = GoogleSheetsService()
    await sheets.ensure_tabs()

    # Start reminder scheduler
    start_scheduler(bot, sheets)

    logger.info("Bot starting…")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
