from typing import Coroutine

import aiohttp


class Session:
    def __init__(self, session: aiohttp.ClientSession = None):
        self.session = session or aiohttp.ClientSession()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def close(self) -> Coroutine:
        return self.session.close()
