import logging

from telegram.ext import Updater, CommandHandler, MessageHandler, Handler

from teletrakt.config import BOT_TOKEN


logger = logging.getLogger(__name__)
updater = Updater(token=BOT_TOKEN, use_context=True)
dp = updater.dispatcher
commands_help = {}


def handler(type, *args, help=None, **kwargs):
    if type == 'cmd':
        handler_cls = CommandHandler
    elif type == 'msg':
        handler_cls = MessageHandler
    elif isinstance(type, Handler):
        handler_cls = type
    else:
        raise ValueError("invalid handler type")

    if help and handler_cls is CommandHandler:
        cmd = args[0] if args else kwargs['command']
        commands_help[cmd] = help

    def wrapper(f):
        logger.debug(f"added handler: {handler_cls.__name__} - {f.__name__}")
        dp.add_handler(handler_cls(*args, callback=f, **kwargs))
        return f

    return wrapper
