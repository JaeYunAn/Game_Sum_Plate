import os
from pathlib import Path

from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
DEFAULT_DB_PATH = PROJECT_ROOT / 'number_addition.db'
DATABASE_PATH = Path(os.environ.get('NUMBER_ADDITION_DB_PATH', DEFAULT_DB_PATH))


def _load_secret_key():
    """SECRET_KEY 를 코드에 적어 두지 않는다.

    DJANGO_SECRET_KEY 환경변수가 있으면 그 값을 쓰고, 없으면 처음 실행할 때
    프로젝트 폴더에 .django_secret_key 파일을 만들어 보관한다(.gitignore 대상).
    """
    from_env = os.environ.get('DJANGO_SECRET_KEY')
    if from_env:
        return from_env

    key_file = PROJECT_ROOT / '.django_secret_key'
    if key_file.exists():
        saved = key_file.read_text(encoding='utf-8').strip()
        if saved:
            return saved

    generated = get_random_secret_key()
    key_file.write_text(generated, encoding='utf-8')
    return generated


SECRET_KEY = _load_secret_key()

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
    # scope 별 허용 횟수. 적용 대상은 game_api/throttles.py 참고.
    'DEFAULT_THROTTLE_RATES': {
        'register': '10/hour',         # 접속 IP 당 회원가입
        'login': '10/min',             # 접속 IP 당 로그인 시도
        'login_nickname': '30/hour',   # 닉네임 당 로그인 시도
        'account': '10/min',           # 회원 당 탈퇴(비밀번호 확인) 시도
        'game_start': '20/min',        # 회원 당 게임 시작
        'record_save': '20/min',       # 회원 당 기록 저장
    },
}

# DEBUG=False 에서도 서버 오류(500)의 원인을 콘솔에서 볼 수 있게 한다.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        # 4xx(잘못된 비밀번호 등)는 정상적인 흐름이므로 5xx 만 남긴다.
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
