from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_klaster'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='chip_number',
            field=models.CharField(blank=True, max_length=20, null=True, unique=True, verbose_name='Numer chip'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='auth_code',
            field=models.CharField(blank=True, max_length=128, verbose_name='Kod autoryzacyjny (hash)'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='auth_code_set',
            field=models.BooleanField(default=False, verbose_name='Kod ustawiony'),
        ),
    ]
