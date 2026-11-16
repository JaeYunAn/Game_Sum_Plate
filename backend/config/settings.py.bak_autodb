import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
DEFAULT_DB_PATH = PROJECT_ROOT / 'number_addition.db'
DATABASE_PATH = Path(os.environ.get('NUMBER_ADDITION_DB_PATH', DEFAULT_DB_PATH))

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-0#vw7-s-oag9bi63%2!ik@ano4&m5$t&)f6yz3&o793h+#6^!z')

DEBUG = os.environ.get('DJANGO_DEBUG', 'false').lower() == 'true'

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        'DJANGO_ALLOWED_HOSTS',
        '127.0.0.1,localhost,.trycloudflare.com',
    ).split(',')
    if host.strip()
]

INSTALLED_APPS = [
    'rest_framework',
    'game_api.apps.GameApiConfig',
]

MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = []

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DATABASE_PATH,
        'OPTIONS': {
            'timeout': 10,
        },
    }
}

APPEND_SLASH = False

LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = False
USE_TZ = True

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'UNAUTHENTICATED_USER': None,
    'EXCEPTION_HANDLER': 'game_api.exceptions.custom_exception_handler',
}
