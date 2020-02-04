import asyncio
import logging
from datetime import datetime
from time import time
from typing import List, Optional

import aiohttp
from yarl import URL

from .models import CalendarShow, Episode, ShowEpisode
from ..config import TRAKT_CLIENT_ID, TRAKT_CLIENT_SECRET


logger = logging.getLogger(__name__)


class TraktClient:
    def __init__(self):
        self.base = URL('https://api.trakt.tv')
        self.session = aiohttp.ClientSession()
        self.access_token = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @property
    def headers(self):
        return {
            'Content-type': 'application/json',
            'Authorization': f'Bearer {self.access_token}',
            'trakt-api-key': TRAKT_CLIENT_ID,
            'trakt-api-version': '2',
        }

    def auth(self, access_token):
        self.access_token = access_token
        return self

    async def device_code(self) -> dict:
        """
        Response example::

            {
              "device_code": "foo",
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
              "access_token": "foo",
              "token_type": "bearer",
              "expires_in": 7200,
              "refresh_token": "bar",
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

    async def calendar_shows(self, start_date=None, days=7, extended=False) -> List[CalendarShow]:
        if not start_date:
            start_date = datetime.utcnow().date().strftime('%Y-%m-%d')
        url = self.base / f'calendars/my/shows/{start_date}/{days}'
        if extended:
            url = url.update_query(extended='full')
        r = await self.session.get(url, headers=self.headers)
        data = await r.json()
        return [CalendarShow.from_dict(e) for e in data]

    async def episode_summary(self, show_id: str, season: int, episode: int, extended=False) -> Episode:
        url = self.base / f'shows/{show_id}/seasons/{season}/episodes/{episode}'
        if extended:
            url = url.update_query(extended='full')
        r = await self.session.get(url, headers=self.headers)
        data = await r.json()
        return Episode.from_dict(data)

    async def search_id(self, provider, id, type=None, extended=False):
        url = self.base / f'search/{provider}/{id}'
        if type:
            url = url.update_query(type=type)
        if extended:
            url = url.update_query(extended='full')
        r = await self.session.get(url, headers=self.headers)
        data = await r.json()
        return data

    async def get_episode(self, episode_id, extended=False) -> Optional[ShowEpisode]:
        data = await self.search_id('trakt', episode_id, type='episode', extended=extended)
        if not data:
            return
        return ShowEpisode.from_dict(data[0])

    async def get_history(self, episode_id, extended=False) -> List[ShowEpisode]:
        url = self.base / 'sync/history/episodes' / str(episode_id)
        if extended:
            url = url.update_query(extended='full')
        r = await self.session.get(url, headers=self.headers)
        data = await r.json()
        return [ShowEpisode.from_dict(e) for e in data]

    async def add_to_history(self, episode_id) -> ShowEpisode:
        url = self.base / 'sync/history'
        data = {
            'episodes': [{
                'ids': {'trakt': episode_id}
            }]
        }
        r = await self.session.post(url, json=data, headers=self.headers)
        data = await r.json()
        return data

    async def remove_from_history(self, episode_id) -> ShowEpisode:
        url = self.base / 'sync/history/remove'
        data = {
            'episodes': [{
                'ids': {'trakt': episode_id}
            }]
        }
        r = await self.session.post(url, json=data, headers=self.headers)
        data = await r.json()
        return data

    async def close(self):
        await self.session.close()
