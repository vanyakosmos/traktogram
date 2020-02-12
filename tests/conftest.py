import pytest

from traktogram.config import REDIS_URL
from traktogram.models import CalendarEpisode
from traktogram.storage import Storage


def pytest_addoption(parser):
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


@pytest.fixture
async def store():
    store = Storage(uri=REDIS_URL, db=1)
    try:
        yield store
    finally:
        conn = await store.redis()
        await conn.flushdb()
        await store.close()
        await store.wait_closed()


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
