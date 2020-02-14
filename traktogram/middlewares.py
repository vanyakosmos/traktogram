import logging
from types import FunctionType

from aiogram.dispatcher.handler import current_handler
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import Message


class LoggingMiddleware(BaseMiddleware):
    async def on_process_message(self, message: Message, data: dict):
        handler: FunctionType = current_handler.get()
        logger = logging.getLogger(handler.__module__)
        logger.debug(f"called {handler.__qualname__!r}")
