import json
from collections import defaultdict
from pathlib import Path


class FSStore:
    def __init__(self, filepath: str):
        self.fp = Path(filepath)
        self.data = defaultdict(dict)
        if self.fp.exists():
            self.data.update(json.loads(self.fp.read_text()))

    def is_auth(self, user_id):
        return str(user_id) in self.data

    def save_creds(self, user_id, tokens):
        self.data[user_id]['tokens'] = tokens
        self.save()

    def save(self):
        self.fp.write_text(json.dumps(self.data, indent=4))


store = FSStore('../db.json')
state = defaultdict(lambda: {'state': None, 'context': None})
