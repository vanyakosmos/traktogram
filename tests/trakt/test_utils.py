import pytest

from traktogram.trakt.utils import get_9anime_url


@pytest.mark.asyncio
async def test_get_9anime_url():
    url = await get_9anime_url("alchemist")
    assert url.startswith('https://9anime.to/watch/fullmetal-alchemist')
