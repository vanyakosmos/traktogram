import os


env_file = os.getenv('ENV_FILE')
if env_file:
    import dotenv
    dotenv.load_dotenv(env_file)

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_LEVEL_ROOT = os.getenv('LOG_LEVEL_ROOT', 'WARNING')
TRAKT_CLIENT_ID = os.getenv('TRAKT_CLIENT_ID')
TRAKT_CLIENT_SECRET = os.getenv('TRAKT_CLIENT_SECRET')
REDIS_URL = os.getenv('REDIS_URL')
WORKER = os.getenv('WORKER', '1') == '1'
