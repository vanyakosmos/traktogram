import asyncio
import logging
import random

from aiogram.types import Message

from traktogram.router import Router, Dispatcher
from traktogram.storage import Storage


logger = logging.getLogger(__name__)
router = Router()


@router.command_handler('start', help="start")
async def start_handler(message: Message):
    await message.answer(random.choice(["hey", "hi", "hello", "henlo", "UwU", "ohayo", "heeeeeeelllooo"]))


@router.command_handler('help', help="show this message", state='*')
async def help_handler(message: Message):
    dp = Dispatcher.get_current()
    lines = ["Available commands:"]
    for cmd, help_text in dp.commands_help.items():
        lines.append(f"/{cmd} - {help_text}")
    await message.answer("\n".join(lines))


@router.command_handler('cancel', help="cancel everything", state='*')
async def cancel_handler(message: Message):
    storage = Storage.get_current()
    await asyncio.gather(
        storage.finish(user=message.from_user.id),
        message.answer("Whatever it was, it was canceled."),
    )
