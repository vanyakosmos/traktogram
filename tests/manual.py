import asyncio
import logging.config
from argparse import ArgumentParser
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pprint import pprint

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
        for user_id, access_token in store.user_access_tokens_iter():
            client.auth(access_token)
            await schedule_calendar_notification(client, queue, user_id, **kwargs)


async def test_calendar(multi: bool):
    async with ctx_manager() as ctx:
        await schedule_calendar_notifications(ctx, multi=multi)
    worker = Worker(
        (send_calendar_notifications, send_calendar_multi_notifications),
        keep_result=0,
        burst=True,
    )
    await worker.async_run()


async def test_refresh_token(user_id):
    async with TraktClient() as client:
        tokens = store.get_tokens(user_id)
        pprint(tokens)
        client.auth(tokens['access_token'])
        tokens = await client.refresh_token(tokens['refresh_token'])
        pprint(tokens)
        store.save_tokens(user_id, tokens)


async def main():
    parser = ArgumentParser()
    sub = parser.add_subparsers(dest='sub')
    p_cal = sub.add_parser('calendar', aliases=('cal',))
    p_cal.add_argument('--multi', '-m', action='store_true')
    p_ref = sub.add_parser('refresh')
    p_ref.add_argument('user_id', type=int)
    args = parser.parse_args()
    if args.sub in ('cal', 'calendar'):
        await test_calendar(args.multi)
    elif args.sub == 'refresh':
        await test_refresh_token(args.user_id)


if __name__ == '__main__':
    logging.config.dictConfig(LOGGING_CONFIG)
    asyncio.get_event_loop().run_until_complete(main())
