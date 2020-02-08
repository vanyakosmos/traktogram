import math
import string
import textwrap
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable, List, Union

from traktogram.trakt import CalendarEpisode


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
    for l in lens:
        res.append(group[a:a + l])
        a += l
    return res


def group_by_show(episodes: List[CalendarEpisode], max_num=8) -> List[List[CalendarEpisode]]:
    """
    Group episodes by show and datetime when they were aired.
    Split big groups into smaller ones.
    Slightly postpone episodes from big groups so that they will be scheduled in order.

    :param episodes: episodes to group
    :param max_num: max number of elements in group
    :return:
    """
    groups = defaultdict(list)
    for e in episodes:
        key = (e.show.ids.trakt, e.first_aired)
        groups[key].append(e)
    res = []
    for group in groups.values():
        gs = split_group(group, max_num)
        for i, g in enumerate(gs):
            for ce in g:
                ce.first_aired += timedelta(seconds=i)
        res.extend(gs)
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
