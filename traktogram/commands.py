import asyncio
import logging

from aiogram.types import CallbackQuery, Message, Update

from .markup import episode_notification_markup, episode_cd, episodes_cd, decode_ids, episodes_notification_markup
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
    msg_text = (
        f"Authorize at {url} using code below\n"
        f"```\n{code}\n```"
    )
    msg_template = f"{msg_text}\n{{}}"
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
            await reply.edit_text(msg_template.format(time_left), **reply_kwargs)
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
    markup = episode_notification_markup(se, watched=watched)
    await asyncio.gather(
        query.message.edit_reply_markup(markup),
        query.answer("marked as watched" if watched else "unwatched")
    )


@dp.callback_query_handler(episodes_cd.filter())
async def multi_episode_watched_cb_handler(query: CallbackQuery, callback_data: dict):
    # extract ids
    episodes_ids = []
    prev_btn, watch_btn, next_btn = query.message.reply_markup.inline_keyboard[0]
    for btn in (prev_btn, watch_btn, next_btn):
        if btn.callback_data:
            cd = episodes_cd.parse(btn.callback_data)
            ids = decode_ids(cd['ids'])
            episodes_ids.extend(ids)
    # extract input data
    action = callback_data['action']
    episode_id = decode_ids(episodes_cd.parse(watch_btn.callback_data)['ids'])[0]
    index = episodes_ids.index(episode_id)
    # validate input
    if index == 0 and action == 'prev':
        await query.answer("already at first episode")
        return
    if index == len(episodes_ids) - 1 and action == 'next':
        await query.answer("already at last episode")
        return
    # change index and episode id according to action
    if action == 'prev':
        index -= 1
    elif action == 'next':
        index += 1
    episode_id = episodes_ids[index]
    # fetch info about current episode
    async with TraktClient() as client:
        access_token = store.get_access_token(query.from_user.id)
        client.auth(access_token)
        watched = await client.watched(episode_id)
        watched_current = False
        if action == 'watch':
            watched_current = await toggle_watched_status(client, episode_id, watched)
            if watched_current:
                index = min(index + 1, len(episodes_ids) - 1)
                episode_id = episodes_ids[index]
                watched = await client.watched(episode_id)
            else:
                watched = False
        se = await client.get_episode(episode_id)
    # handle actions
    if action == 'prev':
        answer = "moving to the previous episode"
    elif action == 'next':
        answer = "moving to the next episode"
    else:
        answer = f"marked as watched" if watched_current else "unwatched"
    markup = episodes_notification_markup(se, episodes_ids, watched, index)
    await asyncio.gather(
        query.message.edit_reply_markup(markup),
        query.answer(answer)
    )
    await query.answer(action)


@dp.errors_handler()
async def error_handler(update: Update, exc: Exception):
    logger.error(update)
    logger.exception(exc)
