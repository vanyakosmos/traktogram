import asyncio
import logging

import aiohttp
from yarl import URL


logger = logging.getLogger(__name__)


class Client:
    """Generic API client"""

    def __init__(self, base_url: str):
        self.base = URL(base_url)
        self.session = aiohttp.ClientSession()
        self.access_token = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_async()

    def close(self):
        loop = asyncio.get_event_loop()
        loop.create_task(self.close_async())

    async def close_async(self):
        logger.debug(f"closing {self.__class__.__name__}...")
        await self.session.close()
        logger.debug(f"closed {self.__class__.__name__}")
