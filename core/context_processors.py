from .models import Powiadomienie
from .permissions import is_admin, GROUP_MECHANICY, GROUP_ELEKTRYCY


def powiadomienia(request):
    if not request.user.is_authenticated:
        return {}
    nieprzeczytane = Powiadomienie.objects.filter(
        odbiorca=request.user, przeczytane=False
    ).count()
    groups = set(request.user.groups.values_list('name', flat=True))
    su = request.user.is_superuser
    return {
        'nieprzeczytane_count': nieprzeczytane,
        'is_admin': is_admin(request.user),
        'nav_mechanicy': su or GROUP_MECHANICY in groups,
        'nav_elektrycy': su or GROUP_ELEKTRYCY in groups,
    }
