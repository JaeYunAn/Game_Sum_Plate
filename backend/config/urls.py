from django.http import JsonResponse
from django.urls import include, path

urlpatterns = [
    path('', include('game_api.urls')),
]


# 프론트엔드는 모든 응답을 JSON({"detail": ...})으로 읽는다.
# Django 기본 HTML 오류 페이지 대신 같은 형식의 JSON으로 응답한다.

def _json_error(message, status):
    return JsonResponse(
        {'detail': message},
        status=status,
        json_dumps_params={'ensure_ascii': False},
    )


def bad_request(request, exception=None):
    return _json_error('잘못된 요청입니다.', 400)


def not_found(request, exception=None):
    return _json_error('요청한 주소를 찾을 수 없습니다.', 404)


def server_error(request):
    return _json_error('서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.', 500)


handler400 = 'config.urls.bad_request'
handler404 = 'config.urls.not_found'
handler500 = 'config.urls.server_error'
