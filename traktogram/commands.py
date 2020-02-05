import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram.types import CallbackQuery, Message, Update

from traktogram.rendering import render_html
from .markup import (
    calendar_multi_notification_markup, calendar_notification_markup, decode_ids, episode_cd,
    episodes_cd
)
from .store import state, store
from .trakt import TraktClient
from .updater import command_handler, commands_help, dp


logger = logging.getLogger(__name__)


@command_handler('start', help="start")
async def start_handler(message: Message):
    await message.answer("start")


@command_handler('help', help="show this message")
async def help_handler(message: Message):
    lines = ["Available commands:"]
    for cmd, help_text in commands_help.items():
        lines.append(f"/{cmd} - {help_text}")
    await message.answer("\n".join(lines))


@command_handler('auth', help="log into trakt.tv", use_async=True)
async def auth_handler(message: Message):
    user_id = message.from_user.id

    if store.is_auth(user_id):
        text = "You are already authenticated. Do you want to /logout?"
        await message.answer(text)
        return

    state[user_id]['state'] = 'auth'
    state[user_id]['context'] = message.message_id

    client = TraktClient()
    flow = client.device_auth_flow()
    data = await flow.__anext__()
    code = data['user_code']
    url = data['verification_url']
    msg_text = render_html('auth_message', url=url, code=code)
    reply_kwargs = dict(disable_web_page_preview=True)
    reply = await message.answer(msg_text, **reply_kwargs)
    async for ok, data in flow:
        if state[user_id]['context'] != message.message_id:
            logger.debug("auth canceled because another auth flow has been initiated")
            await reply.delete()
            await client.close()
            return
        if ok:
            store.save_creds(user_id, data)
            await reply.edit_text("✅ successfully authenticated")
            break
        else:
            time_left = f"⏱ {int(data)} seconds left"
            text = render_html('auth_message', url=url, code=code, extra=time_left)
            await reply.edit_text(text, **reply_kwargs)
    else:
        await reply.edit_text("❌ failed to authenticated in time")
    await client.close()


async def toggle_watched_status(client: TraktClient, episode_id, watched: bool):
    logger.debug(f"watched {watched}")
    if watched:
        await client.remove_from_history(episode_id)
    else:
        await client.add_to_history(episode_id)
    return not watched


@dp.callback_query_handler(episode_cd.filter(action='watch'))
async def episode_watched_cb_handler(query: CallbackQuery, callback_data: dict):
    episode_id = callback_data['id']
    async with TraktClient() as client:
        access_token = store.get_access_token(query.from_user.id)
        client.auth(access_token)
        watched = await client.watched(episode_id)
        watched = await toggle_watched_status(client, episode_id, watched)
        se = await client.get_episode(episode_id, extended=True)
        logger.debug(se)
    # update keyboard
    markup = calendar_notification_markup(se, watched=watched)
    await asyncio.gather(
        query.message.edit_reply_markup(markup),
        query.answer("marked as watched" if watched else "unwatched")
    )


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
        async with TraktClient() as client:
            access_token = store.get_access_token(self.query.from_user.id)
            client.auth(access_token)
            self.watched = await client.watched(self.episode_id)
            yield client
            self.se = await client.get_episode(self.episode_id)

    async def fetch_episode_data(self):
        async with self.fetch_episode_data_context():
            pass

    async def update_message(self, answer: str):
        markup = calendar_multi_notification_markup(self.se, self.episodes_ids, self.watched, self.index)
        await asyncio.gather(
            self.query.message.edit_reply_markup(markup),
            self.query.answer(answer)
        )


@dp.callback_query_handler(episodes_cd.filter(action='prev'))
async def calendar_multi_notification_prev_handler(query: CallbackQuery, callback_data: dict):
    h = CalendarMultiNotificationHelper(query)
    if h.index == 0:
        await query.answer("this is first episode")
        return
    h.move_index(-1)
    await h.fetch_episode_data()
    await h.update_message("moving to the previous episode")


@dp.callback_query_handler(episodes_cd.filter(action='next'))
async def calendar_multi_notification_next_handler(query: CallbackQuery, callback_data: dict):
    h = CalendarMultiNotificationHelper(query)
    if h.index == len(h.episodes_ids) - 1:
        await query.answer("this is last episode")
        return
    h.move_index(1)
    await h.fetch_episode_data()
    await h.update_message(answer="moving to the next episode")


@dp.callback_query_handler(episodes_cd.filter(action='watch'))
async def calendar_multi_notification_watch_handler(query: CallbackQuery, callback_data: dict):
    h = CalendarMultiNotificationHelper(query)
    async with h.fetch_episode_data_context() as client:
        watched_current = await toggle_watched_status(client, h.episode_id, h.watched)
        # patch helper's watch and se so that the right episode will be displayed
        if watched_current:
            h.move_index(1)
            h.watched = await client.watched(h.episode_id)
        else:
            h.watched = False
    answer = f"marked as watched" if watched_current else "unwatched"
    await h.update_message(answer)


@dp.errors_handler()
async def error_handler(update: Update, exc: Exception):
    logger.error(update)
    logger.exception(exc)
