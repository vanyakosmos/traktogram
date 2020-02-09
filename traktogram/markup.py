from typing import List

from aiogram.types import InlineKeyboardButton as IKB, InlineKeyboardMarkup
from aiogram.utils.callback_data import CallbackData

from .models import ShowEpisode
from .utils import compress_int, decompress_int


episode_cd = CallbackData('e', 'id', 'action')
episodes_cd = CallbackData('es', 'ids', 'action')


def encode_ids(episodes: List[int]):
    ids = [compress_int(id) for id in episodes]
    return ','.join(ids) or '-'


def decode_ids(ids: str):
    if ids == '-':
        return []
    ids = ids.split(',')
    ids = [decompress_int(id) for id in ids]
    return ids


async def calendar_notification_markup(se: ShowEpisode, watched: bool):
    mark = '✅' if watched else '❌'
    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            IKB(f'{mark} watched',
                callback_data=episode_cd.new(id=se.episode.ids.trakt, action='watch')),
        ]
    ])
    source, watch_url = await se.episode.watch_url
    if source:
        btn = IKB(f'watch on {source}', url=watch_url)
        keyboard_markup.inline_keyboard[-1].append(btn)
    return keyboard_markup


def calendar_multi_notification_markup(se: ShowEpisode, episodes: List[int], watched: bool, index=0):
    prev_ids = encode_ids(episodes[:index])
    cur_id = encode_ids(episodes[index:index + 1])
    next_ids = encode_ids(episodes[index + 1:])
    mark = '✅' if watched else '❌'
    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            IKB('👈️' if index > 0 else '🤛',
                callback_data=episodes_cd.new(ids=prev_ids, action='prev')),
            IKB(f'{mark} {se.episode.season}x{se.episode.number}',
                callback_data=episodes_cd.new(ids=cur_id, action='watch')),
            IKB('👉' if index < len(episodes) - 1 else '🤜',
                callback_data=episodes_cd.new(ids=next_ids, action='next')),
        ]
    ])
    return keyboard_markup
