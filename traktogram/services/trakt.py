import asyncio
import logging
from datetime import datetime
from time import time
from typing import List, Optional

from aiogram.utils.mixins import ContextInstanceMixin
from aiohttp import ClientSession
from yarl import URL

from .session import Session
from ..config import TRAKT_CLIENT_ID, TRAKT_CLIENT_SECRET
from ..models import CalendarEpisode, Episode, Season, ShowEpisode


logger = logging.getLogger(__name__)


class TraktException(Exception):
    def __init__(self, data):
        self.data = data


class TraktClient(Session, ContextInstanceMixin):
    def __init__(self, session: ClientSession = None, access_token: str = None):
        super().__init__(session)
        self.base = URL('https://api.trakt.tv')
        self.access_token = access_token

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        await self.session.close()

    def auth(self, access_token=None) -> 'TraktClient':
        return TraktClient(self.session, access_token)

    @property
    def is_authenticated(self):
        return self.access_token is not None

    @property
    def headers(self):
        headers = {
            'Content-type': 'application/json',
            'trakt-api-key': TRAKT_CLIENT_ID,
            'trakt-api-version': '2',
        }
        if self.is_authenticated:
            headers['Authorization'] = f'Bearer {self.access_token}'
        return headers

    # = = = = = = = = = = = = = = = = = = = = = = = =
    # AUTHENTICATION
    # = = = = = = = = = = = = = = = = = = = = = = = =

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

    async def refresh_token(self, refresh_token):
        url = self.base / 'oauth/token'
        r = await self.session.post(url, json={
            'refresh_token': refresh_token,
            'client_id': TRAKT_CLIENT_ID,
            'client_secret': TRAKT_CLIENT_SECRET,
            'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
            'grant_type': 'refresh_token'
        })
        data = await r.json()
        return data

    async def revoke_token(self):
        url = self.base / 'oauth/revoke'
        await self.session.post(url, json={
            'token': self.access_token,
            'client_id': TRAKT_CLIENT_ID,
            'client_secret': TRAKT_CLIENT_SECRET,
        })

    # = = = = = = = = = = = = = = = = = = = = = = = =
    # HISTORY
    # = = = = = = = = = = = = = = = = = = = = = = = =

    async def get_history(self, episode_id, extended=True) -> List[ShowEpisode]:
        url = self.base / 'sync/history/episodes' / str(episode_id)
        if extended:
            url = url.update_query(extended='full')
        r = await self.session.get(url, headers=self.headers)
        data = await r.json()
        return [ShowEpisode(**e) for e in data]

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

    async def watched(self, episode_id):
        return len(await self.get_history(episode_id)) != 0

    # = = = = = = = = = = = = = = = = = = = = = = = =
    # CALENDAR AND SEARCH
    # = = = = = = = = = = = = = = = = = = = = = = = =

    async def calendar_shows(self, start_date=None, days=7, extended=True) -> List[CalendarEpisode]:
        if not start_date:
            start_date = datetime.utcnow().date().strftime('%Y-%m-%d')
        url = self.base / f'calendars/my/shows/{start_date}/{days}'
        if extended:
            url = url.update_query(extended='full')
        r = await self.session.get(url, headers=self.headers)
        data = await r.json()
        if r.status != 200:
            raise TraktException(data)
        return [CalendarEpisode(**e) for e in data]

    async def episode_summary(self, show_id: str, season: int, episode: int, extended=True) -> Episode:
        url = self.base / f'shows/{show_id}/seasons/{season}/episodes/{episode}'
        if extended:
            url = url.update_query(extended='full')
        r = await self.session.get(url, headers=self.headers)
        data = await r.json()
        return Episode(**data)

    async def season_summary(self, show_id: str, season: int, extended=True):
        url = self.base / f'shows/{show_id}/seasons'
        if extended:
            url = url.update_query(extended='full')
        r = await self.session.get(url, headers=self.headers)
        seasons = await r.json()
        for s in seasons:
            if s['number'] == season:
                return Season(**s)

    async def search_by_id(self, provider, id, type=None, extended=True):
        url = self.base / f'search/{provider}/{id}'
        if type:
            url = url.update_query(type=type)
        if extended:
            url = url.update_query(extended='full')
        r = await self.session.get(url, headers=self.headers)
        data = await r.json()
        return data

    async def search_by_episode_id(self, episode_id, extended=True) -> Optional[ShowEpisode]:
        data = await self.search_by_id('trakt', episode_id, type='episode', extended=extended)
        if not data:
            return
        return ShowEpisode(**data[0])
