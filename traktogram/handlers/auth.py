import asyncio
import logging

from aiogram.types import Message

from traktogram.rendering import render_html
from traktogram.dispatcher import dp


logger = logging.getLogger(__name__)


async def process_auth_flow(message: Message):
    user_id = message.from_user.id
    sess = dp.trakt.auth()
    flow = sess.device_auth_flow()
    data = await flow.__anext__()
    code = data['user_code']
    url = data['verification_url']
    msg_text = render_html('auth_message', url=url, code=code)
    reply_kwargs = dict(disable_web_page_preview=True)
    reply = await message.answer(msg_text, **reply_kwargs)
    async for ok, data in flow:
        state = await dp.storage.get_state(user=user_id)
        if state != 'auth':
            await reply.edit_text("❌ canceled", **reply_kwargs)
            return
        if ok:
            await asyncio.gather(
                dp.storage.save_creds(user_id, data),
                reply.edit_text("✅ successfully authenticated"),
            )
            break
        else:
            text = render_html('auth_message', url=url, code=code, time_left=data)
            await reply.edit_text(text, **reply_kwargs)
    else:
        await reply.edit_text("❌ failed to authenticated in time")


@dp.command_handler('auth', help="log into trakt.tv")
async def auth_handler(message: Message):
    logger.debug("auth command")
    user_id = message.from_user.id

    if await dp.storage.has_creds(user_id):
        logger.debug("user already authenticated")
        text = "You are already authenticated. Do you want to /logout?"
        await message.answer(text)
        return

    await dp.storage.set_state(user=user_id, state='auth')
    try:
        await process_auth_flow(message)
    finally:
        await dp.storage.finish(user=user_id)
