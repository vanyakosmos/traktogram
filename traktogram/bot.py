import importlib
import logging
import logging.config

from aiogram import Dispatcher
from aiogram.utils import executor

from traktogram.config import LOGGING_CONFIG
from traktogram.updater import dp


logger = logging.getLogger(__name__)


async def on_startup(dispatcher: Dispatcher, **kwargs):
    logger.debug('startup')
    importlib.import_module('traktogram.commands')  # setup handlers


async def on_shutdown(dispatcher: Dispatcher):
    logger.debug('shutdown')


def main():
    logging.config.dictConfig(LOGGING_CONFIG)
    executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown)


if __name__ == '__main__':
    main()
