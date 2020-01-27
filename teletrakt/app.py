import importlib
import logging
import logging.config

from aiogram.utils import executor

from teletrakt.config import LOGGING_CONFIG
from teletrakt.updater import dp


logger = logging.getLogger(__name__)


def main():
    logging.config.dictConfig(LOGGING_CONFIG)
    importlib.import_module('teletrakt.commands')
    logger.info("start polling")
    executor.start_polling(dp, skip_updates=True)
    logger.info("exit")


if __name__ == '__main__':
    main()
