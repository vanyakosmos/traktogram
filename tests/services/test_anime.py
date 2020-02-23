import asyncio

import pytest

from traktogram.services.anime import AnimeDaoService


@pytest.mark.parametrize("show_name, season_name, season, episode, episode_abs, animedao_url", [
    # season 1
    ('my hero academia', None, 1, 1, 1, 'https://animedao.com/watch-online/boku-no-hero-academia-episode-1'),
    ('attack on titan', None,  1, 1, 1, 'https://animedao.com/watch-online/shingeki-no-kyojin-episode-1'),
    ('mob psycho 100', None,  1, 1, 1, 'https://animedao.com/watch-online/mob-psycho-100-episode-1'),
    ('the seven deadly sins', 'The Seven Deadly Sins',  1, 1, 1, 'https://animedao.com/watch-online/nanatsu-no-taizai-episode-1'),
    ('one punch man', 'One Punch Man: OVA Road to Hero',  1, 1, 1, 'https://animedao.com/watch-online/one-punch-man-episode-1'),
    # season 2
    ('my hero academia', None,  2, 2, 25, 'https://animedao.com/watch-online/boku-no-hero-academia-episode-25'),
    ('attack on titan', None, 2, 2, 25, 'https://animedao.com/watch-online/shingeki-no-kyojin-episode-25'),
    ('mob psycho 100', None, 2, 2, 25, 'https://animedao.com/watch-online/mob-psycho-100-ii-episode-2'),
    ('the seven deadly sins', 'Revival of the Commandments', 2, 2, 25, 'https://animedao.com/watch-online/nanatsu-no-taizai-imashime-no-fukkatsu-episode-2'),
    ('one punch man', None, 2, 2, 25, 'https://animedao.com/watch-online/one-punch-man-2-episode-2'),
])
@pytest.mark.slow
async def test_get_animedao_url(show_name, season_name, season, episode, episode_abs, animedao_url, loop):
    async with AnimeDaoService() as ad:
        url = await ad.episode_url(show_name, season_name=season_name, season=season, episode=episode,
                                   episode_abs=episode_abs)
        assert url == animedao_url
