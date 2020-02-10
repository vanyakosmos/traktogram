import importlib
import logging
import logging.config

from aiogram.utils import executor

from traktogram.config import LOGGING_CONFIG
from traktogram.dispatcher import Dispatcher, dp
from traktogram.storage import Storage
from traktogram.trakt import TraktClient


logger = logging.getLogger(__name__)


async def on_startup(dispatcher: Dispatcher, **kwargs):
    logger.debug('startup')
    dispatcher.storage = Storage()
    dispatcher.trakt = TraktClient()
    importlib.import_module('traktogram.handlers')  # setup handlers

    await dispatcher.storage.redis()  # test connection


async def on_shutdown(dispatcher: Dispatcher):
    logger.debug('shutdown')
    await dispatcher.trakt.close()


def main():
    logging.config.dictConfig(LOGGING_CONFIG)
    executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown, skip_updates=True)


if __name__ == '__main__':
    main()
