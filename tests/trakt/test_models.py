from related import to_model

from traktogram.trakt.models import IDs, Show, Episode


class TestSerialization:
    def test_simple(self):
        ids = IDs.from_dict({'trakt': 1})
        assert ids.trakt == 1

    def test_partial(self):
        show = Show.from_dict({
            'ids': {'trakt': 1, 'slug': 'slug'},
            'title': 'title',
            'year': 2020
        })
        assert show.ids.trakt == 1
        assert show.language is None

    def test_overflow(self):
        ids: IDs = to_model(IDs, {
            'trakt': 1,
            'slug': 'fds',
            'tmdb': 1
        })
        assert ids.trakt == 1
        assert not hasattr(ids, 'slug')
        assert not hasattr(ids, 'tmdb')

    def test_nested(self):
        show = Show.from_dict({
            'ids': {
                'trakt': 1,
                'slug': 'slug',
            },
            'title': 'title',
            'year': 2020,
        })
        assert show.title == 'title'
        assert show.ids.trakt == 1


def test_properties():
    e = Episode.from_dict({
        'ids': {'trakt': 1},
        'title': 'episode',
        'season': 1,
        'number': 1,
    })
    assert e.url is None

    e = Episode.from_dict({
        'ids': {'trakt': 1},
        'title': 'episode',
        'season': 1,
        'number': 1,
        'show': {
            'ids': {'trakt': 1, 'slug': 'show'},
            'title': 'show',
            'year': 2020,
        }
    })
    assert str(e.url) == 'https://trakt.tv/shows/show/seasons/1/episodes/1'
