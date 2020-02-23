import asyncio
import re

from lxml import html
from slugify import slugify
from yarl import URL

from .session import Session


white_space_re = re.compile(r'[\n\s]+')
generic_season_ending = re.compile(r'(1st|first|2nd|second|3rd|third|\d+th) season$', re.I)


class MALService(Session):
    @classmethod
    def extract_title(cls, text: bytes):
        root = html.fromstring(text)
        row = root.xpath("//div[@id='content']/descendant::table[last()]/descendant::tr[2]")[0]
        info = row.xpath("td[2]")[0]
        link = info.xpath(".//a[starts-with(@href, 'https://myanimelist.net/anime/')]")[0]
        title = link.text_content().strip()
        title = white_space_re.sub(' ', title)
        return title

    @classmethod
    def make_animedao_url(cls, title: str, episode: int):
        slug = slugify(title)
        return f'https://animedao.com/watch-online/{slug}-episode-{episode}'

    async def get_title(self, query: str):
        url = URL('https://myanimelist.net/anime.php')
        url = url.update_query(q=query)
        r = await self.session.get(url)
        text = await r.read()
        return self.extract_title(text)


class AnimeDaoService(Session):
    @classmethod
    def search_url(cls, query: str):
        url = URL('https://animedao.com/search/')
        url = url.update_query(key=query)
        return url

    async def episode_url(
        self, show_name: str, season: int, episode: int, episode_abs: int = None,
        season_name=None,
    ):
        """
        Scrap anime url from MAL. Extract slug and generate animedao url.
        """
        if season_name is None:
            season_name = str(season)
        if season == 1:
            query = show_name
        else:
            query = f"{show_name} {season_name}"
        episode_abs = episode if episode_abs is None else episode_abs
        mal = MALService(self.session)
        if season == 1:
            title = await mal.get_title(query)
            title1 = title
        else:
            title1, title = await asyncio.gather(
                mal.get_title(show_name),
                mal.get_title(query)
            )
        merged_seasons = mal.make_animedao_url(title1, episode_abs)
        split_seasons = mal.make_animedao_url(title, episode)

        if season == 1 or generic_season_ending.search(title) or title == title1:
            return merged_seasons
        return split_seasons


class NineAnimeService(Session):
    episode_num = re.compile(r'ep (\d+)/\d+', re.I)

    @classmethod
    def search_url(cls, query: str):
        url = URL('https://9anime.to/filter')
        url = url.update_query([
            # on 9anime only keyword filter works properly...
            ('keyword', query),
        ])
        return url

    @classmethod
    def extract_episode_url(cls, html_data: bytes, episode: int = None):
        root = html.fromstring(html_data)
        items = root.xpath("(//div[@class='film-list']/div[@class='item'])")
        for item in items:
            el = item.xpath(".//div[@class='status']//div[@class='dub' or @class='special' or @class='movie']")
            if not el:
                break
        else:
            # everything is dubbed/special/movie
            return
        href = item.xpath('.//a')[0].get("href")

        if episode is not None:
            ep = item.xpath(".//div[@class='status']//div[@class='ep']")[0].text
            ep = int(cls.episode_num.search(ep)[1])
            if ep >= episode:
                return href
            return
        return href

    async def get_9anime_url(self, title, episode: int = None, **kwargs):
        """
        Scrap anime url from 9anime.to.
        If `episode` parameter is specified then url will be returned only if number
        of aired episode is greater or equal to `episode` param.
        """
        url = self.search_url(title)
        r = await self.session.get(url)
        data = await r.read()
        return self.extract_episode_url(data, episode)
