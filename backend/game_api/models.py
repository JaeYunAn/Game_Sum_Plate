from django.db import models


class Member(models.Model):
    id = models.AutoField(primary_key=True)
    # NOCASE: 영문 대소문자만 다른 닉네임(Tester / tester)을 같은 닉네임으로 취급한다.
    nickname = models.TextField(unique=True, db_collation='NOCASE')
    # Django 비밀번호 해시(make_password). 빈 문자열은 비밀번호 도입 전에 가입한 회원으로,
    # 다음 로그인 때 입력한 비밀번호가 설정된다.
    password_hash = models.TextField(default='', blank=True)
    token_hash = models.TextField(unique=True)
    created_at = models.BigIntegerField()

    class Meta:
        db_table = 'members'

    @property
    def is_authenticated(self):
        return True

    @property
    def has_password(self):
        return bool(self.password_hash)

    def __str__(self):
        return f'{self.id}:{self.nickname}'


class Record(models.Model):
    id = models.TextField(primary_key=True)
    member = models.ForeignKey(
        Member,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_column='member_id',
        related_name='records',
    )
    nickname = models.TextField()
    # 점수모드: 게임 시간(초). 생존모드: 정해진 게임 시간이 없으므로 0.
    duration = models.IntegerField()
    game_mode = models.TextField()
    correct = models.IntegerField()
    wrong = models.IntegerField()
    accuracy = models.FloatField()
    # 점수모드: 최종 점수. 생존모드: 게임 중 최고 점수(최종 점수는 항상 0점 이하라 의미가 없다).
    score = models.IntegerField()
    average_response_time = models.FloatField()
    # 생존모드에서 버틴 시간(초). 점수모드 기록은 NULL.
    survival_time = models.FloatField(null=True, blank=True)
    created_at = models.BigIntegerField()

    class Meta:
        db_table = 'records'
        indexes = [
            models.Index(
                fields=[
                    'duration',
                    'game_mode',
                    '-score',
                    '-accuracy',
                    'average_response_time',
                    'created_at',
                ],
                name='idx_records_ranking',
            ),
        ]


class GameSession(models.Model):
    """진행 중인 게임 한 판(점수모드 또는 생존모드).

    서버가 발급한 문제와 시작 시각을 보관해 두었다가, 기록 저장 요청이 오면
    답안 기록을 이 문제들로 채점한다. 저장에 쓰이면 삭제된다(1회용).
    생존모드는 정해진 게임 시간이 없어 duration 이 0 이다.
    """

    id = models.TextField(primary_key=True)
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        db_column='member_id',
        related_name='game_sessions',
    )
    duration = models.IntegerField()
    game_mode = models.TextField()
    questions = models.JSONField()
    started_at = models.BigIntegerField()

    class Meta:
        db_table = 'game_sessions'
