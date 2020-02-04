import logging
import logging.config
from typing import List

from arq import Worker
from arq.connections import ArqRedis
from yarl import URL

from traktogram.config import LOGGING_CONFIG
from traktogram.store import store
from traktogram.trakt import CalendarShow, TraktClient
from traktogram.updater import bot
from traktogram.utils import dedent, group_by_show, make_notification_reply_markup


logger = logging.getLogger(__name__)


async def send_airing_episode(ctx: dict, user_id: str, cs: CalendarShow):
    # extract data
    season = cs.episode.season
    ep_num = cs.episode.number
    ep_num_abs = cs.episode.number_abs
    season_text = 'Special' if season == 0 else f'Season {season}'
    episode_text = f'{ep_num} ({ep_num_abs})' if ep_num_abs else f'{ep_num}'
    # urls
    base_url = URL('https://trakt.tv/shows')
    show_url = base_url / cs.show.ids.slug
    season_url = show_url / 'seasons' / str(season)
    episode_url = season_url / 'episodes' / str(ep_num)
    # message template
    text = dedent(f"""
        *{cs.show.title}* {season}x{ep_num} ["{cs.episode.title}"]({episode_url})
        {season_text} / Episode {episode_text}
    """)

    keyboard_markup = make_notification_reply_markup(cs)
    await bot.send_message(user_id, text, reply_markup=keyboard_markup)


async def send_airing_episodes(ctx: dict, user_id: str, episodes: List[CalendarShow]):
    # todo
    await bot.send_message(user_id, "\n".join([
        f"{e.show.title} - {e.episode.title}"
        for e in episodes
    ]))


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
