import asyncio
import logging.config
from asyncio import CancelledError

import arq
from aiogram import executor

from traktogram.bot import on_shutdown, on_startup
from traktogram.config import WORKER
from traktogram.dispatcher import dp
from traktogram.logging_setup import setup_logging
from traktogram.worker import WorkerConfig


logger = logging.getLogger(__name__)


class Executor(executor.Executor):
    def _run_worker(self):
        worker = arq.worker.create_worker(
            WorkerConfig,
            on_startup=None,
            on_shutdown=None,
            redis_pool=self.dispatcher.queue,
            ctx={
                'trakt': self.dispatcher.trakt,
                'storage': self.dispatcher.storage,
            },
        )
        return worker.async_run()

    def _run_polling(self, with_worker=True):
        self._prepare_polling()
        self.loop.run_until_complete(self._startup_polling())

        self.loop.create_task(dp.start_polling())
        if with_worker:
            self.loop.run_until_complete(self._run_worker())
        else:
            logger.warning("Bot have started without worker.")
            self.loop.run_forever()

    def run_polling(self, wait_closed=False):
        try:
            self._run_polling(wait_closed)
        except (KeyboardInterrupt, SystemExit, CancelledError):
            pass
        finally:
            self.loop.run_until_complete(self._shutdown_polling())


def main():
    setup_logging()
    logger.warning('>>>>> start <<<<<')
    loop = asyncio.get_event_loop()
    ex = Executor(dp, loop=loop)
    ex.on_startup(on_startup)
    ex.on_shutdown(on_shutdown)
    ex.run_polling(WORKER)
    logger.warning('>>>>> finish <<<<<')


if __name__ == '__main__':
    main()
