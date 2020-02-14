import logging

import aiogram

from .config import BOT_TOKEN
from .router import Dispatcher


logger = logging.getLogger(__name__)

bot = aiogram.Bot(token=BOT_TOKEN, parse_mode='html')
dp = Dispatcher(bot)
dp.errors_handlers.once = True  # forbid error to propagate
