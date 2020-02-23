from .anime import AnimeDaoService, MALService, NineAnimeService
from ..models import Show


async def watch_urls(show: Show):
    if show.language == 'ja':
        async with MALService() as mal:
            query = await mal.get_title(show.title)
            yield 'animedao', AnimeDaoService.search_url(query)
            yield '9anime', NineAnimeService.search_url(query)
