import logging

from aiogram import Bot, Dispatcher

from traktogram.storage import Storage
from .config import BOT_TOKEN


logger = logging.getLogger(__name__)
commands_help = {}

bot = Bot(token=BOT_TOKEN, parse_mode='html')
storage = Storage()
dp = Dispatcher(bot, storage=storage)


def message_handler(*filters, **kwargs):
    def wrapper(f):
        logger.debug(f"add message handler: {f.__name__}")
        handler = dp.message_handler(*filters, **kwargs)
        return handler(f)

    return wrapper


def command_handler(command: str, help=None, **kwargs):
    if help:
        commands_help[command] = help

    def wrapper(f):
        logger.debug(f"add command handler: {f.__name__}")
        handler = dp.message_handler(commands=[command], **kwargs)
        return handler(f)

    return wrapper
