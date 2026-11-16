from django.db import migrations


def create_fixed_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    for name in ('Kotłownia', 'Engineering', 'Laboratory'):
        Group.objects.get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0004_userprofile_chip'),
    ]

    operations = [
        migrations.RunPython(create_fixed_groups, migrations.RunPython.noop),
    ]
