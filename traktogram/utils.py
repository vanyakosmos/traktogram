import math
import os
import re
import string
import textwrap
from datetime import datetime
from functools import singledispatch
from logging import LogRecord
from types import FunctionType
from typing import Callable, List, Union

import aioredis.util
import colorlog
from aiogram.utils.callback_data import CallbackDataFilter


digs = string.digits + string.ascii_letters
ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
episode_num = re.compile(r'ep (\d+)/\d+', re.I)


class LogFormatter(colorlog.ColoredFormatter):
    def format(self, record: LogRecord):
        text = record.getMessage()
        record.msg = ''
        record.args = ()
        prefix = super(LogFormatter, self).format(record)
        plain_prefix = ansi_escape.sub('', prefix)
        lines = text.splitlines()
        res = [f"{prefix}{lines[0]}"]
        for line in lines[1:]:
            res.append(' ' * len(plain_prefix) + line)
        return '\n'.join(res)


def dedent(text: str):
    return textwrap.dedent(text).strip('\n')


def split_group(group: list, max_num=8) -> List[List]:
    """
    Split ≈evenly into subgroups with at most `max_num` elements.
    Example::

        max_num = 8
        > 8 -> 8
        > 9 -> 5 4
        > 14 -> 7 7
        > 19 -> 7 6 6
    """
    num = math.ceil(len(group) / max_num)  # number of groups
    base = len(group) // num  # base number in each group
    lens = [base] * num  # sizes of each group
    for i in range(len(group) - base * num):
        lens[i] += 1
    res = []
    a = 0  # anchor
    for l in lens:
        res.append(group[a:a + l])
        a += l
    return res


def compress_int(n: int, base=32):
    if n < base:
        return digs[n]
    else:
        return compress_int(n // base, base) + digs[n % base]


def decompress_int(n: str, base=32, index=0):
    if n:
        return pow(base, index) * digs.index(n[-1]) + decompress_int(n[:-1], base, index + 1)
    return 0


def make_calendar_notification_task_id(func: Union[str, Callable], user_id, show_id, dt: datetime, *episodes_ids):
    """
    Create unique job ID.
    Naturally show+time is enough for uniquely identify job user-wise. But because multi
    notification can be split into multiple messages we also need to accept extra data
    with episodes ids.
    """
    if not isinstance(func, str):
        func = func.__name__
    dt = dt.isoformat()
    id = f"{func}-{user_id}-{show_id}-{dt}"
    if episodes_ids:
        episodes_ids = '|'.join(map(str, episodes_ids))
        id = f'{id}-{episodes_ids}'
    return id


@singledispatch
def to_str(v):
    return str(v)


@to_str.register
def _(v: FunctionType):
    return f"Function({v.__module__}:{v.__qualname__})"


@to_str.register
def _(v: CallbackDataFilter):
    return f"CallbackDataFilter({v.config})"


def parse_redis_uri(uri):
    (host, port), options = aioredis.util.parse_url(uri)
    return {
        'host': host,
        'port': port,
        **options,
    }
