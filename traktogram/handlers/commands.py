import asyncio
import logging

from aiogram.types import Message

from traktogram.dispatcher import dp
from traktogram.router import Router


logger = logging.getLogger(__name__)
router = Router()


@router.command_handler('start', help="start")
async def start_handler(message: Message):
    logger.debug("start")
    await message.answer("start")


@router.command_handler('help', help="show this message", state='*')
async def help_handler(message: Message):
    lines = ["Available commands:"]
    for cmd, help_text in dp.commands_help.items():
        lines.append(f"/{cmd} - {help_text}")
    await message.answer("\n".join(lines))


@router.command_handler('cancel', help="cancel everything", state='*')
async def cancel_handler(message: Message):
    await asyncio.gather(
        dp.storage.finish(user=message.from_user.id),
        message.answer("Whatever it was, it was canceled."),
    )
