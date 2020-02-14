import logging

from aiogram.types import Update
from aiogram.utils.exceptions import MessageNotModified

from traktogram.router import Router


logger = logging.getLogger(__name__)
router = Router()


@router.errors_handler(exception=MessageNotModified)
async def not_modified_error_handler(update: Update, exc: MessageNotModified):
    logger.debug("message was not modified")
    return True


@router.errors_handler()
async def error_handler(update: Update, exc: Exception):
    logger.error(update)
    logger.exception(exc)
    return True
