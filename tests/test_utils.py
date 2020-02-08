from datetime import timedelta

import pytest

from traktogram.trakt import CalendarEpisode
from traktogram.utils import group_by_show, split_group


@pytest.fixture('class')
def make_calendar_episode(request):
    def make(first_aired, show_id, episode_number=1):
        return CalendarEpisode.from_dict({
            'show': {
                'ids': {'trakt': show_id, 'slug': 'slug'},
                'title': 'show',
                'year': 2020,
            },
            'episode': {
                'ids': {'trakt': 1},
                'title': 'episode',
                'season': 1,
                'number': episode_number,
            },
            'first_aired': first_aired,
        })

    meth = staticmethod(make)
    request.cls.make_ce = meth
    request.cls.make_calendar_episode = meth
    return make


@pytest.mark.usefixtures('make_calendar_episode')
class TestGroupByShow:
    def test_simple(self):
        es = [
            self.make_ce('123', 1, 1),
        ]
        groups = group_by_show(es)
        assert groups == [[es[0]]]

    def test_two_same(self):
        es = [
            self.make_ce('123', 1, 1),
            self.make_ce('123', 1, 2),
        ]
        groups = group_by_show(es)
        assert groups == [[es[0], es[1]]]

    def test_two_diff(self):
        es = [
            self.make_ce('123', 1, 1),
            self.make_ce('123', 2, 2),
        ]
        groups = group_by_show(es)
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
        groups = group_by_show(es, max_num=3)
        assert groups == [[es[0], es[1], es[3]], [es[4], es[5]], [es[2]]]

    def test_postpone(self):
        es = [
            self.make_ce('123', 1, 1),
            self.make_ce('123', 1, 2),
            self.make_ce('123', 1, 3),
        ]
        groups = group_by_show(es, max_num=2)
        assert groups == [[es[0], es[1]], [es[2]]]
        assert es[0].first_aired + timedelta(seconds=1) == es[2].first_aired


class TestSplitGroup:
    def test_simple(self):
        gs = split_group([1, 2, 3], max_num=4)
        assert gs == [[1, 2, 3]]

    def test_two(self):
        gs = split_group([1, 2, 3, 4], max_num=3)
        assert gs == [[1, 2], [3, 4]]

    def test_three(self):
        gs = split_group([1, 2, 3, 4, 5, 6, 7], max_num=3)
        assert gs == [[1, 2, 3], [4, 5], [6, 7]]
