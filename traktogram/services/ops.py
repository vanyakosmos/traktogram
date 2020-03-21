import logging

from . import anime
from .torrent import NyaaSiService
from .trakt import TraktClient
from ..models import Episode, Show
from ..storage import Storage


logger = logging.getLogger(__name__)


async def watch_urls(show: Show, episode: Episode):
    if 'anime' in show.genres:
        async with anime.MALService() as mal:
            title = await mal.get_title(show.title)
            yield 'nyaasi[t]', NyaaSiService.search_url(title)
            yield 'dao[q]', anime.AnimeDaoService.search_url(title)
            yield '9anime[q]', anime.NineAnimeService.search_url(title, episode.season)
            try:
                yield 'pahe[s]', await anime.AnimepaheService(mal.session) \
                    .season_url(title, episode.season)
            except Exception as e:
                logger.exception(e)
            yield 'kisa[e]', anime.AnimekisaService.episode_url(title, episode.season, episode.number)
    if 'animation' in show.genres:
        yield 'kimcartoon', anime.KimCartoonService.episode_url(
            show.title, episode.season, episode.number)
        yield 'kimcartoon#2', anime.KimCartoonService.episode_url(
            show.title, episode.season, episode.number, episode.title)


async def trakt_session(user_id, storage=None, trakt=None):
    storage = storage or Storage.get_current()
    trakt = trakt or TraktClient.get_current()
    creds = await storage.get_creds(user_id)
    sess = trakt.auth(creds.access_token)
    return sess
