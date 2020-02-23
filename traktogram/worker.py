import contextvars
import logging
from functools import wraps
from typing import List

import arq
from aiogram import Bot
from arq import cron
from arq.connections import ArqRedis, RedisSettings
from arq.constants import job_key_prefix
from pydantic import BaseModel

from traktogram.config import BOT_TOKEN, REDIS_URL
from traktogram.logging_setup import setup_logging
from traktogram.models import CalendarEpisode
from traktogram.services import (
    CalendarMultiNotification, CalendarNotification, NotificationSchedulerService,
    TraktClient
)
from traktogram.storage import Storage
from traktogram.utils import parse_redis_uri


logger = logging.getLogger(__name__)
worker_queue_var = contextvars.ContextVar('worker_queue_var')


class Context(BaseModel):
    redis: ArqRedis
    trakt: TraktClient
    storage: Storage
    bot: Bot

    class Config:
        arbitrary_types_allowed = True


def with_context(f):
    @wraps(f)
    async def dec(ctx: dict, *args, **kwargs):
        ctx = Context(**ctx)
        return await f(ctx, *args, **kwargs)

    return dec


def without_context(f):
    @wraps(f)
    async def dec(_: dict, *args, **kwargs):
        return f(*args, **kwargs)

    return dec


@with_context
async def send_calendar_notifications(ctx: Context, user_id: str, ce: CalendarEpisode):
    service = CalendarNotification()
    await service.send(ctx.bot, ctx.trakt, ctx.storage, user_id, ce)


@with_context
async def send_calendar_multi_notifications(ctx: Context, user_id: str, episodes: List[CalendarEpisode]):
    service = CalendarMultiNotification()
    await service.send(ctx.bot, ctx.trakt, ctx.storage, user_id, episodes)


@with_context
async def schedule_calendar_notifications(ctx: Context):
    service = NotificationSchedulerService(ctx.redis)
    async for user_id, creds in ctx.storage.creds_iter():
        sess = ctx.trakt.auth(creds.access_token)
        await service.schedule(sess, user_id)


@with_context
async def schedule_tokens_refresh(ctx: Context):
    async for user_id, creds in ctx.storage.creds_iter():
        sess = ctx.trakt.auth(creds.access_token)
        tokens = await sess.refresh_token(creds.refresh_token)
        await ctx.storage.save_creds(user_id, tokens)


async def on_startup(ctx: dict):
    NotificationSchedulerService.send_single_task_name = send_calendar_notifications.__name__
    NotificationSchedulerService.send_multi_task_name = send_calendar_multi_notifications.__name__
    ctx['trakt'] = TraktClient()
    ctx['storage'] = Storage(REDIS_URL)
    ctx['bot'] = Bot(BOT_TOKEN, parse_mode='html')


async def on_shutdown(ctx: dict):
    await ctx['trakt'].close()
    await ctx['storage'].close()
    await ctx['storage'].wait_closed()
    await ctx['bot'].close()


def get_redis_settings(**kwargs):
    rs = parse_redis_uri(REDIS_URL)
    if 'db' in rs:
        rs['database'] = rs['db']
        del rs['db']
    return RedisSettings(**{**rs, **kwargs})


async def get_tasks_keys(queue: ArqRedis, user_id):
    keys = await queue.keys(job_key_prefix + f'send_calendar_notifications-{user_id}-*')
    keys += await queue.keys(job_key_prefix + f'send_calendar_multi_notifications-{user_id}-*')
    return keys


class WorkerConfig:
    functions = (send_calendar_notifications, send_calendar_multi_notifications)
    cron_jobs = (
        cron(schedule_calendar_notifications, hour=0, minute=0, second=0),
        cron(schedule_tokens_refresh, weekday=1, hour=0, minute=0, second=0),
    )
    keep_result = 0
    redis_settings = get_redis_settings()
    on_startup = on_startup
    on_shutdown = on_shutdown


def main():
    setup_logging()
    worker = arq.worker.create_worker(WorkerConfig)
    worker.run()


if __name__ == '__main__':
    main()
