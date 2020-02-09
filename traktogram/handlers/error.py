import logging

from aiogram.types import Update

from traktogram.dispatcher import dp


logger = logging.getLogger(__name__)


@dp.errors_handler()
async def error_handler(update: Update, exc: Exception):
    logger.error(update)
    logger.exception(exc)
