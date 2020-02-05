from typing import List

from aiogram.types import InlineKeyboardButton as IKB, InlineKeyboardMarkup
from aiogram.utils.callback_data import CallbackData

from traktogram.trakt.models import ShowEpisode


episode_cd = CallbackData('e', 'id', 'action')
episodes_cd = CallbackData('es', 'ids', 'action')


def single_notification_markup(se: ShowEpisode, watched=False):
    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            IKB('✅ watched' if watched else '❌ watched',
                callback_data=episode_cd.new(id=se.episode.ids.trakt, action='watched')),
        ]
    ])
    source, watch_url = se.episode.watch_url
    if source:
        btn = IKB(f'watch on {source}', url=watch_url)
        keyboard_markup.inline_keyboard[-1].append(btn)
    return keyboard_markup


def bulk_notification_markup(episodes: List[ShowEpisode], index=0):


    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            IKB('◀️ prev', callback_data=episodes_cd.new(ids='', action='prev')),
            IKB('✅ watched' if watched else '❌ watched',
                callback_data=episodes_cd.new(id=se.episode.ids.trakt, action='watched')),
            IKB('next ▶️', callback_data=episodes_cd.new(ids='', action='prev')),
        ]
    ])
    return keyboard_markup
