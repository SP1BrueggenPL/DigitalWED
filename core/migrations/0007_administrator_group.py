from django.db import migrations


def create_administrator_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model('auth', 'User')
    new_group, _ = Group.objects.get_or_create(name='Administrator')
    old_group = Group.objects.filter(name='Administratorzy').first()
    if old_group:
        for user in User.objects.filter(groups=old_group):
            user.groups.add(new_group)
        old_group.delete()


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0006_migrate_user_groups'),
    ]

    operations = [
        migrations.RunPython(create_administrator_group, migrations.RunPython.noop),
    ]
