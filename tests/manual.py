import asyncio
import logging.config
import os
from argparse import ArgumentParser
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pprint import pprint

from arq import create_pool, Worker

from traktogram.worker import *


@asynccontextmanager
async def ctx_manager():
    ctx = {'redis': await create_pool(get_redis_settings())}
    await on_startup(ctx)
    try:
        yield Context(**ctx)
    finally:
        await on_shutdown(ctx)
        ctx['redis'].close()


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


async def schedule_calendar_notification(sess: TraktSession, queue: ArqRedis, user_id, multi=False, delay=1):
    episodes = await sess.calendar_shows(extended=True, start_date='2020-01-30', days=2)
    first_aired = datetime.utcnow() + timedelta(seconds=delay)
    for e in episodes:
        e.first_aired = first_aired
    groups = CalendarEpisode.group_by_show(episodes, max_num=3)
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


@with_context
async def schedule_calendar_notifications(ctx: Context, **kwargs):
    user_creds = [(u, c) async for u, c in ctx.storage.creds_iter()]
    logger.info(f"{len(user_creds)} creds were found.")
    for user_id, creds in user_creds:
        sess = ctx.trakt.auth(creds.access_token)
        await schedule_calendar_notification(sess, ctx.redis, user_id, **kwargs)


async def test_calendar(delay, **kwargs):
    async with ctx_manager() as ctx:
        await schedule_calendar_notifications(ctx, delay=delay, **kwargs)
        worker = Worker(
            (send_calendar_notifications, send_calendar_multi_notifications),
            keep_result=0,
            burst=True,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            redis_settings=get_redis_settings(),
        )
        await worker.async_run()


async def test_refresh_token(user_id):
    async with ctx_manager() as ctx:
        creds = await ctx.storage.get_creds(user_id)
        pprint(creds.to_dict())
        sess = ctx.trakt.auth(creds.access_token)
        tokens = await sess.refresh_token(creds.refresh_token)
        pprint(tokens)
        await ctx.storage.save_creds(user_id, tokens)


async def test_task(_):
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
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            redis_settings=get_redis_settings(),
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
            redis_settings=get_redis_settings(),
        )
        await worker.async_run()


async def main():
    parser = ArgumentParser()
    parser.add_argument('--all', '-a', action='store_true')
    sub = parser.add_subparsers(dest='sub')
    p_cal = sub.add_parser('calendar', aliases=('cal',))
    p_cal.add_argument('--multi', '-m', action='store_true')
    p_cal.add_argument('--delay', '-d', type=int, default=1)
    p_ref = sub.add_parser('refresh')
    p_ref.add_argument('user_id', type=int)
    sub.add_parser('same')
    sub.add_parser('remove')
    args = parser.parse_args()
    if args.sub in ('cal', 'calendar'):
        await test_calendar(multi=args.multi, delay=args.delay)
    elif args.sub == 'refresh':
        await test_refresh_token(args.user_id)
    elif args.sub == 'same':
        await test_same_time_schedule()
    elif args.sub == 'remove':
        await test_remove()
    elif args.all:
        await test_calendar(multi=True, delay=1)
        await test_calendar(multi=False, delay=1)
        await test_refresh_token(os.getenv('USER_ID'))
        await test_same_time_schedule()


if __name__ == '__main__':
    setup_logging()
    asyncio.get_event_loop().run_until_complete(main())
