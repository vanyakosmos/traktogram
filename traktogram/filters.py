import argparse
import re
from typing import Tuple

from aiogram.dispatcher.filters import BoundFilter
from aiogram.types import Message


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


class CmdArgs(BoundFilter):
    key = 'command_args'

    def __init__(self, command_args: Tuple[tuple, dict], parser=None):
        self.command_args = command_args
        self.parser = parser or self.setup_parser(command_args)

    def setup_parser(self, command_args: Tuple[tuple, dict]):
        parser = ArgumentParser()
        for args, kwargs in command_args:
            parser.add_argument(*args, **kwargs)
        return parser

    async def check(self, message: Message):
        if not message.is_command():
            return False

        command = message.text.split()[0][1:]
        command, _, mention = command.partition('@')

        if mention and mention != (await message.bot.me).username:
            return False

        resp = {'command_args': None, 'command_args_error': None}
        parts = re.split(r'\s+', message.text)
        try:
            args = self.parser.parse_args(parts[1:])
            resp['command_args'] = args
            return resp
        except ValueError as e:
            resp['command_args_error'] = str(e)
            return resp
        except (Exception, SystemExit):
            return False
