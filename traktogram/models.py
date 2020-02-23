from collections import defaultdict
from datetime import datetime, timedelta
from typing import List

from pydantic import BaseModel
from yarl import URL

from .utils import split_group


class IDs(BaseModel):
    trakt: int


class ShowIDs(IDs):
    slug: str


class Show(BaseModel):
    ids: ShowIDs
    title: str
    year: int
    language: str = None

    @property
    def id(self):
        return self.ids.trakt

    @property
    def url(self):
        return URL('https://trakt.tv/shows') / self.ids.slug


class Season(BaseModel):
    ids: IDs
    title: str
    number: int
    aired_episodes: int
    episode_count: int
    rating: float

    @property
    def id(self):
        return self.ids.trakt


class Episode(BaseModel):
    ids: IDs
    title: str
    season: int
    number: int
    number_abs: int = None

    @property
    def id(self):
        return self.ids.trakt

    def url(self, show: Show):
        return show.url / f'seasons/{self.season}/episodes/{self.number}'


class ShowEpisode(BaseModel):
    show: Show
    episode: Episode

    @property
    def url(self):
        season_url = self.show.url / f'seasons/{self.episode.season}'
        return season_url / f'episodes/{self.episode.number}'


class CalendarEpisode(ShowEpisode):
    first_aired: datetime

    @classmethod
    def group_by_show(cls, episodes: List['CalendarEpisode'], max_num=8) -> List[List['CalendarEpisode']]:
        """
        Group episodes by show and datetime when they were aired.
        Split big groups into smaller ones.
        Slightly postpone episodes from big groups so that they will be scheduled in order.

        :param episodes: episodes to group
        :param max_num: max number of elements in group
        :return:
        """
        groups = defaultdict(list)
        for e in episodes:
            key = (e.show.id, e.first_aired)
            groups[key].append(e)
        res = []
        for group in groups.values():
            gs = split_group(group, max_num)
            for i, g in enumerate(gs):
                for ce in g:
                    ce.first_aired += timedelta(seconds=i)
            res.extend(gs)
        return res
