from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from rest_framework.views import exception_handler


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
    return '요청을 처리할 수 없습니다.'


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        response.status_code = 401

    response.data = {'detail': _extract_message(response.data)}
    return response
