"""
Anime Family Feud — Telegram bot entry point.

Run directly for local development (long polling):

    python bot.py

In production (Railway), the same entry point is invoked by the
Procfile / railway.json worker process.
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import config, setup_logging
from database import dispose_engines, init_app_db
from handlers import admin, daily, errors, help, leaderboard, misc, play, profile, settings, start
from middlewares.user_middleware import UserContextMiddleware
from services.achievement_service import achievement_service
from services.alias_service import alias_service

logger = logging.getLogger(__name__)


def build_dispatcher() -> Dispatcher:
    """Assemble the dispatcher with all routers and middleware registered."""
    dispatcher = Dispatcher(storage=MemoryStorage())

    dispatcher.message.middleware(UserContextMiddleware())
    dispatcher.callback_query.middleware(UserContextMiddleware())

    # Order matters: the errors router must be included so its @router.errors()
    # handler is registered; admin-only routes are filtered internally.
    dispatcher.include_router(errors.router)
    dispatcher.include_router(start.router)
    dispatcher.include_router(help.router)
    dispatcher.include_router(profile.router)
    dispatcher.include_router(leaderboard.router)
    dispatcher.include_router(settings.router)
    dispatcher.include_router(daily.router)
    dispatcher.include_router(misc.router)
    dispatcher.include_router(admin.router)
    # play.router is included last: it contains the catch-all plain-text
    # guess handler, which should never shadow more specific commands.
    dispatcher.include_router(play.router)

    return dispatcher


async def on_startup() -> None:
    logger.info("Starting Anime Family Feud bot (env=%s)...", config.environment)
    await init_app_db()
    await achievement_service.ensure_seeded()
    await alias_service.ensure_seeded()
    logger.info("Startup complete.")


async def on_shutdown() -> None:
    logger.info("Shutting down...")
    await dispose_engines()


async def main() -> None:
    setup_logging(config.log_level)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = build_dispatcher()
    dispatcher.startup.register(on_startup)
    dispatcher.shutdown.register(on_shutdown)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user, exiting.")
