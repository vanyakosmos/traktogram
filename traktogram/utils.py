import string
import textwrap
from collections import defaultdict
from datetime import datetime
from typing import List, Callable, Union

from traktogram.trakt import CalendarEpisode


digs = string.digits + string.ascii_letters


def dedent(text: str):
    return textwrap.dedent(text).strip('\n')


def group_by_show(episodes: List[CalendarEpisode], max_group=6) -> List[List[CalendarEpisode]]:
    """
    :param episodes:
    :param max_group: max number of elements in group
    :return:
    """
    groups = defaultdict(list)
    splitter = defaultdict(int)
    for e in episodes:
        show_key = (e.show.ids.trakt, e.first_aired)
        key = (*show_key, splitter[show_key])
        if len(groups[key]) >= max_group:
            splitter[show_key] += 1
            key = (*show_key, splitter[show_key])
        groups[key].append(e)
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
