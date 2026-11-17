from django.http import Http404
from rest_framework.exceptions import (
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    NotFound,
    ParseError,
    Throttled,
    UnsupportedMediaType,
)
from rest_framework.views import exception_handler

FALLBACK_MESSAGE = '요청을 처리할 수 없습니다.'

# DRF 기본 문구는 영어이므로, 프론트엔드에 그대로 노출되는 문구를 한글로 고정한다.
FIXED_MESSAGES = (
    (NotAuthenticated, '회원 인증이 필요합니다.'),
    (MethodNotAllowed, '허용되지 않는 요청 방식입니다.'),
    (ParseError, '요청 본문을 해석할 수 없습니다.'),
    (UnsupportedMediaType, '지원하지 않는 요청 형식입니다.'),
    (NotFound, '요청한 대상을 찾을 수 없습니다.'),
    (Http404, '요청한 대상을 찾을 수 없습니다.'),
)


def _extract_message(data):
    if isinstance(data, dict):
        if 'detail' in data and isinstance(data['detail'], str):
            return data['detail']
        for value in data.values():
            msg = _extract_message(value)
            if msg:
                return msg
    elif isinstance(data, list):
        for item in data:
            msg = _extract_message(item)
            if msg:
                return msg
    elif isinstance(data, str):
        return data
    return ''


def _message_for(exc, data):
    if isinstance(exc, Throttled):
        if exc.wait is None:
            return '요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.'
        return f'요청이 너무 많습니다. {int(exc.wait) + 1}초 후 다시 시도해 주세요.'

    for exc_class, message in FIXED_MESSAGES:
        if isinstance(exc, exc_class):
            return message

    return _extract_message(data) or FALLBACK_MESSAGE


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        # 처리되지 않은 예외는 config.urls.handler500 이 JSON 500으로 응답한다.
        return None

    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        response.status_code = 401

    response.data = {'detail': _message_for(exc, response.data)}
    return response
