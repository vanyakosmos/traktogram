from datetime import datetime

from attr import attrib, attrs


def nested_attrib(cls):
    def converter(kw):
        if hasattr(cls, 'from_dict'):
            return cls.from_dict(kw)
        return cls(**kw)

    return attrib(type=cls, converter=converter)


def datetime_attrib(**kwargs):
    return attrib(type=datetime, converter=lambda s: datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%f%z"), **kwargs)


# noinspection PyArgumentList,PyUnresolvedReferences
class Model:
    @classmethod
    def from_dict(cls, data: dict = None, **kwargs):
        """Factory that allows to pass extra kwrags without errors."""
        data = data.copy() if data else {}
        data.update(kwargs)
        return cls(**{
            a.name: data[a.name]
            for a in cls.__attrs_attrs__
            if a.name in data
        })


@attrs
class IDs(Model):
    trakt = attrib(type=int)
    slug = attrib(type=str, default=None)


@attrs
class Show(Model):
    ids = nested_attrib(IDs)
    title = attrib(type=str)
    year = attrib(type=int)
    language = attrib(type=str)


@attrs
class Episode(Model):
    ids = nested_attrib(IDs)
    title = attrib(type=str)
    season = attrib(type=int)
    number = attrib(type=int)
    number_abs = attrib(type=int, default=None)


@attrs
class CalendarShow(Model):
    episode = nested_attrib(Episode)
    show = nested_attrib(Show)
    first_aired = datetime_attrib()

    @property
    def watch_url(self):
        if self.show.language == 'ja':
            slug = self.show.title.lower()
            slug = slug.strip(' -')
            slug = '-'.join(slug.split())
            return 'animedao', f'https://animedao.com/watch-online/{slug}-episode-{self.episode.number}'
        return None, None
