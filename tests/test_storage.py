import pytest

from traktogram.storage import Storage


@pytest.mark.asyncio
async def test_cache():
    store = Storage()
    await store.save_cache('foo', 'bar')
    assert await store.get_cache('foo') == b'bar'
    await store.delete_cache('foo')
    assert await store.get_cache('foo') is None
    await store.close()
    await store.wait_closed()


@pytest.mark.asyncio
async def test_creds():
    store = Storage()
    async for user_id, creds in store.creds_iter():
        assert creds.access_token
    await store.close()
    await store.wait_closed()


@pytest.mark.asyncio
async def test_redis_cache_dec():
    store = Storage()

    @store.cache()
    async def func(d):
        return {'foo': d}

    key = store.make_func_key(func, 4)
    try:
        assert await store.get_cache(key) is None
        assert await func(4) == {'foo': 4}
        assert await store.get_cache(key) == b'{"foo": 4}'
        assert await func(4) == {'foo': 4}
    finally:
        await store.delete_cache(key)
        await store.close()
        await store.wait_closed()
