import asyncio
import logging

from aiogram.types import Message

from traktogram.dispatcher import dp
from traktogram.worker import get_tasks_keys


logger = logging.getLogger(__name__)


@dp.command_handler('start', help="start")
async def start_handler(message: Message):
    logger.debug("start")
    await message.answer("start")


@dp.command_handler('help', help="show this message", state='*')
async def help_handler(message: Message):
    lines = ["Available commands:"]
    for cmd, help_text in dp.commands_help.items():
        lines.append(f"/{cmd} - {help_text}")
    await message.answer("\n".join(lines))


@dp.command_handler('cancel', help="cancel everything", state='*')
async def cancel_handler(message: Message):
    await asyncio.gather(
        dp.storage.finish(user=message.from_user.id),
        message.answer("Whatever it was, it was canceled."),
    )


@dp.command_handler('logout', help="logout")
async def logout_handler(message: Message):
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
        await message.answer("You weren't logged in.")
