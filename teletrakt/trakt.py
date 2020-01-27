import asyncio
import logging
from time import time

import aiohttp
from yarl import URL

from teletrakt.config import TRAKT_CLIENT_ID, TRAKT_CLIENT_SECRET


logger = logging.getLogger(__name__)


class TraktClient:
    def __init__(self):
        self.base = URL('https://api.trakt.tv')
        self.session = aiohttp.ClientSession()

    @property
    def headers(self):
        return {
            'Content-type': 'application/json',
            'trakt-api-key': TRAKT_CLIENT_ID,
            'trakt-api-version': '2',
        }

    async def device_code(self) -> dict:
        """
        Response example::

            {
              "device_code": "d9c126a7706328d808914cfd1e40274b6e009f684b1aca271b9b3f90b3630d64",
              "user_code": "5055CC52",
              "verification_url": "https://trakt.tv/activate",
              "expires_in": 600,
              "interval": 5
            }
        """
        url = self.base / 'oauth/device/code'
        r = await self.session.post(url, json={'client_id': TRAKT_CLIENT_ID})
        return await r.json()

    async def get_token(self, device_code: str):
        """
        Response example::

            {
              "access_token": "dbaf9757982a9e738f05d249b7b5b4a266b3a139049317c4909f2f263572c781",
              "token_type": "bearer",
              "expires_in": 7200,
              "refresh_token": "76ba4c5c75c96f6087f58a4de10be6c00b29ea1ddc3b2022ee2016d1363e3a7c",
              "scope": "public",
              "created_at": 1487889741
            }
        """
        url = self.base / 'oauth/device/token'
        r = await self.session.post(url, json={
            "code": device_code,
            "client_id": TRAKT_CLIENT_ID,
            "client_secret": TRAKT_CLIENT_SECRET,
        })
        if r.status == 200:
            return 'done', await r.json()
        if r.status == 400:
            return 'pending', None
        raise Exception(r.status)

    async def device_auth_flow(self):
        """Device authentication flow."""
        data = await self.device_code()
        end_time = time() + data['expires_in']
        yield data
        while end_time - time() > 0:
            status, tokens = await self.get_token(data['device_code'])
            if status == 'done':
                yield True, tokens
                return
            if status == 'pending':
                time_left = end_time - time()
                yield False, time_left
            await asyncio.sleep(data['interval'])

    async def close(self):
        await self.session.close()
