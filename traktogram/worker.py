import logging
import logging.config
import textwrap
from collections import defaultdict
from typing import List

from aiogram.types import InlineKeyboardButton as IKB, InlineKeyboardMarkup
from arq import Worker, cron
from arq.connections import ArqRedis
from yarl import URL

from traktogram.config import LOGGING_CONFIG
from traktogram.store import store
from traktogram.trakt import CalendarShow, TraktClient
from traktogram.updater import bot


logger = logging.getLogger(__name__)


def dedent(text: str):
    return textwrap.dedent(text).strip('\n')


def group_by_show(episodes: List[CalendarShow]) -> List[List[CalendarShow]]:
    groups = defaultdict(list)
    for e in episodes:
        key = (e.show.ids.trakt, e.first_aired)
        groups[key].append(e)
    return list(groups.values())


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

    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            IKB('show', url=str(show_url)),
            IKB('season', url=str(season_url)),
            IKB('episode', url=str(episode_url)),
        ],
        [
            IKB('❌ watched', callback_data='notification:watched'),
        ]
    ])
    source, watch_url = cs.watch_url
    if source:
        btn = IKB(f'watch on {source}', url=watch_url)
        keyboard_markup.inline_keyboard[-1].append(btn)
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
    for user_id in store.data:
        access_token = store.data[user_id]['tokens']['access_token']
        client.auth(access_token)
        episodes = await client.calendar_shows(extended=True)
        groups = group_by_show(episodes)
        for group in groups:
            first = group[0]
            if len(group) == 1:
                # todo: don't schedule if job already exists
                await queue.enqueue_job('send_airing_episode', user_id, first, _defer_until=first.first_aired)
            else:
                await queue.enqueue_job('send_airing_episodes', user_id, group, _defer_until=first.first_aired)


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
