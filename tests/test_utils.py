import pytest

from traktogram.utils import split_group


class TestSplitGroup:
    def test_simple(self):
        gs = split_group([1, 2, 3], max_num=4)
        assert gs == [[1, 2, 3]]

    def test_two(self):
        gs = split_group([1, 2, 3, 4], max_num=3)
        assert gs == [[1, 2], [3, 4]]

    def test_three(self):
        gs = split_group([1, 2, 3, 4, 5, 6, 7], max_num=3)
        assert gs == [[1, 2, 3], [4, 5], [6, 7]]


@pytest.mark.asyncio
async def test_creds(store):
    async for user_id, creds in store.creds_iter():
        assert creds.access_token
