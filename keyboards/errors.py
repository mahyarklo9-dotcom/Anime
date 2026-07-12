"""Global exception handler.

Any exception raised inside an update handler ends up here instead of
crashing the polling/webhook loop. We log the full traceback for
debugging and try to give the user a friendly, non-technical message.
"""
from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import ErrorEvent

logger = logging.getLogger(__name__)
router = Router(name="errors")


@router.errors()
async def handle_error(event: ErrorEvent) -> bool:
    logger.exception(
        "Unhandled exception while processing update %s",
        event.update.update_id,
        exc_info=event.exception,
    )

    update = event.update

    # Best-effort user notice; failures here must not raise further.
    try:
        if update.message:
            await update.message.answer(
                "⚠️ Something went wrong on our end. Please try again in a moment."
            )
        elif update.callback_query:
            await update.callback_query.answer(
                "⚠️ Something went wrong. Please try again.", show_alert=True
            )
    except Exception:  # noqa: BLE001
        logger.warning("Failed to notify user about the error.")

    return True
