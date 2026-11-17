from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game_api', '0003_member_password_game_session'),
    ]

    operations = [
        migrations.AddField(
            model_name='record',
            name='survival_time',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
