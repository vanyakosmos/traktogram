import asyncio
import logging

from aiogram.types import Message

from traktogram.dispatcher import dp
from traktogram.rendering import render_html
from traktogram.router import Router
from traktogram.worker import schedule_calendar_notification, get_tasks_keys


logger = logging.getLogger(__name__)
router = Router()


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
            return data['access_token']
        else:
            text = render_html('auth_message', url=url, code=code, time_left=data)
            await reply.edit_text(text, **reply_kwargs)
    else:
        await reply.edit_text("❌ failed to authenticated in time")


@router.command_handler('auth', help="log into trakt.tv")
async def auth_handler(message: Message):
    logger.debug("sign in")
    user_id = message.from_user.id

    if await dp.storage.has_creds(user_id):
        logger.debug("user already authenticated")
        text = "You are already authenticated. Do you want to /logout?"
        await message.answer(text)
        return

    await dp.storage.set_state(user=user_id, state='auth')
    try:
        access_token = await process_auth_flow(message)
        if access_token:
            sess = dp.trakt.auth(access_token)
            await schedule_calendar_notification(sess, dp.queue, user_id)
    finally:
        await dp.storage.finish(user=user_id)


@router.command_handler('logout', help="logout")
async def logout_handler(message: Message):
    logger.debug("sign out")
    user_id = message.from_user.id
    creds = await dp.storage.get_creds(user_id)
    if creds:
        keys = await get_tasks_keys(dp.queue, user_id)
        sess = dp.trakt.auth(creds.access_token)
        await asyncio.gather(
            sess.revoke_token(),
            dp.storage.remove_creds(message.from_user.id),
            message.answer("Successfully logged out."),
            dp.queue.delete(*keys),
        )
    else:
        await message.answer("You are not logged in. Use /auth to authenticate.")
