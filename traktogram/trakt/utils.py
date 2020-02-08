import aiohttp
from lxml import html
from yarl import URL

from traktogram.updater import storage


@storage.cache()
async def get_9anime_url(title):
    async with aiohttp.ClientSession() as s:
        url = URL('https://9anime.to/filter')
        url = url.update_query([
            ('keyword', title),
            ('type[]', 'series'),
            ('type[]', 'ova'),
            ('type[]', 'ona'),
            ('language[]', 'subbed'),
        ])
        r = await s.get(url)
        root = html.fromstring(await r.read())
    el = root.xpath("(//div[@class='film-list']//a)[1]")[0]
    return el.get("href")
