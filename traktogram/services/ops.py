from .anime import AnimeDaoService, MALService, NineAnimeService, KimCartoonService
from .torrent import NyaaSiService
from .trakt import TraktClient
from ..models import Show, Episode
from ..storage import Storage


async def watch_urls(show: Show, episode: Episode):
    if 'anime' in show.genres:
        async with MALService() as mal:
            query = await mal.get_title(show.title)
            yield 'nyaasi', NyaaSiService.search_url(query)
            yield 'animedao', AnimeDaoService.search_url(query)
            yield '9anime', NineAnimeService.search_url(query)
    if 'animation' in show.genres:
        yield 'kimcartoon', KimCartoonService.episode_url(show.title, episode.season, episode.number)
        yield 'kimcartoon#2', KimCartoonService.episode_url(show.title, episode.season, episode.number, episode.title)


async def trakt_session(user_id):
    storage = Storage.get_current()
    trakt = TraktClient.get_current()
    creds = await storage.get_creds(user_id)
    sess = trakt.auth(creds.access_token)
    return sess
