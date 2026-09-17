from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kotlownia', '0002_kotlowniaformularz_status_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='KotlowniaUstawienia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email_odbiorca_1', models.EmailField(blank=True, max_length=254, verbose_name='Email odbiorcy 1')),
                ('email_odbiorca_2', models.EmailField(blank=True, max_length=254, verbose_name='Email odbiorcy 2')),
            ],
            options={
                'verbose_name': 'Ustawienia Kotłowni',
                'verbose_name_plural': 'Ustawienia Kotłowni',
            },
        ),
    ]
