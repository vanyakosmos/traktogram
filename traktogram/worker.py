import logging
import logging.config
from typing import List

from arq import Worker, cron
from arq.connections import ArqRedis

from traktogram import rendering
from traktogram.config import LOGGING_CONFIG
from traktogram.store import store
from traktogram.trakt import CalendarEpisode, TraktClient
from traktogram.updater import bot
from traktogram.utils import group_by_show
from traktogram.markup import calendar_notification_markup, calendar_multi_notification_markup


logger = logging.getLogger(__name__)


async def send_airing_episode(ctx: dict, user_id: str, ce: CalendarEpisode):
    text = rendering.render_html(
        'calendar_notification',
        show=ce.show,
        episode=ce.episode,
    )
    client: TraktClient = ctx['trakt']
    watched = await client.watched(ce.episode.ids.trakt)
    keyboard_markup = calendar_notification_markup(ce, watched=watched)
    await bot.send_message(user_id, text, reply_markup=keyboard_markup)


async def send_airing_episodes(ctx: dict, user_id: str, episodes: List[CalendarEpisode]):
    first = episodes[0]
    show = first.show
    text = rendering.render_html(
        'calendar_multi_notification',
        show=show,
        episodes=[cs.episode for cs in episodes],
    )
    client: TraktClient = ctx['trakt']
    watched = await client.watched(first.episode.ids.trakt)
    episodes_ids = [cs.episode.ids.trakt for cs in episodes]
    keyboard_markup = calendar_multi_notification_markup(first, episodes_ids, watched)
    await bot.send_message(user_id, text, reply_markup=keyboard_markup)


async def schedule_calendar_shows(ctx: dict):
    client: TraktClient = ctx['trakt']
    queue: ArqRedis = ctx['redis']
    # todo: send multiple requests in batch
    for user_id, access_token in store.users_tokens_iter():
        client.auth(access_token)
        episodes = await client.calendar_shows(extended=True)
        logger.debug(f"fetched {len(episodes)} episodes")
        groups = group_by_show(episodes)
        for group in groups:
            first = group[0]
            if len(group) == 1:
                # todo: don't schedule if job already exists
                await queue.enqueue_job('send_airing_episode', user_id, first, _defer_until=first.first_aired)
            else:
                await queue.enqueue_job('send_airing_episodes', user_id, group, _defer_until=first.first_aired)
        logger.debug(f"scheduled {len(groups)} notifications")


async def startup(ctx):
    ctx['trakt'] = TraktClient()


async def shutdown(ctx):
    await ctx['trakt'].close()


# noinspection PyTypeChecker
def main():
    logging.config.dictConfig(LOGGING_CONFIG)
    worker = Worker(
        functions=(send_airing_episode, send_airing_episodes),
        cron_jobs=[
            cron(schedule_calendar_shows, hour=0, minute=0, second=0),
        ],
        on_startup=startup,
        on_shutdown=shutdown,
        keep_result=0,
    )
    worker.run()


if __name__ == '__main__':
    main()
