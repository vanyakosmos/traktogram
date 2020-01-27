import importlib
import logging
import logging.config

from teletrakt.config import LOGGING_CONFIG
from teletrakt.updater import updater

logger = logging.getLogger(__name__)


def main():
    logging.config.dictConfig(LOGGING_CONFIG)
    importlib.import_module('teletrakt.commands')
    logger.info("start polling")
    updater.start_polling()
    updater.idle()
    logger.info("exit")


if __name__ == '__main__':
    main()
