from __future__ import annotations

import asyncio
import logging

from telegram.ext import Application

from app.config import load_settings
from app.handlers import register_handlers, schedule_daily_summary
from app.logging_config import setup_logging
from app.sheets_service import SheetsService

LOGGER = logging.getLogger(__name__)


def run() -> None:
    settings = load_settings()
    setup_logging(settings.log_level)

    LOGGER.info("Starting Telegram expense bot")
    sheets_service = SheetsService(settings)

    application = Application.builder().token(settings.telegram_bot_token).build()
    register_handlers(application, settings, sheets_service)
    schedule_daily_summary(application, settings)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if settings.bot_mode == "polling":
        LOGGER.info("Running in polling mode")
        application.run_polling(drop_pending_updates=True, allowed_updates=None)
        return

    LOGGER.info("Running webhook on port %s at path %s", settings.port, settings.webhook_path)
    application.run_webhook(
        listen="0.0.0.0",
        port=settings.port,
        url_path=settings.webhook_path.lstrip("/"),
        webhook_url=settings.webhook_url,
        secret_token=settings.webhook_secret_token,
        drop_pending_updates=True,
        allowed_updates=None,
    )
