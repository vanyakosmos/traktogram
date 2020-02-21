import asyncio
import re

from aiohttp import ClientSession
from lxml import html
from slugify import slugify
from yarl import URL


white_space_re = re.compile(r'[\n\s]+')
generic_season_ending = re.compile(r'(1st|first|2nd|second|3rd|third|\d+th) season$', re.I)


class AnimeService:
    def extract_mal_title(self, text: bytes):
        root = html.fromstring(text)
        row = root.xpath("//div[@id='content']/descendant::table[last()]/descendant::tr[2]")[0]
        info = row.xpath("td[2]")[0]
        link = info.xpath(".//a[starts-with(@href, 'https://myanimelist.net/anime/')]")[0]
        title = link.text_content().strip()
        title = white_space_re.sub(' ', title)
        return title

    async def get_mal_title(self, session: ClientSession, query: str):
        url = URL('https://myanimelist.net/anime.php')
        url = url.update_query(q=query)
        r = await session.get(url)
        text = await r.read()
        return self.extract_mal_title(text)

    def make_animedao_url(self, title: str, episode: int):
        slug = slugify(title)
        return f'https://animedao.com/watch-online/{slug}-episode-{episode}'


async def get_animedao_url(show_name: str, season: int, episode: int, episode_abs: int = None, season_name=None,
                           both=False, **kwargs):
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
    anime = AnimeService()
    async with ClientSession(trust_env=True, **kwargs) as session:
        if season == 1:
            title = await anime.get_mal_title(session, query)
            title1 = title
        else:
            title1, title = await asyncio.gather(
                anime.get_mal_title(session, show_name),
                anime.get_mal_title(session, query)
            )
    merged_seasons = anime.make_animedao_url(title1, episode_abs)
    split_seasons = anime.make_animedao_url(title, episode)

    if both:
        # return url for merged and split versions
        return merged_seasons, split_seasons
    if season == 1 or generic_season_ending.search(title) or title == title1:
        return merged_seasons
    return split_seasons
