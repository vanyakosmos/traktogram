import textwrap
from collections import defaultdict
from typing import List

from aiogram.types import InlineKeyboardButton as IKB, InlineKeyboardMarkup
from aiogram.utils.callback_data import CallbackData
from yarl import URL

from traktogram.trakt import CalendarShow
from traktogram.trakt.models import ShowEpisode


episode_cd = CallbackData('episode', 'id', 'action')


def dedent(text: str):
    return textwrap.dedent(text).strip('\n')


def group_by_show(episodes: List[CalendarShow]) -> List[List[CalendarShow]]:
    groups = defaultdict(list)
    for e in episodes:
        key = (e.show.ids.trakt, e.first_aired)
        groups[key].append(e)
    return list(groups.values())


def make_notification_reply_markup(se: ShowEpisode, watched=True):
    show, episode = se.show, se.episode
    season = episode.season
    ep_num = episode.number
    # urls
    base_url = URL('https://trakt.tv/shows')
    show_url = base_url / show.ids.slug
    season_url = show_url / 'seasons' / str(season)
    episode_url = season_url / 'episodes' / str(ep_num)

    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            IKB('show', url=str(show_url)),
            IKB('season', url=str(season_url)),
            IKB('episode', url=str(episode_url)),
        ],
        [
            IKB('✅ watched' if watched else '❌ watched',
                callback_data=episode_cd.new(id=episode.ids.trakt, action='watched')),
        ]
    ])
    source, watch_url = se.watch_url
    if source:
        btn = IKB(f'watch on {source}', url=watch_url)
        keyboard_markup.inline_keyboard[-1].append(btn)
    return keyboard_markup
