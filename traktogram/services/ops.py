from .anime import AnimeDaoService, MALService, NineAnimeService
from .torrent import NyaaSiService, PirateBayService
from .trakt import TraktClient
from ..models import Show
from ..storage import Storage


async def watch_urls(show: Show):
    if show.language == 'ja':
        async with MALService() as mal:
            query = await mal.get_title(show.title)
            yield 'nyaasi', NyaaSiService.search_url(query)
            yield 'animedao', AnimeDaoService.search_url(query)
            yield '9anime', NineAnimeService.search_url(query)
    else:
        yield 'torrent', PirateBayService.search_url(show.title)


async def trakt_session(user_id):
    storage = Storage.get_current()
    trakt = TraktClient.get_current()
    creds = await storage.get_creds(user_id)
    sess = trakt.auth(creds.access_token)
    return sess
