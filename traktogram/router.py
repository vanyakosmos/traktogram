import logging
import textwrap
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Dict, Tuple, Union

import aiogram
from aiogram.utils.mixins import ContextInstanceMixin

from .storage import Storage
from .utils import to_str


MaybeContextVar = Union[ContextInstanceMixin, Tuple[ContextVar, Any]]
logger = logging.getLogger(__name__)


def log_register(f):
    def dec(self, callback, *args, **kwargs):
        lines = []
        if args:
            lines.append(', '.join(map(to_str, args)))
        if kwargs:
            pairs = ((k, v) for k, v in kwargs.items() if v)
            lines.append(', '.join(map(lambda e: f"{e[0]}={e[1]!r}", pairs)))
        text = '\n'.join(lines)
        text = textwrap.indent(text, prefix='    ')
        logger.debug(f"registered \033[1m{callback.__name__}\033[0m:\n{text}")
        return f(self, callback, *args, **kwargs)

    return dec


@dataclass
class Holder:
    args: tuple
    kwargs: dict


class Router:
    def __init__(self):
        self.commands_help = {}
        self.message_handlers = []
        self.callback_query_handlers = []
        self.errors_handlers = []

    def command_handler(self, command, *custom_filters, help=None, regexp=None, content_types=None, state=None,
                        run_task=None, **kwargs):
        commands = command if isinstance(command, (list, tuple, set)) else [command]
        if help:
            for cmd in commands:
                self.commands_help[cmd] = help

        def decorator(callback):
            self.message_handlers.append(
                Holder(args=(callback, *custom_filters),
                       kwargs=dict(
                           commands=commands, regexp=regexp, content_types=content_types,
                           state=state, run_task=run_task, **kwargs))
            )
            return callback

        return decorator

    def message_handler(self, *custom_filters, regexp=None, content_types=None, state=None,
                        run_task=None, **kwargs):
        def decorator(callback):
            self.message_handlers.append(
                Holder(args=(callback, *custom_filters),
                       kwargs=dict(
                           regexp=regexp, content_types=content_types, state=state,
                           run_task=run_task, **kwargs))
            )
            return callback

        return decorator

    def callback_query_handler(self, *custom_filters, state=None, run_task=None, **kwargs):
        def decorator(callback):
            self.callback_query_handlers.append(
                Holder(args=(callback, *custom_filters),
                       kwargs=dict(state=state, run_task=run_task, **kwargs))
            )
            return callback

        return decorator

    def errors_handler(self, *custom_filters, exception=None, **kwargs):
        def decorator(callback):
            self.errors_handlers.append(
                Holder(args=(callback, *custom_filters),
                       kwargs=dict(exception=exception, **kwargs))
            )
            return callback

        return decorator


class Dispatcher(aiogram.Dispatcher):
    def __init__(self, *args, storage: Storage = None, **kwargs):
        super(Dispatcher, self).__init__(*args, storage=storage, **kwargs)
        self.commands_help = {}
        self.storage = storage
        self.context_vars: Dict[str, MaybeContextVar] = {}

        for register in ('register_message_handler', 'register_callback_query_handler', 'register_errors_handler'):
            method = getattr(self.__class__, register)
            method = log_register(method)
            setattr(self.__class__, register, method)

    def command_handler(self, command, help=None, **kwargs):
        if help:
            self.commands_help[command] = help

        def decorator(callback):
            self.register_message_handler(callback, commands=[command], **kwargs)
            return callback

        return decorator

    def add_router(self, router: Router):
        self.commands_help.update(router.commands_help)
        for holder in router.message_handlers:
            self.register_message_handler(*holder.args, **holder.kwargs)
        for holder in router.callback_query_handlers:
            self.register_callback_query_handler(*holder.args, **holder.kwargs)
        for holder in router.errors_handlers:
            self.register_errors_handler(*holder.args, **holder.kwargs)

    def gen_context(self):
        for key, var in self.context_vars.items():
            if isinstance(var, ContextInstanceMixin):
                yield key, var
            else:
                yield key, var[1]

    def contextualize(self, *args: MaybeContextVar):
        for arg in args:
            if isinstance(arg, ContextInstanceMixin):
                arg.__class__.set_current(arg)
            else:
                var, val = arg
                # noinspection PyArgumentList
                var.set(val)

    async def start_polling(self, *args, **kwargs):
        if self._polling:
            raise RuntimeError('Polling already started')
        self.contextualize(*self.context_vars.values())
        return await super(Dispatcher, self).start_polling(*args, **kwargs)
