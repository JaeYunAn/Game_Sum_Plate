import hashlib
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import Member


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


class BearerTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None

        scheme, _, token = auth_header.partition(' ')
        cleaned_token = token.strip()
        if scheme.lower() != 'bearer' or not cleaned_token:
            raise AuthenticationFailed('인증 정보가 올바르지 않습니다.')

        member = Member.objects.filter(token_hash=hash_token(cleaned_token)).first()
        if member is None:
            raise AuthenticationFailed('유효하지 않은 회원 인증입니다.')

        return (member, cleaned_token)

    def authenticate_header(self, request):
        return 'Bearer'
