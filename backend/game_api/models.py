from django.db import models


class Member(models.Model):
    id = models.AutoField(primary_key=True)
    nickname = models.TextField(unique=True)
    token_hash = models.TextField(unique=True)
    created_at = models.BigIntegerField()

    class Meta:
        managed = False
        db_table = 'members'

    @property
    def is_authenticated(self):
        return True

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
    duration = models.IntegerField()
    difficulty = models.TextField()
    correct = models.IntegerField()
    wrong = models.IntegerField()
    accuracy = models.FloatField()
    score = models.IntegerField()
    average_response_time = models.FloatField()
    created_at = models.BigIntegerField()

    class Meta:
        managed = False
        db_table = 'records'
