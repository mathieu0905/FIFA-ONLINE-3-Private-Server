"""Native 8088 admin integration for global player data."""
from pathlib import Path
import os
from .player_database import Database

database = None

def install(hc, admin):
    global database
    if database is not None:
        return
    server = Path(hc.HERE)
    work = os.environ.get('FO3_PLAYER_EDITOR_WORK', str(server.parent / 'player-editor-workspace'))
    database = Database(server, os.environ.get('FO3_GAME', str(server.parent / '32795')), work)
    for name in ('search', 'detail', 'status', 'stage', 'remove', 'build', 'publish', 'save'):
        method = database.queue if name == 'build' else getattr(database, name)
        def endpoint(params, method=method):
            with database.lock:
                return method(params)
        admin.API['database_' + name] = endpoint
    admin.READ_ONLY.update('database_' + n for n in ('search', 'detail', 'status'))

def page():
    return (Path(__file__).parent / 'index.html').read_bytes()
