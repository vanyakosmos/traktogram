import asyncio
import logging
import os
from argparse import ArgumentParser
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pprint import pformat, pprint

from arq import ArqRedis, Worker, create_pool
from arq.constants import job_key_prefix

from traktogram.logging_setup import setup_logging
from traktogram.models import CalendarEpisode
from traktogram.services import NotificationScheduler, TraktClient
from traktogram.worker import Context, get_redis_settings, on_shutdown, on_startup, send_calendar_multi_notifications, \
    send_calendar_notifications, with_context


logger = logging.getLogger(__name__)
REDIS_SETTINGS = get_redis_settings(database=1)


@asynccontextmanager
async def ctx_manager():
    ctx = {'redis': await create_pool(REDIS_SETTINGS)}
    await on_startup(ctx)
    try:
        yield ctx
    finally:
        await on_shutdown(ctx)
        ctx['redis'].close()


async def schedule_calendar_notification(sess: TraktClient, queue: ArqRedis, user_id, start_date=None):
    if start_date is None:
        start_date = datetime.now().date().isoformat()
    logger.debug(pformat(locals()))
    episodes = await sess.calendar_shows(extended=True, start_date=start_date, days=1)
    first_aired = datetime.utcnow() + timedelta(seconds=1)
    for e in episodes:
        e.first_aired = first_aired
    logger.debug(pformat([e.dict() for e in episodes]))
    groups = CalendarEpisode.group_by_show(episodes, max_num=15)
    logger.debug(f"groups: {list(map(len, groups))}")
    s = NotificationScheduler(queue)
    await s.schedule_groups(user_id, groups)


@with_context
async def schedule_calendar_notifications(ctx: Context, **kwargs):
    user_creds = [(u, c) async for u, c in ctx.storage.creds_iter()]
    logger.info(f"{len(user_creds)} creds were found.")
    for user_id, creds in user_creds:
        sess = ctx.trakt.auth(creds.access_token)
        await schedule_calendar_notification(sess, ctx.redis, user_id, **kwargs)


async def test_calendar(**kwargs):
    async with ctx_manager() as ctx:
        await schedule_calendar_notifications(ctx, **kwargs)
        worker = Worker(
            (send_calendar_notifications, send_calendar_multi_notifications),
            keep_result=0,
            burst=True,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            redis_settings=REDIS_SETTINGS,
        )
        await worker.async_run()


async def test_refresh_token(user_id):
    async with ctx_manager() as ctx:
        ctx = Context(**ctx)
        creds = await ctx.storage.get_creds(user_id)
        pprint(dict(creds))
        sess = ctx.trakt.auth(creds.access_token)
        tokens = await sess.refresh_token(creds.refresh_token)
        pprint(tokens)
        await ctx.storage.save_creds(user_id, tokens)


async def test_task(_):
    logger.debug('test task')


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
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            redis_settings=REDIS_SETTINGS,
        )
        await worker.async_run()


async def test_remove():
    async with ctx_manager() as ctx:
        dt = datetime.utcnow() + timedelta(seconds=2)
        await ctx.redis.enqueue_job('test_task', _job_id='test_task1', _defer_until=dt)
        print(await ctx.redis.delete(job_key_prefix + 'test_task1'))
        worker = Worker(
            (test_task,),
            keep_result=0,
            burst=True,
            redis_settings=REDIS_SETTINGS,
        )
        await worker.async_run()


async def main():
    parser = ArgumentParser()
    parser.add_argument('--all', '-a', action='store_true')
    sub = parser.add_subparsers(dest='sub')
    p_cal = sub.add_parser('cal')
    p_cal.add_argument('--date', '-d', type=str, default=None)
    p_ref = sub.add_parser('refresh')
    p_ref.add_argument('user_id', type=int)
    sub.add_parser('same')
    sub.add_parser('remove')
    args = parser.parse_args()
    if args.sub == 'cal':
        await test_calendar(start_date=args.date)
    elif args.sub == 'refresh':
        await test_refresh_token(args.user_id)
    elif args.sub == 'same':
        await test_same_time_schedule()
    elif args.sub == 'remove':
        await test_remove()
    elif args.all:
        await test_calendar()
        await test_refresh_token(os.getenv('USER_ID'))
        await test_same_time_schedule()


if __name__ == '__main__':
    setup_logging()
    asyncio.get_event_loop().run_until_complete(main())
