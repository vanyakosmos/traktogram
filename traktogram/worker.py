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

from traktogram import rendering
from traktogram.config import BOT_TOKEN, REDIS_URL
from traktogram.logging_setup import setup_logging
from traktogram.markup import calendar_multi_notification_markup, calendar_notification_markup
from traktogram.models import CalendarEpisode
from traktogram.storage import Storage
from traktogram.services import TraktClient
from traktogram.utils import make_calendar_notification_task_id, parse_redis_uri


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
    text = rendering.render_html(
        'calendar_notification',
        show_episode=ce,
    )
    creds = await ctx.storage.get_creds(user_id)
    sess = ctx.trakt.auth(creds.access_token)
    watched = await sess.watched(ce.episode.id)
    keyboard_markup = await calendar_notification_markup(ce, watched=watched)
    await ctx.bot.send_message(user_id, text, reply_markup=keyboard_markup, disable_web_page_preview=watched)


@with_context
async def send_calendar_multi_notifications(ctx: Context, user_id: str, episodes: List[CalendarEpisode]):
    first = episodes[0]
    text = rendering.render_html(
        'calendar_multi_notification',
        show=first.show,
        episodes=episodes,
    )
    creds = await ctx.storage.get_creds(user_id)
    sess = ctx.trakt.auth(creds.access_token)
    watched = await sess.watched(first.episode.id)
    episodes_ids = [cs.episode.id for cs in episodes]
    keyboard_markup = calendar_multi_notification_markup(first, episodes_ids, watched)
    await ctx.bot.send_message(user_id, text, reply_markup=keyboard_markup)


async def schedule_calendar_notification(sess: TraktClient, queue: ArqRedis, user_id,
                                         episodes=None, start_date=None, days=7):
    if episodes is None:
        episodes = await sess.calendar_shows(start_date, days, extended=True)
    logger.debug(f"fetched {len(episodes)} episodes")
    groups = CalendarEpisode.group_by_show(episodes)
    for group in groups:
        first = group[0]
        if len(group) == 1:
            await queue.enqueue_job('send_calendar_notifications', user_id, first,
                                    _job_id=make_calendar_notification_task_id(
                                        send_calendar_notifications,
                                        user_id,
                                        first.show.ids.trakt,
                                        first.first_aired,
                                    ),
                                    _defer_until=first.first_aired)
        else:
            await queue.enqueue_job('send_calendar_multi_notifications', user_id, group,
                                    _job_id=make_calendar_notification_task_id(
                                        send_calendar_notifications,
                                        user_id,
                                        first.show.ids.trakt,
                                        first.first_aired,
                                        *(e.episode.ids.trakt for e in group)
                                    ),
                                    _defer_until=first.first_aired)
    logger.debug(f"scheduled {len(groups)} notifications")


@with_context
async def schedule_calendar_notifications(ctx: Context):
    async for user_id, creds in ctx.storage.creds_iter():
        sess = ctx.trakt.auth(creds.access_token)
        await schedule_calendar_notification(sess, ctx.redis, user_id)


@with_context
async def schedule_tokens_refresh(ctx: Context):
    async for user_id, creds in ctx.storage.creds_iter():
        sess = ctx.trakt.auth(creds.access_token)
        tokens = await sess.refresh_token(creds.refresh_token)
        await ctx.storage.save_creds(user_id, tokens)


async def on_startup(ctx: dict):
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
