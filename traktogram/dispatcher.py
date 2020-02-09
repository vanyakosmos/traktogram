import logging
import textwrap
from typing import Optional

import aiogram

from .config import BOT_TOKEN
from .storage import Storage


logger = logging.getLogger(__name__)


def log_register(f):
    def dec(self, callback, *args, **kwargs):
        lines = []
        # if args:
        #     lines.append(', '.join(map(str, args)))
        if kwargs:
            lines.append(', '.join(map(lambda e: f"{e[0]}={e[1]!r}", kwargs.items())))
        text = '\n'.join(lines)
        # text = textwrap.indent(text, prefix='    ')
        logger.debug(f"registered {callback.__name__}: {text}")
        return f(self, callback, *args, **kwargs)

    return dec


class Dispatcher(aiogram.Dispatcher):
    def __init__(self, *args, storage: Storage = None, **kwargs):
        super(Dispatcher, self).__init__(*args, storage=storage, **kwargs)
        self.commands_help = {}
        self.trakt: Optional['TraktClient'] = None
        self.storage = storage

    def command_handler(self, command, help=None, **kwargs):
        if help:
            self.commands_help[command] = help

        def decorator(callback):
            self.register_message_handler(callback, commands=[command], **kwargs)
            return callback

        return decorator

    @log_register
    def register_message_handler(self, *args, **kwargs):
        return super(Dispatcher, self).register_message_handler(*args, **kwargs)

    @log_register
    def register_callback_query_handler(self, *args, **kwargs):
        return super(Dispatcher, self).register_callback_query_handler(*args, **kwargs)


bot = aiogram.Bot(token=BOT_TOKEN, parse_mode='html')
dp = Dispatcher(bot)
