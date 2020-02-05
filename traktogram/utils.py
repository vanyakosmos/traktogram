import string
import textwrap
from collections import defaultdict
from typing import List

from traktogram.trakt import CalendarShow


digs = string.digits + string.ascii_letters


def dedent(text: str):
    return textwrap.dedent(text).strip('\n')


def group_by_show(episodes: List[CalendarShow]) -> List[List[CalendarShow]]:
    groups = defaultdict(list)
    for e in episodes:
        key = (e.show.ids.trakt, e.first_aired)
        groups[key].append(e)
    # todo: split big groups
    return list(groups.values())


def compress_int(n: int, base=32):
    if n < base:
        return digs[n]
    else:
        return compress_int(n // base, base) + digs[n % base]


def decompress_int(n: str, base=32, index=0):
    if n:
        return pow(base, index) * digs.index(n[-1]) + decompress_int(n[:-1], base, index + 1)
    return 0
