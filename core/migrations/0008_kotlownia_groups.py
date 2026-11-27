from django.db import migrations


def rename_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model('auth', 'User')
    new_group, _ = Group.objects.get_or_create(name='Kotłownia - Mechanicy')
    old_group = Group.objects.filter(name='Kotłownia').first()
    if old_group:
        for user in User.objects.filter(groups=old_group):
            user.groups.add(new_group)
        old_group.delete()
    Group.objects.get_or_create(name='Kotłownia - Elektrycy')


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0007_administrator_group'),
    ]

    operations = [
        migrations.RunPython(rename_groups, migrations.RunPython.noop),
    ]
