import asyncio
import logging.config
from asyncio import CancelledError

import arq
from aiogram import executor, Bot

from traktogram.bot import on_shutdown, on_startup, make_dispatcher
from traktogram.config import WORKER, BOT_TOKEN
from traktogram.logging_setup import setup_logging
from traktogram.worker import WorkerConfig


logger = logging.getLogger(__name__)


class Executor(executor.Executor):
    def _run_worker(self):
        worker = arq.worker.create_worker(
            WorkerConfig,
            on_startup=None,
            on_shutdown=None,
            redis_pool=self.dispatcher.context_vars['queue'][1],
            ctx={
                'bot': self.dispatcher.bot,
                'trakt': self.dispatcher.context_vars['trakt'],
                'storage': self.dispatcher.context_vars['storage'],
            },
        )
        return worker.async_run()

    def _run_polling(self, with_worker=True):
        self._prepare_polling()
        self.loop.run_until_complete(self._startup_polling())  # welcome + services setup

        self.loop.create_task(self.dispatcher.start_polling())
        if with_worker:
            self.loop.run_until_complete(self._run_worker())
        else:
            logger.warning("Bot has started without worker.")
            self.loop.run_forever()

    def run_polling(self, wait_closed=False):
        try:
            self._run_polling(wait_closed)
        except (KeyboardInterrupt, SystemExit, CancelledError):
            pass
        finally:
            self.loop.run_until_complete(self._shutdown_polling())  # shut down services


def main():
    setup_logging()
    logger.warning('>>>>> start <<<<<')
    loop = asyncio.get_event_loop()
    bot = Bot(token=BOT_TOKEN, parse_mode='html')
    dp = make_dispatcher(bot)
    ex = Executor(dp, loop=loop)
    ex.on_startup(on_startup)
    ex.on_shutdown(on_shutdown)
    ex.run_polling(WORKER)
    logger.warning('>>>>> finish <<<<<')


if __name__ == '__main__':
    main()
