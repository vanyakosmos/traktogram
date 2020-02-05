import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template


env = Environment(loader=FileSystemLoader(Path(__file__).parent / 'templates'))
white_spaces = re.compile(r' +')
leading_space = re.compile(r'(^ +| +$)', re.MULTILINE)


def render_string(template: str, **kwargs):
    template = Template(template)
    return _render(template, **kwargs)


def render_html(template_name: str, **kwargs):
    template = env.get_template(f'{template_name}.html')
    return _render(template, **kwargs)


def _render(template: Template, **kwargs):
    text = template.render(**kwargs)
    text = text.replace('\n', ' ').replace(r'<br/>', '\n')
    text = white_spaces.sub(' ', text)
    text = leading_space.sub('', text)
    text = text.strip(' \n')
    return text
