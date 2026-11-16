import secrets
import time
import uuid

from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import BearerTokenAuthentication, hash_token
from .models import Member, Record
from .permissions import IsMemberAuthenticated
from .serializers import NicknameSerializer, RecordCreateSerializer, RecordSerializer


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = NicknameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nickname = serializer.validated_data['nickname']
        token = secrets.token_urlsafe(32)
        now_ms = int(time.time() * 1000)

        try:
            with transaction.atomic():
                member = Member.objects.create(
                    nickname=nickname,
                    token_hash=hash_token(token),
                    created_at=now_ms,
                )
        except IntegrityError:
            return Response(
                {'detail': '이미 사용 중인 닉네임입니다.'},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                'id': member.id,
                'nickname': member.nickname,
                'token': token,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = NicknameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nickname = serializer.validated_data['nickname']
        token = secrets.token_urlsafe(32)

        with transaction.atomic():
            member = Member.objects.filter(nickname=nickname).first()
            if member is None:
                return Response(
                    {'detail': '등록되지 않은 닉네임입니다.'},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            member.token_hash = hash_token(token)
            member.save(update_fields=['token_hash'])

        return Response(
            {
                'id': member.id,
                'nickname': member.nickname,
                'token': token,
            },
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    authentication_classes = [BearerTokenAuthentication]
    permission_classes = [IsMemberAuthenticated]

    def get(self, request):
        return Response(
            {
                'id': request.user.id,
                'nickname': request.user.nickname,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    authentication_classes = [BearerTokenAuthentication]
    permission_classes = [IsMemberAuthenticated]

    def post(self, request):
        replacement_token = secrets.token_urlsafe(32)
        request.user.token_hash = hash_token(replacement_token)
        request.user.save(update_fields=['token_hash'])
        return Response({'message': '로그아웃되었습니다.'}, status=status.HTTP_200_OK)


class AccountView(APIView):
    authentication_classes = [BearerTokenAuthentication]
    permission_classes = [IsMemberAuthenticated]

    def delete(self, request):
        with transaction.atomic():
            request.user.delete()
        return Response({'message': '회원탈퇴가 완료되었습니다.'}, status=status.HTTP_200_OK)


class RecordsView(APIView):
    def get_authenticators(self):
        if self.request and self.request.method == 'POST':
            return [BearerTokenAuthentication()]
        return []

    def get_permissions(self):
        if self.request and self.request.method == 'POST':
            return [IsMemberAuthenticated()]
        return [AllowAny()]

    def get(self, request):
        raw_duration = request.query_params.get('duration', '60')
        try:
            duration = int(raw_duration)
        except (TypeError, ValueError):
            duration = None

        if duration not in (30, 60):
            return Response(
                {'detail': '게임 시간은 30초 또는 60초여야 합니다.'},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        game_mode = request.query_params.get('gameMode', 'score')
        if game_mode not in ('score', 'survival'):
            return Response(
                {'detail': '올바른 게임모드를 선택하세요.'},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        rows = Record.objects.filter(
            duration=duration,
            game_mode=game_mode,
        ).order_by('-score', '-accuracy', 'average_response_time', 'created_at')[:10]

        return Response(RecordSerializer(rows, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = RecordCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        record = Record.objects.create(
            id=str(uuid.uuid4()),
            member=request.user,
            nickname=request.user.nickname,
            duration=data['duration'],
            game_mode=data['gameMode'],
            correct=data['correct'],
            wrong=data['wrong'],
            accuracy=data['accuracy'],
            score=data['score'],
            average_response_time=data['averageResponseTime'],
            created_at=int(time.time() * 1000),
        )
        return Response(RecordSerializer(record).data, status=status.HTTP_201_CREATED)
