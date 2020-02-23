from lxml import html
from yarl import URL

from traktogram.services.session import Session


class PirateBayService(Session):
    @classmethod
    def search_url(cls, query: str):
        url = URL('https://thepiratebay.org/search')
        return url / query

    @classmethod
    def extract_magnet_link(cls, data: bytes):
        root = html.fromstring(data)
        el = root.xpath("/descendant::a[starts-with(@href, 'magnet:')][1]")
        if el:
            return el[0].get('href')

    async def magnet_link(self, query: str):
        url = self.search_url(query)
        r = await self.session.get(url)
        data = await r.read()
        return self.extract_magnet_link(data)


class NyaaSiService(Session):
    @classmethod
    def search_url(cls, query: str):
        url = URL('https://nyaa.si')
        url = url.update_query(
            f='0',
            c='1_2',  # translated anime
            q=query,
        )
        return url
