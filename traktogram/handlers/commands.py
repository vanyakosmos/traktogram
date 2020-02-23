import asyncio
import logging
import random

from aiogram.types import Message

from traktogram.rendering import render_html
from traktogram.router import Dispatcher, Router
from traktogram.services import NotificationSchedulerService, TraktException, trakt_session
from traktogram.storage import Storage
from traktogram.worker import worker_queue_var


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


@router.command_handler(
    'calendar',
    command_args=(
        (('date',), dict(nargs='?')),
        (('--days', '-d'), dict(type=int, default=1)),
        (('--schedule', '-s'), dict(action='store_true')),
    ),
    help="Show calendar events. Ex.: /calendar 2020-12-29 5"
)
async def calendar_show_handler(message: Message, command_args, **kwargs):
    if not 1 <= command_args.days <= 7:
        await message.answer("invalid day offset, should in range [1, 7]")
        return

    user_id = message.from_user.id

    sess = await trakt_session(user_id)
    try:
        episodes = await sess.calendar_shows(command_args.date, command_args.days, extended=True)
    except TraktException:
        await message.answer(f"invalid date {command_args.date!r}")
        return
    text = render_html('shows_list', episodes=episodes)
    queue = worker_queue_var.get()
    tasks = [message.answer(text)]
    if command_args.schedule:
        service = NotificationSchedulerService(queue)
        tasks.append(service.schedule(sess, user_id, episodes))
    await asyncio.gather(*tasks)
