from collections import defaultdict
from datetime import timedelta
from typing import Type, TypeVar, List

from related import ChildField, DateTimeField, IntegerField, StringField, immutable, mutable, to_dict, to_model
from yarl import URL

from .utils import get_9anime_url, split_group


ModelType = TypeVar('ModelType')


class Model:
    @classmethod
    def from_dict(cls: Type[ModelType], data: dict = None, **kwargs) -> ModelType:
        """Factory that allows to pass extra kwargs without errors."""
        data = data.copy() if data else {}
        data.update(kwargs)
        return to_model(cls, data)

    def to_dict(self, **kwargs) -> dict:
        return to_dict(self, **kwargs)


@immutable
class IDs(Model):
    trakt = IntegerField()


@immutable
class ShowIDs(IDs):
    slug = StringField()


@immutable
class Show(Model):
    ids = ChildField(ShowIDs)
    title = StringField()
    year = IntegerField()
    language = StringField(required=False)

    @property
    def url(self):
        return URL('https://trakt.tv/shows') / self.ids.slug


@mutable()
class Episode(Model):
    ids = ChildField(IDs)
    title = StringField()
    season = IntegerField()
    number = IntegerField()
    number_abs = IntegerField(required=False)
    show = ChildField(Show, required=False)

    @property
    def season_url(self):
        if self.show:
            return self.show.url / 'seasons' / str(self.season)

    @property
    def url(self):
        if self.show:
            return self.season_url / 'episodes' / str(self.number)

    @property
    async def watch_url(self):
        if self.show is None:
            return None, None
        if self.show.language == 'ja':
            url = await get_9anime_url(self.show.title)
            return '9anime', url
        return None, None


@mutable
class ShowEpisode(Model):
    show = ChildField(Show)
    episode = ChildField(Episode)

    @classmethod
    def from_dict(cls: Type[ModelType], data: dict = None, **kwargs) -> ModelType:
        se = super(ShowEpisode, cls).from_dict(data, **kwargs)
        se.episode.show = se.show
        return se


@mutable
class CalendarEpisode(ShowEpisode):
    first_aired = DateTimeField()

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
            key = (e.show.ids.trakt, e.first_aired)
            groups[key].append(e)
        res = []
        for group in groups.values():
            gs = split_group(group, max_num)
            for i, g in enumerate(gs):
                for ce in g:
                    ce.first_aired += timedelta(seconds=i)
            res.extend(gs)
        return res
