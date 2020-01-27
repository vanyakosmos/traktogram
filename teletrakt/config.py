import os

import dotenv


dotenv.load_dotenv()
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_LEVEL_ROOT = os.getenv('LOG_LEVEL_ROOT', 'WARNING')
TRAKT_CLIENT_ID = os.getenv('TRAKT_CLIENT_ID')
TRAKT_CLIENT_SECRET = os.getenv('TRAKT_CLIENT_SECRET')

LOGGING_CONFIG = {
    'version': 1,
    'formatters': {
        'default': {
            '()': 'colorlog.ColoredFormatter',
            'format': (
                '%(log_color)s%(levelname)-8s%(reset)s '
                '%(name)20s%(cyan)s:%(lineno)d%(reset)s '
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
        'teletrakt': {
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
