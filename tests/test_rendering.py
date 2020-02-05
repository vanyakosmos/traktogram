import textwrap

from traktogram.rendering import render_html, render_string
from traktogram.trakt.models import ShowEpisode
from traktogram.utils import dedent


class TestRender:
    def test_simple(self):
        text = render_string(textwrap.dedent("""
                foo bar
            """))
        assert text == "foo bar"

    def test_new_line(self):
        text = render_string(textwrap.dedent("""
            foo
            
            
            bar
            <br/>
            
            baz
        """))
        assert text == "foo bar\nbaz"

    def test_leading_psace(self):
        text = render_string(textwrap.dedent("""
            foo
            <br/>
            {% if foo %}
              bar
            {%  endif %}
        """), foo=True)
        assert text == "foo\nbar"


class TestMessages:
    def test_new_episode(self):
        se = ShowEpisode.from_dict({
            'show': {
                'title': 'show',
                'year': 2020,
                'ids': {'trakt': 1},
            },
            'episode': {
                'title': 'episode',
                'season': 1,
                'number': 1,
                'ids': {'trakt': 1},
            }
        })
        text = render_html(
            'new_episode_message',
            show=se.show,
            episode=se.episode,
            episode_url='https://example.com',
        )
        assert text == dedent("""
            <b>show</b> 1x1 <a href="https://example.com">"episode"</a>
            Season 1 / Episode 1
        """)

    def test_new_episodes(self):
        se = ShowEpisode.from_dict({
            'show': {
                'title': 'show',
                'year': 2020,
                'ids': {'trakt': 1},
            },
            'episode': {
                'title': 'episode',
                'season': 1,
                'number': 1,
                'ids': {'trakt': 1},
            }
        })
        text = render_html(
            'new_episodes_message',
            show=se.show,
            episodes=[se.episode, se.episode],
        )
        assert text == dedent("""
            <b>show</b>
            
            1x1 <a href="">"episode"</a> 
            1x1 <a href="">"episode"</a>
        """)
