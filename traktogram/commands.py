import logging

from aiogram.types import Message, Update
from aiogram.utils.markdown import escape_md

from .store import store, state
from .trakt import TraktClient
from .updater import command_handler, commands_help, dp, message_handler


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
        await message.answer(escape_md(text))
        return

    state[user_id]['state'] = 'auth'
    state[user_id]['context'] = message.message_id

    client = TraktClient()
    flow = client.device_auth_flow()
    data = await flow.__anext__()
    code = data['user_code']
    url = data['verification_url']
    msg_text = (
        f"Authorize at {escape_md(url)} using code below\n"
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


@message_handler()
async def echo(message: Message):
    logger.debug(f"echoed {message.text}")
    await message.answer(message.text)


@dp.errors_handler()
async def error_handler(update: Update, exc: Exception):
    logger.error(update)
    logger.exception(exc)
