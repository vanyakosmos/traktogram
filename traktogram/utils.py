import math
import string
import textwrap
from datetime import datetime
from functools import singledispatch
from types import FunctionType
from typing import List

import aioredis.util
from aiogram.utils.callback_data import CallbackDataFilter


digs = string.digits + string.ascii_letters


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
    for e in lens:
        res.append(group[a:a + e])
        a += e
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


@singledispatch
def to_str(v):
    return str(v)


@to_str.register
def _(v: FunctionType):
    return f"Function({v.__module__}:{v.__qualname__})"


@to_str.register
def _(v: datetime):
    return v.isoformat()


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


def a(*args, **kwargs):
    return args, kwargs
