import logging
import logging.config
from typing import List

from arq import Worker, cron
from arq.connections import ArqRedis

from traktogram import rendering
from traktogram.config import LOGGING_CONFIG
from traktogram.markup import calendar_multi_notification_markup, calendar_notification_markup
from traktogram.trakt import CalendarEpisode, TraktClient
from traktogram.updater import bot, storage
from traktogram.utils import group_by_show, make_calendar_notification_task_id


logger = logging.getLogger(__name__)


async def send_calendar_notifications(ctx: dict, user_id: str, ce: CalendarEpisode):
    text = rendering.render_html(
        'calendar_notification',
        show=ce.show,
        episode=ce.episode,
    )
    async with TraktClient() as client:
        creds = await storage.get_creds(user_id)
        client.auth(creds.access_token)
        watched = await client.watched(ce.episode.ids.trakt)
    keyboard_markup = await calendar_notification_markup(ce, watched=watched)
    await bot.send_message(user_id, text, reply_markup=keyboard_markup)


async def send_calendar_multi_notifications(ctx: dict, user_id: str, episodes: List[CalendarEpisode]):
    first = episodes[0]
    show = first.show
    text = rendering.render_html(
        'calendar_multi_notification',
        show=show,
        episodes=[cs.episode for cs in episodes],
    )
    async with TraktClient() as client:
        creds = await storage.get_creds(user_id)
        client.auth(creds.access_token)
        watched = await client.watched(first.episode.ids.trakt)
    episodes_ids = [cs.episode.ids.trakt for cs in episodes]
    keyboard_markup = calendar_multi_notification_markup(first, episodes_ids, watched)
    await bot.send_message(user_id, text, reply_markup=keyboard_markup)


async def schedule_calendar_notification(client: TraktClient, queue: ArqRedis, user_id):
    episodes = await client.calendar_shows(extended=True)
    logger.debug(f"fetched {len(episodes)} episodes")
    groups = group_by_show(episodes)
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


async def schedule_calendar_notifications(ctx: dict):
    queue: ArqRedis = ctx['redis']
    async with TraktClient() as client:
        async for user_id, creds in storage.creds_iter():
            client.auth(creds.access_token)
            await schedule_calendar_notification(client, queue, user_id)


async def schedule_tokens_refresh(ctx: dict):
    async with TraktClient() as client:
        async for user_id, creds in storage.creds_iter():
            client.auth(creds.access_token)
            tokens = await client.refresh_token(creds.refresh_token)
            await storage.save_creds(user_id, tokens)


def main():
    logging.config.dictConfig(LOGGING_CONFIG)
    worker = Worker(
        (send_calendar_notifications, send_calendar_multi_notifications),
        cron_jobs=[
            cron(schedule_calendar_notifications, hour=0, minute=0, second=0),
            cron(schedule_tokens_refresh, weekday=1, hour=0, minute=0, second=0),
        ],
        keep_result=0,
    )
    worker.run()


if __name__ == '__main__':
    main()
