import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram.types import CallbackQuery

from traktogram.markup import (
    calendar_multi_notification_markup, calendar_notification_markup, decode_ids, episode_cd,
    episodes_cd
)
from traktogram.router import Router
from traktogram.storage import Storage
from traktogram.trakt import TraktSession, TraktClient


logger = logging.getLogger(__name__)
router = Router()


async def toggle_watched_status(sess: TraktSession, episode_id, watched: bool):
    logger.debug(f"watched {watched}")
    if watched:
        await sess.remove_from_history(episode_id)
    else:
        await sess.add_to_history(episode_id)
    return not watched


class CalendarMultiNotificationHelper:
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
                cd = episodes_cd.parse(btn.callback_data)
                ids = decode_ids(cd['ids'])
                episodes_ids.extend(ids)
        return episodes_ids

    def get_current_episode(self):
        watch_btn = self.buttons[1]
        ids = episodes_cd.parse(watch_btn.callback_data)['ids']
        episode_id = decode_ids(ids)[0]
        return episode_id

    def move_index(self, step):
        self.index = max(0, min(self.index + step, len(self.episodes_ids) - 1))
        self.episode_id = self.episodes_ids[self.index]

    @asynccontextmanager
    async def fetch_episode_data_context(self):
        storage = Storage.get_current()
        trakt = TraktClient.get_current()

        creds = await storage.get_creds(self.query.from_user.id)
        sess = trakt.auth(creds.access_token)
        self.watched = await sess.watched(self.episode_id)
        yield sess
        self.se = await sess.search_by_episode_id(self.episode_id)

    async def fetch_episode_data(self):
        async with self.fetch_episode_data_context():
            pass

    async def update_message(self, answer: str = None):
        markup = calendar_multi_notification_markup(self.se, self.episodes_ids, self.watched, self.index)
        await asyncio.gather(
            self.query.message.edit_reply_markup(markup),
            self.query.answer(answer)
        )


@router.callback_query_handler(episode_cd.filter(action='watch'))
async def calendar_notification_watch_handler(query: CallbackQuery, callback_data: dict):
    storage = Storage.get_current()
    trakt = TraktClient.get_current()
    episode_id = callback_data['id']

    creds = await storage.get_creds(query.from_user.id)
    sess = trakt.auth(creds.access_token)
    watched = await sess.watched(episode_id)
    watched = await toggle_watched_status(sess, episode_id, watched)
    se = await sess.search_by_episode_id(episode_id, extended=True)
    logger.debug(se)
    # update keyboard
    markup = await calendar_notification_markup(se, watched=watched)
    await asyncio.gather(
        query.message.edit_reply_markup(markup),
        query.answer("marked as watched" if watched else "unwatched")
    )


@router.callback_query_handler(episodes_cd.filter(action='prev'))
async def calendar_multi_notification_prev_handler(query: CallbackQuery, callback_data: dict):
    h = CalendarMultiNotificationHelper(query)
    if h.index == 0:
        await query.answer("this is first episode in the queue")
        return
    h.move_index(-1)
    await h.fetch_episode_data()
    await h.update_message()


@router.callback_query_handler(episodes_cd.filter(action='next'))
async def calendar_multi_notification_next_handler(query: CallbackQuery, callback_data: dict):
    h = CalendarMultiNotificationHelper(query)
    if h.index == len(h.episodes_ids) - 1:
        await query.answer("this is last episode in the queue")
        return
    h.move_index(1)
    await h.fetch_episode_data()
    await h.update_message()


@router.callback_query_handler(episodes_cd.filter(action='watch'))
async def calendar_multi_notification_watch_handler(query: CallbackQuery, callback_data: dict):
    h = CalendarMultiNotificationHelper(query)
    async with h.fetch_episode_data_context() as sess:
        watched_current = await toggle_watched_status(sess, h.episode_id, h.watched)
        # patch helper's watch and se so that the right episode will be displayed
        if watched_current:
            h.move_index(1)
            h.watched = await sess.watched(h.episode_id)
        else:
            h.watched = False
    answer = f"marked as watched" if watched_current else "unwatched"
    await h.update_message(answer)


@router.callback_query_handler(episode_cd.filter(action='refresh'))
async def refresh_callback(query: CallbackQuery, callback_data: dict):
    answer = asyncio.create_task(query.answer("refreshing"))

    storage = Storage.get_current()
    trakt = TraktClient.get_current()
    episode_id = callback_data['id']

    creds = await storage.get_creds(query.from_user.id)
    sess = trakt.auth(creds.access_token)
    se = await sess.search_by_episode_id(episode_id, extended=True)
    watched = await sess.watched(se.episode.ids.trakt)
    keyboard_markup = await calendar_notification_markup(se, watched=watched)
    await asyncio.gather(
        query.message.edit_reply_markup(keyboard_markup),
        answer,
    )
