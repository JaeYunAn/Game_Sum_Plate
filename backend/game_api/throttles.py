"""요청 횟수 제한.

허용 횟수는 settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] 에서 scope 별로 정한다.
"""

import hashlib

from rest_framework.throttling import SimpleRateThrottle


def client_ip(request):
    """접속자 IP.

    서버는 Cloudflare Tunnel → Caddy 뒤에 있어 REMOTE_ADDR 가 항상 127.0.0.1 이다.
    Cloudflare 가 붙여 주는 CF-Connecting-IP 가 실제 접속자 주소다. Caddy 는 127.0.0.1 에만
    바인딩되어 있으므로 이 헤더를 임의로 넣을 수 있는 것은 서버 PC 자신뿐이다.
    """
    return (
        request.META.get('HTTP_CF_CONNECTING_IP')
        or request.META.get('REMOTE_ADDR')
        or 'unknown'
    )


class _ClientIPThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': client_ip(request)}


class _MemberThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        member = request.user
        if member is None:
            return None
        return self.cache_format % {'scope': self.scope, 'ident': member.pk}


class RegisterThrottle(_ClientIPThrottle):
    scope = 'register'


class LoginThrottle(_ClientIPThrottle):
    scope = 'login'


class LoginNicknameThrottle(SimpleRateThrottle):
    """한 닉네임에 대한 로그인 시도 횟수 제한(여러 IP에서 나눠 시도하는 경우 대비)."""

    scope = 'login_nickname'

    def get_cache_key(self, request, view):
        data = request.data
        nickname = data.get('nickname') if isinstance(data, dict) else None
        if not isinstance(nickname, str) or not nickname.strip():
            return None
        ident = hashlib.sha256(nickname.strip().casefold().encode('utf-8')).hexdigest()
        return self.cache_format % {'scope': self.scope, 'ident': ident}


class AccountThrottle(_MemberThrottle):
    scope = 'account'


class GameStartThrottle(_MemberThrottle):
    scope = 'game_start'


class RecordSaveThrottle(_MemberThrottle):
    scope = 'record_save'
