from datetime import timedelta

import pytest

from traktogram.models import CalendarEpisode, IDs, Show


class TestSerialization:
    def test_simple(self):
        ids = IDs(**{'trakt': 1})
        assert ids.trakt == 1

    def test_partial(self):
        show = Show(**{
            'ids': {'trakt': 1, 'slug': 'slug'},
            'title': 'title',
            'year': 2020
        })
        assert show.ids.trakt == 1
        assert show.language is None

    def test_overflow(self):
        ids: IDs = IDs(**{
            'trakt': 1,
            'slug': 'fds',
            'tmdb': 1
        })
        assert ids.trakt == 1
        assert not hasattr(ids, 'slug')
        assert not hasattr(ids, 'tmdb')

    def test_nested(self):
        show = Show(**{
            'ids': {
                'trakt': 1,
                'slug': 'slug',
            },
            'title': 'title',
            'year': 2020,
        })
        assert show.title == 'title'
        assert show.ids.trakt == 1


@pytest.mark.usefixtures('make_calendar_episode')
class TestGroupByShow:
    def test_simple(self):
        es = [
            self.make_ce('123', 1, 1),
        ]
        groups = CalendarEpisode.group_by_show(es)
        assert groups == [[es[0]]]

    def test_two_same(self):
        es = [
            self.make_ce('123', 1, 1),
            self.make_ce('123', 1, 2),
        ]
        groups = CalendarEpisode.group_by_show(es)
        assert groups == [[es[0], es[1]]]

    def test_two_diff(self):
        es = [
            self.make_ce('123', 1, 1),
            self.make_ce('123', 2, 2),
        ]
        groups = CalendarEpisode.group_by_show(es)
        assert groups == [[es[0]], [es[1]]]

    def test_split_big(self):
        es = [
            self.make_ce('123', 1, 1),
            self.make_ce('123', 1, 2),
            self.make_ce('123', 2, 1),
            self.make_ce('123', 1, 3),
            self.make_ce('123', 1, 4),
            self.make_ce('123', 1, 5),
        ]
        groups = CalendarEpisode.group_by_show(es, max_num=3)
        assert groups == [[es[0], es[1], es[3]], [es[4], es[5]], [es[2]]]

    def test_postpone(self):
        es = [
            self.make_ce('123', 1, 1),
            self.make_ce('123', 1, 2),
            self.make_ce('123', 1, 3),
        ]
        groups = CalendarEpisode.group_by_show(es, max_num=2)
        assert groups == [[es[0], es[1]], [es[2]]]
        assert es[0].first_aired + timedelta(seconds=1) == es[2].first_aired
