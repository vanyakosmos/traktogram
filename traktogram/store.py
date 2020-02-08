import json
from collections import defaultdict
from datetime import timedelta
from functools import wraps

import redis

from .config import REDIS_URI


class RedisStore:
    def __init__(self, uri=REDIS_URI, prefix='traktogram'):
        self.client = redis.Redis.from_url(uri)
        self.prefix = prefix
        self.key_tokens = self.make_key('tokens')
        self.key_titles = self.make_key('titles')

    def __getitem__(self, item: str):
        key = self.make_key('cache', item)
        res = self.client.get(key)
        if res:
            return res.decode()

    def __setitem__(self, key, value):
        key = self.make_key('cache', key)
        self.client.set(key, value, ex=int(timedelta(days=1).total_seconds()))

    def __delitem__(self, key):
        key = self.make_key('cache', key)
        self.client.delete(key)

    def make_key(self, *args):
        return ':'.join([self.prefix, *args])

    def is_auth(self, user_id):
        self.client.hexists(self.key_tokens, str(user_id))

    def save_tokens(self, user_id, tokens):
        self.client.hset(self.key_tokens, str(user_id), json.dumps(tokens))

    def get_tokens(self, user_id):
        data = self.client.hget(self.key_tokens, str(user_id))
        return json.loads(data.decode())

    def users_tokens_iter(self):
        for user_id, tokens in self.client.hscan_iter(self.key_tokens):
            yield (
                user_id.decode(),
                json.loads(tokens.decode()),
            )

    def user_access_tokens_iter(self):
        for user_id, tokens in self.users_tokens_iter():
            yield user_id, tokens['access_token']

    def get_access_token(self, user_id):
        tokens = self.get_tokens(user_id)
        return tokens['access_token']

    def get_title(self, slug: str):
        title = self.client.hget(self.key_titles, slug)
        if title:
            return title.decode()


def make_func_key(func, *args, **kwargs):
    key = json.dumps((args, kwargs))
    key = f'{func.__name__}:{key}'
    return key


def redis_cache_async():
    def wrap(f):
        @wraps(f)
        async def dec(*args, **kwargs):
            key = make_func_key(f, *args, **kwargs)
            res = store[key]
            if res:
                return json.loads(res)
            res = await f(*args, **kwargs)
            store[key] = json.dumps(res)
            return res

        return dec

    return wrap


store = RedisStore()
state = defaultdict(lambda: {'state': None, 'context': None})
