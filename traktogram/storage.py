import asyncio
import json
import logging
from datetime import timedelta
from functools import wraps
from types import FunctionType
from typing import Optional

import aioredis
import related
from aiogram.contrib.fsm_storage.redis import RedisStorage2

from traktogram.config import REDIS_URL
from traktogram.models import Model
from traktogram.utils import parse_redis_uri


CREDS_KEY = 'creds'
CACHE_KEY = 'cache'

logger = logging.getLogger(__name__)


@related.immutable
class Creds(Model):
    access_token = related.StringField()
    refresh_token = related.StringField()


class HelpersMixin:
    async def hscan_iter(self: 'Storage', name, match=None, count=None):
        conn = await self.redis()
        cursor = '0'
        while cursor != 0:
            cursor, data = await conn.hscan(name, cursor=cursor, match=match, count=count)
            for item in data:
                yield item


class CredsMixin(HelpersMixin):
    @property
    async def creds_conn_key(self: 'Storage'):
        conn = await self.redis()
        creds_key = self.generate_key(CREDS_KEY)
        return conn, creds_key

    async def has_creds(self, user_id):
        conn, key = await self.creds_conn_key
        return await conn.hexists(key, user_id)

    async def save_creds(self, user_id, creds):
        conn, key = await self.creds_conn_key
        return await conn.hset(key, user_id, json.dumps(creds))

    async def get_creds(self, user_id) -> Optional[Creds]:
        conn, key = await self.creds_conn_key
        data = await conn.hget(key, user_id)
        if data:
            data = json.loads(data.decode())
            return Creds.from_dict(data)

    async def remove_creds(self, user_id):
        conn, key = await self.creds_conn_key
        return await conn.hdel(key, user_id)

    async def creds_iter(self):
        conn, key = await self.creds_conn_key
        async for user_id, tokens in self.hscan_iter(key):
            data = json.loads(tokens.decode())
            yield (
                user_id.decode(),
                Creds.from_dict(data),
            )


class CacheMixin:
    CACHE_EXPIRY = int(timedelta(weeks=1).total_seconds())

    @property
    async def cache_conn_key(self: 'Storage'):
        conn = await self.redis()
        key = self.generate_key(CACHE_KEY)
        return conn, key

    async def save_cache(self, key, value, **kwargs):
        conn, ckey = await self.cache_conn_key
        name = f"{ckey}:{key}"
        kwargs.setdefault('expire', self.CACHE_EXPIRY)
        return await conn.set(name, value, **kwargs)

    async def get_cache(self, key, expire=None):
        conn, ckey = await self.cache_conn_key
        name = f"{ckey}:{key}"
        res = await conn.get(name)
        if res:
            if expire:
                await conn.expire(name, expire)
            return res

    async def delete_cache(self, key):
        conn, ckey = await self.cache_conn_key
        name = f"{ckey}:{key}"
        return await conn.delete(name)

    @classmethod
    def make_func_key(cls, func: FunctionType, *args, **kwargs):
        key = ":".join(map(repr, (*args, *kwargs.values())))
        key = f'{func.__module__}.{func.__qualname__}:{key}'
        return key

    def cache(self, expire=CACHE_EXPIRY):
        def wrap(f):
            @wraps(f)
            async def dec(*args, **kwargs):
                key = self.make_func_key(f, *args, **kwargs)
                res = await self.get_cache(key)
                if res:
                    return json.loads(res)
                res = await f(*args, **kwargs)
                await self.save_cache(key, json.dumps(res), expire=expire)
                return res

            return dec

        return wrap

    async def cached_call(self, func: FunctionType, *args, expire=CACHE_EXPIRY, **kwargs):
        key = self.make_func_key(func, *args, **kwargs)
        res = await self.get_cache(key, expire)
        if res:
            return json.loads(res)
        maybe_coro = func(*args, **kwargs)
        if asyncio.iscoroutinefunction(func):
            res = await maybe_coro
        else:
            res = maybe_coro
        await self.save_cache(key, json.dumps(res), expire=expire)
        return res


def build_redis_uri(host='localhost', port=6379, db=None, password=None, **kwargs):
    auth = f":****@" if password else ''
    uri = f"redis://{auth}{host}:{port}"
    if db is not None:
        uri += f'/{db}'
    return uri


class Storage(RedisStorage2, CredsMixin, CacheMixin):
    def __init__(self, uri=REDIS_URL, **kwargs):
        kwargs.setdefault('prefix', 'traktogram')
        if uri:
            options = parse_redis_uri(uri)
            for k, v in options.items():
                kwargs.setdefault(k, v)
        redis_uri = build_redis_uri(**kwargs)
        logger.debug(f"Connecting to redis: {redis_uri}")
        super().__init__(**kwargs)

    async def redis(self) -> aioredis.Redis:
        async with self._connection_lock:
            if self._redis is None or self._redis.closed:
                self._redis = await aioredis.create_redis_pool(
                    (self._host, self._port),
                    db=self._db, password=self._password, ssl=self._ssl,
                    minsize=1, maxsize=self._pool_size,
                    loop=self._loop, **self._kwargs
                )
        return self._redis

    async def close(self):
        async with self._connection_lock:
            if self._redis and not self._redis.closed:
                self._redis.close()
