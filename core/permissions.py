ADMIN_GROUP = 'Administrator'
GROUP_MECHANICY = 'Kotłownia - Mechanicy'
GROUP_ELEKTRYCY = 'Kotłownia - Elektrycy'


def is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name=ADMIN_GROUP).exists()
    )
