import math
import re
import unicodedata

from rest_framework import serializers

from .game_rules import (
    ANSWER_TIME_SLACK_SECONDS,
    DURATIONS,
    GAME_MODES,
    QUESTION_LIMIT_SECONDS,
    SCORE_DURATION,
)
from .models import Record

NICKNAME_MAX_LENGTH = 16
PASSWORD_MIN_LENGTH = 4
PASSWORD_MAX_LENGTH = 64

NICKNAME_LENGTH_MESSAGE = '닉네임은 1~16자로 입력하세요.'
NICKNAME_CHARSET_MESSAGE = (
    '닉네임에는 한글, 영문, 숫자, 밑줄(_), 하이픈(-)만 사용할 수 있습니다. '
    '공백은 단어 사이에 한 칸만 넣을 수 있습니다.'
)
PASSWORD_LENGTH_MESSAGE = (
    f'비밀번호는 {PASSWORD_MIN_LENGTH}~{PASSWORD_MAX_LENGTH}자로 입력하세요.'
)
PASSWORD_REQUIRED_MESSAGE = '비밀번호를 입력하세요.'
ANSWER_LOG_MESSAGE = '답안 기록 형식이 올바르지 않습니다.'
GAME_MODE_MESSAGE = '올바른 게임모드를 선택하세요.'
DURATION_MESSAGE = f'점수모드의 게임 시간은 {SCORE_DURATION}초입니다.'

# 눈에 보이지 않는 문자(제로폭 공백 등)나 닮은꼴 문자로 남의 닉네임을 흉내 내지 못하도록
# 허용 문자를 정해 둔다. 단어 사이 공백은 한 칸만 허용한다.
_NICKNAME_WORD = r'[0-9A-Za-z가-힣ㄱ-ㅎㅏ-ㅣ_-]+'
NICKNAME_PATTERN = re.compile(rf'^{_NICKNAME_WORD}(?: {_NICKNAME_WORD})*$')


def _all_messages(message):
    """필드에서 날 수 있는 모든 검증 오류를 같은 한글 문구로 통일한다."""
    keys = (
        'required', 'null', 'blank', 'invalid', 'max_length', 'min_length',
        'max_value', 'min_value', 'max_string_length', 'invalid_choice',
        'not_a_list', 'empty',
    )
    return {key: message for key in keys}


def normalize_nickname(value):
    """한글 자모 분리형(NFD) 입력을 완성형으로 합치고 앞뒤 공백을 제거한다."""
    return unicodedata.normalize('NFC', value).strip()


class StrictIntField(serializers.IntegerField):
    def to_internal_value(self, data):
        if isinstance(data, bool):
            self.fail('invalid')
        return super().to_internal_value(data)


class StrictFloatField(serializers.FloatField):
    def to_internal_value(self, data):
        if isinstance(data, bool):
            self.fail('invalid')
        val = super().to_internal_value(data)
        if not math.isfinite(val):
            self.fail('invalid')
        return val


class _InputSerializer(serializers.Serializer):
    """요청 본문이 JSON 객체가 아닐 때의 문구도 한글로 통일한다."""

    default_error_messages = {'invalid': '요청 형식이 올바르지 않습니다.'}


class _NicknameField(serializers.CharField):
    def __init__(self, **kwargs):
        kwargs.setdefault('trim_whitespace', False)
        kwargs.setdefault('allow_blank', True)
        kwargs.setdefault('error_messages', _all_messages(NICKNAME_LENGTH_MESSAGE))
        super().__init__(**kwargs)


class RegisterSerializer(_InputSerializer):
    nickname = _NicknameField()
    password = serializers.CharField(
        trim_whitespace=False,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
        error_messages=_all_messages(PASSWORD_LENGTH_MESSAGE),
    )

    def validate_nickname(self, value):
        nickname = normalize_nickname(value)
        if not nickname or len(nickname) > NICKNAME_MAX_LENGTH:
            raise serializers.ValidationError(NICKNAME_LENGTH_MESSAGE)
        if not NICKNAME_PATTERN.fullmatch(nickname):
            raise serializers.ValidationError(NICKNAME_CHARSET_MESSAGE)
        return nickname


class LoginSerializer(_InputSerializer):
    nickname = _NicknameField()
    password = serializers.CharField(
        trim_whitespace=False,
        max_length=PASSWORD_MAX_LENGTH,
        error_messages={
            **_all_messages(PASSWORD_REQUIRED_MESSAGE),
            'max_length': PASSWORD_LENGTH_MESSAGE,
        },
    )

    def validate_nickname(self, value):
        # 문자 종류 제한은 가입 시에만 적용한다. (제한 도입 전에 만든 닉네임도 로그인 가능)
        nickname = normalize_nickname(value)
        if not nickname or len(nickname) > NICKNAME_MAX_LENGTH:
            raise serializers.ValidationError(NICKNAME_LENGTH_MESSAGE)
        return nickname


class WithdrawSerializer(_InputSerializer):
    password = serializers.CharField(
        trim_whitespace=False,
        required=False,
        allow_blank=True,
        max_length=PASSWORD_MAX_LENGTH,
        error_messages=_all_messages(PASSWORD_REQUIRED_MESSAGE),
    )


class GameStartSerializer(_InputSerializer):
    gameMode = serializers.ChoiceField(
        choices=GAME_MODES,
        error_messages=_all_messages(GAME_MODE_MESSAGE),
    )
    # 점수모드는 1분 고정이라 생략할 수 있다. 생존모드에는 정해진 게임 시간이 없어 무시한다.
    duration = StrictIntField(
        required=False,
        error_messages=_all_messages(DURATION_MESSAGE),
    )

    def validate(self, attrs):
        if attrs['gameMode'] == 'survival':
            attrs['duration'] = 0
            return attrs

        duration = attrs.get('duration', SCORE_DURATION)
        if duration not in DURATIONS:
            raise serializers.ValidationError({'duration': DURATION_MESSAGE})

        attrs['duration'] = duration
        return attrs


class AnswerSerializer(serializers.Serializer):
    # None 은 시간 초과
    answer = StrictIntField(
        allow_null=True,
        min_value=0,
        max_value=99,
        error_messages=_all_messages(ANSWER_LOG_MESSAGE),
    )
    time = StrictFloatField(
        min_value=0.0,
        max_value=QUESTION_LIMIT_SECONDS + ANSWER_TIME_SLACK_SECONDS,
        error_messages=_all_messages(ANSWER_LOG_MESSAGE),
    )

    default_error_messages = {'invalid': ANSWER_LOG_MESSAGE}


class RecordSubmitSerializer(_InputSerializer):
    gameId = serializers.CharField(
        max_length=64,
        error_messages=_all_messages('게임 정보가 올바르지 않습니다.'),
    )
    answers = serializers.ListField(
        child=AnswerSerializer(),
        allow_empty=True,
        max_length=500,
        error_messages=_all_messages(ANSWER_LOG_MESSAGE),
    )


class RecordSerializer(serializers.ModelSerializer):
    averageResponseTime = serializers.FloatField(source='average_response_time')
    createdAt = serializers.IntegerField(source='created_at')
    gameMode = serializers.CharField(source='game_mode')
    # 생존모드에서 버틴 시간(초). 점수모드 기록은 null.
    survivalTime = serializers.FloatField(source='survival_time', allow_null=True)
    # 탈퇴한 회원의 기록. 같은 닉네임으로 새로 가입한 회원의 기록과 구분하기 위해 내려준다.
    withdrawn = serializers.SerializerMethodField()

    class Meta:
        model = Record
        fields = (
            'id',
            'nickname',
            'withdrawn',
            'duration',
            'gameMode',
            'correct',
            'wrong',
            'accuracy',
            'score',
            'survivalTime',
            'averageResponseTime',
            'createdAt',
        )

    def get_withdrawn(self, obj):
        return obj.member_id is None
