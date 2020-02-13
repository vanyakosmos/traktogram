import logging
import logging.config
import textwrap

from .config import LOG_LEVEL, LOG_LEVEL_ROOT


def squish(text: str):
    text = textwrap.dedent(text)
    lines = text.strip(' \n').splitlines()
    return ' '.join(lines)


class CustomHandler(logging.StreamHandler):
    def __init__(self):
        super(CustomHandler, self).__init__()

    def emit(self, record):
        messages = record.msg.splitlines()
        for message in messages:
            record.msg = message
            super(CustomHandler, self).emit(record)


def setup_logging():
    logging.addLevelName(logging.DEBUG, 'DEBG')
    logging.addLevelName(logging.WARNING, 'WARN')
    logging.addLevelName(logging.ERROR, 'ERRO')
    logging.addLevelName(logging.CRITICAL, 'CRIT')

    LOGGING_CONFIG = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                '()': 'colorlog.ColoredFormatter',
                'format': squish("""
                    {purple}{asctime}{reset}
                    {log_color}{levelname}{reset}
                    \033[2m{name:>29s}{reset}:{cyan}{lineno:<3d}{reset}
                    {blue}>{reset}
                    {message_log_color}{message}{reset}
                """),
                'log_colors': {
                    'DEBG': 'cyan',
                    'INFO': 'green',
                    'WARN': 'yellow',
                    'ERRO': 'red',
                    'CRIT': 'red,bg_white',
                },
                'secondary_log_colors': {
                    'message': {
                        'INFO': 'green',
                        'WARN': 'yellow',
                        'ERRO': 'red',
                        'CRIT': 'red'
                    }
                },
                'datefmt': '%H:%M:%S',
                'style': '{',
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'formatter': 'default',
                'class': 'traktogram.logging_setup.CustomHandler',
            },
        },
        'loggers': {
            '': {
                'handlers': ['console'],
                'level': LOG_LEVEL_ROOT,
                'propagate': False
            },
            'traktogram': {
                'handlers': ['console'],
                'level': LOG_LEVEL,
                'propagate': False
            },
            '__main__': {
                'handlers': ['console'],
                'level': LOG_LEVEL,
                'propagate': False
            },
        },
    }
    logging.config.dictConfig(LOGGING_CONFIG)
