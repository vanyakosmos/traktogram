import asyncio
import logging

from aiogram.types import CallbackQuery, Message, Update

from .store import state, store
from .trakt import TraktClient
from .updater import command_handler, commands_help, dp
from .utils import episode_cd, make_notification_reply_markup


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


@dp.callback_query_handler(episode_cd.filter(action='watched'))
async def inline_kb_answer_callback_handler(query: CallbackQuery, callback_data: dict):
    episode_id = callback_data['id']
    async with TraktClient() as client:
        access_token = store.get_access_token(query.from_user.id)
        client.auth(access_token)
        watched = len(await client.get_history(episode_id)) != 0
        logger.debug(f"watched {watched}")
        if watched:
            await client.remove_from_history(episode_id)
        else:
            await client.add_to_history(episode_id)
        watched = not watched
        se = await client.get_episode(episode_id, extended=True)
        logger.debug(se)
    # update keyboard
    markup = make_notification_reply_markup(se, watched=watched)
    await asyncio.gather(
        query.message.edit_reply_markup(markup),
        query.answer("marked as watched" if watched else "unwatched")
    )


@dp.errors_handler()
async def error_handler(update: Update, exc: Exception):
    logger.error(update)
    logger.exception(exc)
