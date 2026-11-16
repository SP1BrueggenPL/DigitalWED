from django.db import migrations


RENAME_MAP = {
    'Techniczny':   'Engineering',
    'Laboratorium': 'Laboratory',
}


def migrate_user_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    User  = apps.get_model('auth', 'User')

    for old_name, new_name in RENAME_MAP.items():
        try:
            old_group = Group.objects.get(name=old_name)
            new_group, _ = Group.objects.get_or_create(name=new_name)
            for user in User.objects.filter(groups=old_group):
                user.groups.add(new_group)
                user.groups.remove(old_group)
        except Group.DoesNotExist:
            pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0005_fixed_groups'),
    ]

    operations = [
        migrations.RunPython(migrate_user_groups, migrations.RunPython.noop),
    ]
