from django.db import migrations, models


def _nocase_key(nickname):
    # SQLite NOCASE 와 동일하게 ASCII 대문자만 소문자로 접는다.
    return ''.join(
        char.lower() if 'A' <= char <= 'Z' else char
        for char in nickname
    )


def check_case_duplicates(apps, schema_editor):
    """대소문자만 다른 닉네임이 이미 있으면 알기 쉬운 메시지로 중단한다.

    이 검사 없이 진행하면 테이블 재생성 중 UNIQUE 제약 오류로 실패하는데,
    원인을 알아보기 어렵다. 마이그레이션은 트랜잭션으로 묶여 있어
    여기서 중단되어도 DB는 변경되지 않는다.
    """
    Member = apps.get_model('game_api', 'Member')
    groups = {}
    for nickname in Member.objects.values_list('nickname', flat=True):
        groups.setdefault(_nocase_key(nickname), []).append(nickname)

    duplicates = [names for names in groups.values() if len(names) > 1]
    if duplicates:
        listing = '; '.join(' / '.join(names) for names in duplicates)
        raise RuntimeError(
            '대소문자만 다른 닉네임이 있어 마이그레이션을 중단합니다: '
            f'{listing}. 한쪽 회원의 닉네임을 바꾸거나 정리한 뒤 다시 실행하세요.'
        )


class Migration(migrations.Migration):

    dependencies = [
        ('game_api', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(check_case_duplicates, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='member',
            name='nickname',
            field=models.TextField(db_collation='NOCASE', unique=True),
        ),
    ]
