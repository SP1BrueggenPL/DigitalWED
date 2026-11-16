from django.db import migrations, models


def copy_recipients(apps, schema_editor):
    Ustawienia = apps.get_model('kotlownia', 'KotlowniaUstawienia')
    for obj in Ustawienia.objects.all():
        obj.odbiorcy = [e for e in (obj.email_odbiorca_1, obj.email_odbiorca_2) if e]
        obj.save()


class Migration(migrations.Migration):
    dependencies = [
        ('kotlownia', '0003_kotlowniaustawienia'),
    ]

    operations = [
        migrations.AddField(
            model_name='kotlowniaustawienia',
            name='odbiorcy',
            field=models.JSONField(blank=True, default=list, verbose_name='Odbiorcy e-mail'),
        ),
        migrations.RunPython(copy_recipients, migrations.RunPython.noop),
        migrations.RemoveField(model_name='kotlowniaustawienia', name='email_odbiorca_1'),
        migrations.RemoveField(model_name='kotlowniaustawienia', name='email_odbiorca_2'),
    ]
