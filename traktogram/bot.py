import logging

import arq
from aiogram.utils import executor

from traktogram.config import REDIS_URL
from traktogram.dispatcher import Dispatcher, dp
from traktogram.logging_setup import setup_logging
from traktogram.storage import Storage
from traktogram.trakt import TraktClient
from traktogram.worker import get_redis_settings


logger = logging.getLogger(__name__)


async def on_startup(dispatcher: Dispatcher, **kwargs):
    logger.debug('starting up services')
    dispatcher.storage = Storage(REDIS_URL)
    dispatcher.queue = await arq.create_pool(get_redis_settings())
    dispatcher.trakt = TraktClient()
    from traktogram.handlers import auth_router, cmd_router, notification_router, error_router
    for router in (auth_router, cmd_router, notification_router, error_router):
        dispatcher.add_router(router)

    await dispatcher.storage.redis()  # test connection


async def on_shutdown(dispatcher: Dispatcher):
    await dispatcher.trakt.close()
    dispatcher.queue.close()
    await dispatcher.queue.wait_closed()
    # storage and bot will be closed in dispatcher
    logger.debug('services were shutdown')


def main():
    setup_logging()
    executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown, skip_updates=True)


if __name__ == '__main__':
    main()
