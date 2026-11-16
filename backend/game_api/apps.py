from django.apps import AppConfig
from django.db.backends.signals import connection_created


def configure_sqlite_connection(sender, connection, **kwargs):
    if connection.vendor != 'sqlite':
        return
    with connection.cursor() as cursor:
        cursor.execute('PRAGMA foreign_keys = ON;')
        cursor.execute('PRAGMA busy_timeout = 10000;')
        cursor.execute('PRAGMA journal_mode = WAL;')


class GameApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'game_api'

    def ready(self):
        connection_created.connect(
            configure_sqlite_connection,
            dispatch_uid='game_api_configure_sqlite_connection',
        )
