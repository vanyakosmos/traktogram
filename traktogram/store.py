import json
from collections import defaultdict

import redis

from .config import REDIS_URI


class RedisStore:
    def __init__(self, uri=REDIS_URI, prefix='traktogram'):
        self.client = redis.Redis.from_url(uri)
        self.prefix = prefix
        self.key_tokens = self.key('tokens')

    def key(self, *args):
        return ':'.join([self.prefix, *args])

    def is_auth(self, user_id):
        self.client.hexists(self.key_tokens, str(user_id))

    def save_creds(self, user_id, tokens):
        self.client.hset(self.key_tokens, str(user_id), json.dumps(tokens))

    def load_creds(self, user_id):
        data = self.client.hget(self.key_tokens, str(user_id))
        return json.loads(data.decode())

    def users_tokens_iter(self):
        for user_id, tokens in self.client.hscan_iter(self.key_tokens):
            yield (
                user_id.decode(),
                json.loads(tokens.decode()),
            )


store = RedisStore()
state = defaultdict(lambda: {'state': None, 'context': None})
