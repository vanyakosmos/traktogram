import os

import dotenv

dotenv.load_dotenv()
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_LEVEL_ROOT = os.getenv('LOG_LEVEL_ROOT', 'WARNING')
TRAKT_CLIENT_ID = os.getenv('TRAKT_CLIENT_ID')
TRAKT_CLIENT_SECRET = os.getenv('TRAKT_CLIENT_SECRET')
REDIS_URI = os.getenv('REDIS_URI')

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            '()': 'traktogram.utils.LogFormatter',
            'format': (
                '%(purple)s%(asctime)s%(reset)s '
                '%(log_color)s%(levelname)-8s%(reset)s '
                '%(name)15s%(cyan)s:%(lineno)-3d%(reset)s '
                '%(blue)s>%(reset)s '
                '%(message)s'
            ),
            'log_colors': {
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            },
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'formatter': 'default',
            'class': 'logging.StreamHandler',
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
