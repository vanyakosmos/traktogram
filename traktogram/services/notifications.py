import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Callable, List, Union

from aiogram import Bot
from aiogram.types import CallbackQuery, InlineKeyboardButton as IKB, InlineKeyboardMarkup
from aiogram.utils.callback_data import CallbackData
from arq import ArqRedis
from arq.constants import job_key_prefix

from traktogram import rendering
from traktogram.models import CalendarEpisode, ShowEpisode
from traktogram.storage import Storage
from traktogram.utils import compress_int, decompress_int
from .ops import trakt_session, watch_urls
from .trakt import TraktClient


logger = logging.getLogger(__name__)


class NotificationSchedulerService:
    send_single_task_name = 'send_calendar_notifications'
    send_multi_task_name = 'send_calendar_multi_notifications'

    def __init__(self, queue: ArqRedis):
        self.queue = queue

    @classmethod
    def make_job_id(cls, func: Union[str, Callable], user_id, show_id, dt: datetime, *episodes_ids):
        """
        Create unique job ID.
        Naturally show+time is enough for uniquely identify job user-wise. But because multi
        notification can be split into multiple messages we also need to accept extra data
        with episodes ids.
        """
        if not isinstance(func, str):
            func = func.__name__
        dt = dt.isoformat()
        id = f"{func}-{user_id}-{show_id}-{dt}"
        if episodes_ids:
            episodes_ids = '|'.join(map(str, episodes_ids))
            id = f'{id}-{episodes_ids}'
        return id

    async def clear_existing_job(self, job_id: str):
        """Remove existing job. Can be useful for tasks recreation and update of payload."""
        keys = await self.queue.keys(job_key_prefix + job_id)
        if keys:
            self.queue.delete(*keys)

    async def schedule(self, sess: TraktClient, user_id, episodes=None, start_date=None, days=7):
        if episodes is None:
            episodes = await sess.calendar_shows(start_date, days, extended=True)
        logger.debug(f"fetched {len(episodes)} episodes")
        groups = CalendarEpisode.group_by_show(episodes)
        for group in groups:
            if len(group) == 1:
                await self.schedule_single(self.send_single_task_name, user_id, group[0])
            else:
                await self.schedule_multi(self.send_multi_task_name, user_id, group)
        logger.debug(f"scheduled {len(groups)} notifications")

    async def schedule_single(self, task_name, user_id, ce: CalendarEpisode):
        job_id = self.make_job_id(task_name, user_id, ce.show.ids.trakt, ce.first_aired)
        await self.clear_existing_job(job_id)
        await self.queue.enqueue_job(task_name, user_id, ce, _job_id=job_id, _defer_until=ce.first_aired)

    async def schedule_multi(self, task_name, user_id, group: List[CalendarEpisode]):
        first = group[0]
        job_id = self.make_job_id(
            task_name,
            user_id,
            first.show.ids.trakt,
            first.first_aired,
            *(e.episode.ids.trakt for e in group)
        )
        await self.clear_existing_job(job_id)
        await self.queue.enqueue_job(task_name, user_id, group, _job_id=job_id, _defer_until=first.first_aired)


class CalendarNotification:
    cd = CallbackData('e', 'id', 'watched')

    @classmethod
    async def markup(cls, se: ShowEpisode, watched: bool, hide: bool):
        mark = '✅' if watched else '❌'
        cd = cls.cd.new(id=se.episode.ids.trakt, watched='1' if watched else '0')
        watch_btn = IKB(f'{mark} watched', callback_data=cd)

        kb = InlineKeyboardMarkup(inline_keyboard=[[watch_btn]])
        if not hide or not watched:
            kb.add(*[
                IKB(source, url=str(url))
                async for source, url in watch_urls(se.show)
            ])
        return kb

    async def send(self, bot: Bot, trakt: TraktClient, storage: Storage, user_id, ce: CalendarEpisode):
        text = rendering.render_html(
            'calendar_notification',
            show_episode=ce,
        )
        creds, user_data = await asyncio.gather(
            storage.get_creds(user_id),
            storage.get_data(user=user_id),
        )
        on_watch = user_data.get('on_watch', 'hide')
        sess = trakt.auth(creds.access_token)
        watched = await sess.watched(ce.episode.id)
        if watched and on_watch == 'delete':
            return
        keyboard_markup = await self.markup(ce, watched=watched, hide=on_watch == 'hide')
        await bot.send_message(user_id, text, reply_markup=keyboard_markup, disable_web_page_preview=watched)


class CalendarMultiNotification:
    cd = CallbackData('es', 'ids', 'action')

    @staticmethod
    def encode_ids(episodes: List[int]):
        ids = [compress_int(id) for id in episodes]
        return ','.join(ids) or '-'

    @staticmethod
    def decode_ids(ids: str):
        if ids == '-':
            return []
        ids = ids.split(',')
        ids = [decompress_int(id) for id in ids]
        return ids

    @classmethod
    def markup(cls, se: ShowEpisode, episodes_ids: List[int], watched: bool, index=0):
        prev_ids = cls.encode_ids(episodes_ids[:index])
        cur_id = cls.encode_ids(episodes_ids[index:index + 1])
        next_ids = cls.encode_ids(episodes_ids[index + 1:])
        mark = '✅' if watched else '❌'
        row = [
            IKB('👈️' if index > 0 else '🤛',
                callback_data=cls.cd.new(ids=prev_ids, action='prev')),
            IKB(f'{mark} {se.episode.season}x{se.episode.number}',
                callback_data=cls.cd.new(ids=cur_id, action='watch')),
            IKB('👉' if index < len(episodes_ids) - 1 else '🤜',
                callback_data=cls.cd.new(ids=next_ids, action='next')),
        ]
        return InlineKeyboardMarkup(inline_keyboard=[row])

    async def send(self, bot: Bot, trakt: TraktClient, storage: Storage, user_id: str, episodes: List[CalendarEpisode]):
        first = episodes[0]
        text = rendering.render_html(
            'calendar_multi_notification',
            show=first.show,
            episodes=episodes,
        )
        creds = await storage.get_creds(user_id)
        sess = trakt.auth(creds.access_token)
        watched = await sess.watched(first.episode.id)
        episodes_ids = [cs.episode.id for cs in episodes]
        keyboard_markup = self.markup(first, episodes_ids, watched)
        await bot.send_message(user_id, text, reply_markup=keyboard_markup)


class CalendarMultiNotificationFlow:
    def __init__(self, query: CallbackQuery):
        self.query = query
        self.buttons = query.message.reply_markup.inline_keyboard[0]
        self.episodes_ids = self.get_episode_ids()
        self.episode_id = self.get_current_episode()
        self.index = self.episodes_ids.index(self.episode_id)
        self.watched = False
        self.se = None

    def get_episode_ids(self):
        episodes_ids = []
        for btn in self.buttons:
            if btn.callback_data:
                cd = CalendarMultiNotification.cd.parse(btn.callback_data)
                ids = CalendarMultiNotification.decode_ids(cd['ids'])
                episodes_ids.extend(ids)
        return episodes_ids

    def get_current_episode(self):
        watch_btn = self.buttons[1]
        ids = CalendarMultiNotification.cd.parse(watch_btn.callback_data)['ids']
        episode_id = CalendarMultiNotification.decode_ids(ids)[0]
        return episode_id

    def move_index(self, step):
        self.index = max(0, min(self.index + step, len(self.episodes_ids) - 1))
        self.episode_id = self.episodes_ids[self.index]

    @asynccontextmanager
    async def fetch_episode_data_context(self):
        sess = await trakt_session(self.query.from_user.id)
        self.watched = await sess.watched(self.episode_id)
        yield sess
        self.se = await sess.search_by_episode_id(self.episode_id)

    async def fetch_episode_data(self):
        async with self.fetch_episode_data_context():
            pass

    async def update_message(self, answer: str = None):
        markup = CalendarMultiNotification.markup(self.se, self.episodes_ids, self.watched, self.index)
        await asyncio.gather(
            self.query.message.edit_reply_markup(markup),
            self.query.answer(answer)
        )
