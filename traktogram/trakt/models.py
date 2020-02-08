from typing import Type

from related import ChildField, DateTimeField, IntegerField, StringField, immutable, mutable
from yarl import URL

from traktogram.models import Model, ModelType
from .utils import get_9anime_url


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
