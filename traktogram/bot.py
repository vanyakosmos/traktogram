import logging

import arq
from aiogram import Bot
from aiogram.utils import executor

from traktogram.config import REDIS_URL, BOT_TOKEN
from traktogram.filters import CmdArgs
from traktogram.logging_setup import setup_logging
from traktogram.middlewares import LoggingMiddleware
from traktogram.router import Dispatcher
from traktogram.storage import Storage
from traktogram.services import TraktClient
from traktogram.worker import get_redis_settings, worker_queue_var


logger = logging.getLogger(__name__)


async def on_startup(dispatcher: Dispatcher, **kwargs):
    logger.debug('setting up services')
    dispatcher.storage = Storage(REDIS_URL)

    queue = await arq.create_pool(get_redis_settings())
    dispatcher.context_vars.update({
        'storage': dispatcher.storage,
        'trakt': TraktClient(),
        'queue': (worker_queue_var, queue),
    })

    # setup handlers
    from traktogram.handlers import auth_router, cmd_router, notification_router, error_router
    for router in (auth_router, cmd_router, notification_router, error_router):
        dispatcher.add_router(router)

    await dispatcher.storage.redis()  # test connection


async def on_shutdown(dispatcher: Dispatcher):
    context = dict(dispatcher.gen_context())
    await context['trakt'].close()
    queue = context['queue']
    queue.close()
    await queue.wait_closed()
    # storage and bot will be closed in dispatcher
    logger.debug('services were shut down')


def make_dispatcher(bot: Bot):
    dp = Dispatcher(bot)
    dp.errors_handlers.once = True  # forbid error to propagate
    dp.middleware.setup(LoggingMiddleware())
    dp.filters_factory.bind(CmdArgs, event_handlers=[dp.message_handlers])
    return dp


def main():
    setup_logging()
    bot = Bot(token=BOT_TOKEN, parse_mode='html')
    dp = make_dispatcher(bot)
    executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown, skip_updates=True)


if __name__ == '__main__':
    main()
