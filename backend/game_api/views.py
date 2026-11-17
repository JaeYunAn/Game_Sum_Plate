import secrets
import time
import uuid

from django.contrib.auth.hashers import check_password, make_password
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import BearerTokenAuthentication, hash_token
from .game_rules import (
    COUNTDOWN_SECONDS,
    DURATIONS,
    GAME_MODES,
    SCORE_DURATION,
    InvalidGameLog,
    UnfinishedGame,
    generate_questions,
    grade,
    grade_survival,
)
from .models import GameSession, Member, Record
from .permissions import IsMemberAuthenticated
from .serializers import (
    DURATION_MESSAGE,
    GAME_MODE_MESSAGE,
    PASSWORD_LENGTH_MESSAGE,
    PASSWORD_MIN_LENGTH,
    GameStartSerializer,
    LoginSerializer,
    RecordSerializer,
    RecordSubmitSerializer,
    RegisterSerializer,
    WithdrawSerializer,
)
from .throttles import (
    AccountThrottle,
    GameStartThrottle,
    LoginNicknameThrottle,
    LoginThrottle,
    RecordSaveThrottle,
    RegisterThrottle,
)

RANKING_SIZE = 10

# 게임이 끝난 뒤 이 시간 안에 저장하지 않으면 기록을 저장할 수 없다.
SAVE_WINDOW_SECONDS = 10 * 60
# 게임 시간이 다 지나기 전에 온 저장 요청은 중도 종료로 보고 거부한다(타이머 오차 1초 허용).
# 생존모드에서는 답안 기록상의 생존 시간이 실제로 지난 시간보다 길 수 없다는 검사에 쓴다.
EARLY_SAVE_TOLERANCE_SECONDS = 1

UNFINISHED_MESSAGE = '게임을 끝까지 진행한 기록만 저장할 수 있습니다.'
INVALID_LOG_MESSAGE = '게임 기록이 올바르지 않아 저장할 수 없습니다.'
# 저장되지 않은 채 남은 게임 정보를 정리하는 기준
SESSION_RETENTION_SECONDS = 60 * 60


def now_ms():
    return int(time.time() * 1000)


def error(message, status_code):
    return Response({'detail': message}, status=status_code)


def account_payload(member, token=None):
    payload = {
        'id': member.id,
        'nickname': member.nickname,
        'hasPassword': member.has_password,
    }
    if token is not None:
        payload['token'] = token
    return payload


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [RegisterThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = secrets.token_urlsafe(32)

        try:
            with transaction.atomic():
                member = Member.objects.create(
                    nickname=serializer.validated_data['nickname'],
                    password_hash=make_password(serializer.validated_data['password']),
                    token_hash=hash_token(token),
                    created_at=now_ms(),
                )
        except IntegrityError:
            return error('이미 사용 중인 닉네임입니다.', status.HTTP_409_CONFLICT)

        return Response(account_payload(member, token), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle, LoginNicknameThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nickname = serializer.validated_data['nickname']
        password = serializer.validated_data['password']
        token = secrets.token_urlsafe(32)
        password_set = False

        with transaction.atomic():
            member = Member.objects.filter(nickname=nickname).first()
            if member is None:
                return error('등록되지 않은 닉네임입니다.', status.HTTP_401_UNAUTHORIZED)

            update_fields = ['token_hash']

            if member.has_password:
                if not check_password(password, member.password_hash):
                    return error('비밀번호가 올바르지 않습니다.', status.HTTP_401_UNAUTHORIZED)
            else:
                # 비밀번호 도입 전에 가입한 회원: 이번에 입력한 비밀번호를 설정한다.
                if len(password) < PASSWORD_MIN_LENGTH:
                    return error(PASSWORD_LENGTH_MESSAGE, status.HTTP_400_BAD_REQUEST)
                member.password_hash = make_password(password)
                update_fields.append('password_hash')
                password_set = True

            # 새 토큰을 발급하면 다른 기기의 기존 로그인은 무효가 된다.
            member.token_hash = hash_token(token)
            member.save(update_fields=update_fields)

        payload = account_payload(member, token)
        payload['passwordSet'] = password_set
        return Response(payload, status=status.HTTP_200_OK)


class MeView(APIView):
    authentication_classes = [BearerTokenAuthentication]
    permission_classes = [IsMemberAuthenticated]

    def get(self, request):
        return Response(account_payload(request.user), status=status.HTTP_200_OK)


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
    throttle_classes = [AccountThrottle]

    def delete(self, request):
        serializer = WithdrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = request.user

        # 로그인된 기기를 잠깐 빌린 사람이 탈퇴시키지 못하도록 비밀번호를 다시 확인한다.
        if member.has_password:
            password = serializer.validated_data.get('password', '')
            if not check_password(password, member.password_hash):
                # 401 은 프론트엔드에서 "로그인 만료"로 처리하므로 403 을 쓴다.
                return error('비밀번호가 올바르지 않습니다.', status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            # 기록은 남기고(records.member_id = NULL) 회원과 진행 중인 게임 정보만 삭제된다.
            member.delete()

        return Response({'message': '회원탈퇴가 완료되었습니다.'}, status=status.HTTP_200_OK)


class GamesView(APIView):
    """게임 시작(점수모드·생존모드): 서버가 문제를 발급하고 시작 시각을 기록한다."""

    authentication_classes = [BearerTokenAuthentication]
    permission_classes = [IsMemberAuthenticated]
    throttle_classes = [GameStartThrottle]

    def post(self, request):
        serializer = GameStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        duration = serializer.validated_data['duration']
        game_mode = serializer.validated_data['gameMode']
        now = now_ms()

        with transaction.atomic():
            # 한 회원은 한 번에 한 판만 진행한다. 새 게임을 시작하면 이전 판은 저장할 수 없다.
            GameSession.objects.filter(member=request.user).delete()
            GameSession.objects.filter(
                started_at__lt=now - SESSION_RETENTION_SECONDS * 1000
            ).delete()

            session = GameSession.objects.create(
                id=str(uuid.uuid4()),
                member=request.user,
                duration=duration,
                game_mode=game_mode,
                questions=generate_questions(game_mode, duration),
                started_at=now,
            )

        return Response(
            {
                'gameId': session.id,
                'duration': session.duration,
                'gameMode': session.game_mode,
                'questions': session.questions,
            },
            status=status.HTTP_201_CREATED,
        )


class RecordsView(APIView):
    def get_authenticators(self):
        if self.request and self.request.method == 'POST':
            return [BearerTokenAuthentication()]
        return []

    def get_permissions(self):
        if self.request and self.request.method == 'POST':
            return [IsMemberAuthenticated()]
        return [AllowAny()]

    def get_throttles(self):
        if self.request and self.request.method == 'POST':
            return [RecordSaveThrottle()]
        return []

    def get(self, request):
        game_mode = request.query_params.get('gameMode', 'score')
        if game_mode not in GAME_MODES:
            return error(GAME_MODE_MESSAGE, status.HTTP_422_UNPROCESSABLE_ENTITY)

        if game_mode == 'survival':
            # 오래 버틴 순. 생존모드에는 게임 시간 설정이 없어 duration 은 보지 않는다.
            rows = Record.objects.filter(
                game_mode=game_mode,
                survival_time__isnull=False,
            ).order_by('-survival_time', '-correct', 'created_at')
        else:
            raw_duration = request.query_params.get('duration', str(SCORE_DURATION))
            try:
                duration = int(raw_duration)
            except (TypeError, ValueError):
                duration = None

            if duration not in DURATIONS:
                return error(DURATION_MESSAGE, status.HTTP_422_UNPROCESSABLE_ENTITY)

            rows = Record.objects.filter(
                duration=duration,
                game_mode=game_mode,
            ).order_by('-score', '-accuracy', 'average_response_time', 'created_at')

        # 한 사람이 순위표를 독차지하지 않도록 회원별 최고 기록 하나만 올린다.
        # 탈퇴 회원의 기록(member_id 없음)은 닉네임 단위로 묶는다.
        ranking = []
        seen = set()
        for record in rows.iterator(chunk_size=200):
            if record.member_id is not None:
                key = ('member', record.member_id)
            else:
                key = ('withdrawn', record.nickname.casefold())
            if key in seen:
                continue
            seen.add(key)
            ranking.append(record)
            if len(ranking) == RANKING_SIZE:
                break

        return Response(RecordSerializer(ranking, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = RecordSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        game_id = serializer.validated_data['gameId']
        answers = serializer.validated_data['answers']
        member = request.user
        now = now_ms()

        with transaction.atomic():
            session = GameSession.objects.filter(id=game_id, member=member).first()
            if session is None:
                return error(
                    '게임 정보를 찾을 수 없습니다. 이미 저장했거나 새 게임을 시작한 경우입니다.',
                    status.HTTP_404_NOT_FOUND,
                )

            elapsed = (now - session.started_at) / 1000
            survival = session.game_mode == 'survival'

            try:
                if survival:
                    # 게임 길이가 정해져 있지 않아, 채점해서 얼마나 버텼는지부터 구한다.
                    result = grade_survival(session.questions, answers)
                    play_seconds = result.survival_time
                else:
                    result = grade(session.questions, answers, session.duration)
                    play_seconds = session.duration
            except UnfinishedGame:
                return error(UNFINISHED_MESSAGE, status.HTTP_400_BAD_REQUEST)
            except InvalidGameLog:
                return error(INVALID_LOG_MESSAGE, status.HTTP_400_BAD_REQUEST)

            if elapsed < play_seconds - EARLY_SAVE_TOLERANCE_SECONDS:
                # 점수모드: 게임 시간이 다 지나기 전의 요청은 중도 종료다.
                # 생존모드: 게임을 시작한 뒤 실제로 지난 시간보다 오래 버텼다는 기록은 있을 수 없다.
                return error(
                    INVALID_LOG_MESSAGE if survival else UNFINISHED_MESSAGE,
                    status.HTTP_400_BAD_REQUEST,
                )

            if elapsed > COUNTDOWN_SECONDS + play_seconds + SAVE_WINDOW_SECONDS:
                session.delete()
                return error(
                    '기록을 저장할 수 있는 시간이 지났습니다.',
                    status.HTTP_400_BAD_REQUEST,
                )

            # 같은 게임으로 두 번 저장할 수 없도록 게임 정보를 먼저 지운다.
            session.delete()

            record = Record.objects.create(
                id=str(uuid.uuid4()),
                member=member,
                nickname=member.nickname,
                duration=session.duration,
                game_mode=session.game_mode,
                correct=result.correct,
                wrong=result.wrong,
                accuracy=result.accuracy,
                score=result.score,
                average_response_time=result.average_response_time,
                survival_time=result.survival_time,
                created_at=now,
            )

        return Response(RecordSerializer(record).data, status=status.HTTP_201_CREATED)
