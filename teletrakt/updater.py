import logging
from typing import Type

from telegram.ext import BaseFilter, CommandHandler, Handler, MessageHandler, Updater

from teletrakt.config import BOT_TOKEN


logger = logging.getLogger(__name__)
updater = Updater(token=BOT_TOKEN, use_context=True)
dp = updater.dispatcher
commands_help = {}


def make_wrapper(handler_cls: Type[Handler], *args, **kwargs):
    def wrapper(f):
        logger.debug(f"add handler: {handler_cls.__name__} - {f.__name__}")
        dp.add_handler(handler_cls(*args, callback=f, **kwargs))
        return f

    return wrapper


def message_handler(filters: BaseFilter, **kwargs):
    return make_wrapper(MessageHandler, filters, **kwargs)


def command_handler(command: str, help=None, **kwargs):
    if help:
        commands_help[command] = help
    return make_wrapper(CommandHandler, command, **kwargs)
