from traktogram.storage import Storage
from traktogram.services import TraktClient


async def trakt_session(user_id):
    storage = Storage.get_current()
    trakt = TraktClient.get_current()
    creds = await storage.get_creds(user_id)
    sess = trakt.auth(creds.access_token)
    return sess
