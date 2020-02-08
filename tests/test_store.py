import pytest

from traktogram.store import store, redis_cache_async


def test_redis_cache():
    try:
        assert store['title'] is None
        store['title'] = 'foo'
        assert store['title'] == 'foo'
    finally:
        del store['title']


@redis_cache_async()
async def func(d):
    return {'foo': d}


@pytest.mark.asyncio
async def test_redis_cache_dec():
    key = 'func:[[4], {}]'
    try:
        assert store[key] is None
        assert await func(4) == {'foo': 4}
        assert store[key] == '{"foo": 4}'
        assert await func(4) == {'foo': 4}
    finally:
        del store[key]
