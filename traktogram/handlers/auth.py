import asyncio
import logging

from aiogram.types import Message

from traktogram.rendering import render_html
from traktogram.router import Router
from traktogram.services.notifications import NotificationSchedulerService
from traktogram.storage import Storage
from traktogram.services import TraktClient
from traktogram.worker import get_tasks_keys, worker_queue_var


logger = logging.getLogger(__name__)
router = Router()


async def process_auth_flow(message: Message):
    storage = Storage.get_current()
    trakt = TraktClient.get_current()
    user_id = message.from_user.id

    flow = trakt.device_auth_flow()
    data = await flow.__anext__()
    code = data['user_code']
    url = data['verification_url']
    msg_text = render_html('auth_message', url=url, code=code)
    reply_kwargs = dict(disable_web_page_preview=True)
    reply = await message.answer(msg_text, **reply_kwargs)
    async for ok, data in flow:
        state = await storage.get_state(user=user_id)
        if state != 'auth':
            await reply.edit_text("❌ canceled", **reply_kwargs)
            return
        if ok:
            await asyncio.gather(
                storage.save_creds(user_id, data),
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
    storage = Storage.get_current()
    trakt = TraktClient.get_current()
    queue = worker_queue_var.get()
    user_id = message.from_user.id

    if await storage.has_creds(user_id):
        logger.debug("user already authenticated")
        text = "You are already authenticated. Do you want to /logout?"
        await message.answer(text)
        return

    await storage.set_state(user=user_id, state='auth')
    try:
        if access_token := await process_auth_flow(message):
            sess = trakt.auth(access_token)
            service = NotificationSchedulerService(queue)
            await service.schedule(sess, user_id)
    finally:
        await storage.finish(user=user_id)


@router.command_handler('logout', help="logout")
async def logout_handler(message: Message):
    storage = Storage.get_current()
    trakt = TraktClient.get_current()
    queue = worker_queue_var.get()
    user_id = message.from_user.id
    action = asyncio.create_task(message.bot.send_chat_action(message.chat.id, 'typing'))

    creds = await storage.get_creds(user_id)
    if creds:
        sess = trakt.auth(creds.access_token)
        tasks = [
            action,
            sess.revoke_token(),
            storage.remove_creds(message.from_user.id),
            message.answer("Successfully logged out."),
        ]
        if keys := await get_tasks_keys(queue, user_id):
            tasks.append(queue.delete(*keys))
        await asyncio.gather(*tasks)
    else:
        await asyncio.gather(
            action,
            message.answer("You are not logged in. Use /auth to authenticate.")
        )
