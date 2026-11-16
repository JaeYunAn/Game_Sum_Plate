from rest_framework.permissions import BasePermission


class IsMemberAuthenticated(BasePermission):
    message = '회원 인증이 필요합니다.'

    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, 'is_authenticated', False))
