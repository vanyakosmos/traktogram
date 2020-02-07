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
from traktogram.utils import group_by_show, make_calendar_notification_task_id
from traktogram.worker import send_calendar_multi_notifications, send_calendar_notifications


@asynccontextmanager
async def ctx_manager():
    d = {'redis': await create_pool(RedisSettings())}
    yield d
    d['redis'].close()


async def schedule_single(*, queue, user_id, first, first_aired, **kwargs):
    return await queue.enqueue_job('send_calendar_notifications', user_id, first,
                                   _job_id=make_calendar_notification_task_id(
                                       send_calendar_notifications,
                                       user_id,
                                       first.show.ids.trakt,
                                       first_aired,
                                   ),
                                   _defer_until=first_aired)


async def schedule_multi(*, queue, user_id, first, group, **kwargs):
    return await queue.enqueue_job('send_calendar_multi_notifications', user_id, group,
                                   _job_id=make_calendar_notification_task_id(
                                       send_calendar_notifications,
                                       user_id,
                                       first.show.ids.trakt,
                                       first.first_aired,
                                       *(e.episode.ids.trakt for e in group)
                                   ),
                                   _defer_until=first.first_aired)


async def schedule_calendar_notification(client: TraktClient, queue: ArqRedis, user_id, multi=False, delay=1):
    episodes = await client.calendar_shows(extended=True, start_date='2020-01-30', days=2)
    first_aired = datetime.utcnow() + timedelta(seconds=delay)
    for e in episodes:
        e.first_aired = first_aired
    groups = group_by_show(episodes, max_num=3)
    print(len(groups))
    print(list(map(len, groups)))
    for group in groups:
        first = group[0]
        if len(group) == 1 and not multi:
            for i in range(3):
                print(await schedule_single(**locals()))
            break
        if len(group) > 1 and multi:
            for i in range(3):
                print(await schedule_multi(**locals()))


async def schedule_calendar_notifications(ctx: dict, **kwargs):
    queue: ArqRedis = ctx['redis']
    async with TraktClient() as client:
        for user_id, access_token in store.user_access_tokens_iter():
            client.auth(access_token)
            await schedule_calendar_notification(client, queue, user_id, **kwargs)


async def test_calendar(**kwargs):
    async with ctx_manager() as ctx:
        await schedule_calendar_notifications(ctx, **kwargs)
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


async def test_task(ctx: dict):
    print('test')


async def test_same_time_schedule():
    async with ctx_manager() as ctx:
        queue: ArqRedis = ctx['redis']
        dt = datetime.utcnow() + timedelta(seconds=2)
        await queue.enqueue_job('test_task', _job_id='test_task1', _defer_until=dt)
        await queue.enqueue_job('test_task', _job_id='test_task1', _defer_until=dt)
        assert len(await queue.queued_jobs()) == 1

    worker = Worker(
        (test_task,),
        keep_result=0,
        burst=True,
    )
    await worker.async_run()


async def main():
    parser = ArgumentParser()
    sub = parser.add_subparsers(dest='sub')
    p_cal = sub.add_parser('calendar', aliases=('cal',))
    p_cal.add_argument('--multi', '-m', action='store_true')
    p_cal.add_argument('--delay', '-d', type=int, default=1)
    p_ref = sub.add_parser('refresh')
    p_ref.add_argument('user_id', type=int)
    p_same = sub.add_parser('same')
    args = parser.parse_args()
    if args.sub in ('cal', 'calendar'):
        await test_calendar(multi=args.multi, delay=args.delay)
    elif args.sub == 'refresh':
        await test_refresh_token(args.user_id)
    elif args.sub == 'same':
        await test_same_time_schedule()


if __name__ == '__main__':
    logging.config.dictConfig(LOGGING_CONFIG)
    asyncio.get_event_loop().run_until_complete(main())
