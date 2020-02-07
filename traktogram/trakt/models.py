import re
from typing import Type, TypeVar

from related import ChildField, DateTimeField, IntegerField, StringField, immutable, mutable, to_model
from yarl import URL


T = TypeVar('T')


class Model:
    @classmethod
    def from_dict(cls: Type[T], data: dict = None, **kwargs) -> T:
        """Factory that allows to pass extra kwrags without errors."""
        data = data.copy() if data else {}
        data.update(kwargs)
        return to_model(cls, data)


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
    def watch_url(self):
        if self.show is None:
            return None, None
        if self.show.language == 'ja':
            slug = self.show.title.lower()
            slug = re.sub('[^a-z ]', '', slug).strip()
            slug = '-'.join(slug.split())
            return 'animedao', f'https://animedao.com/watch-online/{slug}-episode-{self.number}'
        return None, None


@mutable
class ShowEpisode(Model):
    show = ChildField(Show)
    episode = ChildField(Episode)

    @classmethod
    def from_dict(cls: Type[T], data: dict = None, **kwargs) -> T:
        se = super(ShowEpisode, cls).from_dict(data, **kwargs)
        se.episode.show = se.show
        return se


@mutable
class CalendarEpisode(ShowEpisode):
    first_aired = DateTimeField()
