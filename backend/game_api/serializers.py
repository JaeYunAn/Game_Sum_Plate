import math
from rest_framework import serializers

from .models import Record


class NicknameSerializer(serializers.Serializer):
    nickname = serializers.CharField(
        trim_whitespace=False,
        allow_blank=True,
        error_messages={
            'required': '닉네임은 1~16자로 입력하세요.',
            'null': '닉네임은 1~16자로 입력하세요.',
            'blank': '닉네임은 1~16자로 입력하세요.',
            'invalid': '닉네임은 1~16자로 입력하세요.',
        },
    )

    def validate_nickname(self, value):
        if not isinstance(value, str):
            raise serializers.ValidationError('닉네임은 1~16자로 입력하세요.')
        stripped = value.strip()
        if not stripped or len(stripped) > 16:
            raise serializers.ValidationError('닉네임은 1~16자로 입력하세요.')
        return stripped


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


class RecordCreateSerializer(serializers.Serializer):
    duration = StrictIntField()
    gameMode = serializers.ChoiceField(choices=('score', 'survival'))
    correct = StrictIntField(min_value=0)
    wrong = StrictIntField(min_value=0)
    accuracy = StrictFloatField(min_value=0.0, max_value=100.0)
    score = StrictIntField()
    averageResponseTime = StrictFloatField(min_value=0.0)

    def validate_duration(self, value):
        if value not in (30, 60):
            raise serializers.ValidationError('게임 시간은 30초 또는 60초여야 합니다.')
        return value


class RecordSerializer(serializers.ModelSerializer):
    averageResponseTime = serializers.FloatField(source='average_response_time')
    createdAt = serializers.IntegerField(source='created_at')
    gameMode = serializers.CharField(source='game_mode')

    class Meta:
        model = Record
        fields = (
            'id',
            'nickname',
            'duration',
            'gameMode',
            'correct',
            'wrong',
            'accuracy',
            'score',
            'averageResponseTime',
            'createdAt',
        )
