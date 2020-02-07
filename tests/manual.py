import asyncio
import logging.config
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from arq import ArqRedis, Worker, create_pool
from arq.connections import RedisSettings

from traktogram.config import LOGGING_CONFIG
from traktogram.store import store
from traktogram.trakt import TraktClient
from traktogram.utils import group_by_show
from traktogram.worker import send_calendar_multi_notifications, send_calendar_notifications


@asynccontextmanager
async def ctx_manager():
    d = {'redis': await create_pool(RedisSettings())}
    yield d
    d['redis'].close()


async def schedule_calendar_notification(client: TraktClient, queue: ArqRedis, user_id, multi=False):
    episodes = await client.calendar_shows(extended=True, start_date='2020-01-30')
    groups = group_by_show(episodes)
    for group in groups:
        first = group[0]
        first_aired = datetime.utcnow() + timedelta(seconds=1)
        if len(group) == 1 and not multi:
            await queue.enqueue_job('send_calendar_notifications', user_id, first, _defer_until=first_aired)
            break
        if len(group) > 1 and multi:
            await queue.enqueue_job('send_calendar_multi_notifications', user_id, group, _defer_until=first_aired)
            break


async def schedule_calendar_notifications(ctx: dict, **kwargs):
    queue: ArqRedis = ctx['redis']
    async with TraktClient() as client:
        for user_id, access_token in store.users_tokens_iter():
            client.auth(access_token)
            await schedule_calendar_notification(client, queue, user_id, **kwargs)


async def main():
    logging.config.dictConfig(LOGGING_CONFIG)
    async with ctx_manager() as ctx:
        await schedule_calendar_notifications(ctx, multi=False)
    worker = Worker(
        (send_calendar_notifications, send_calendar_multi_notifications),
        keep_result=0,
        burst=True,
    )
    await worker.async_run()


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
