from .models import Powiadomienie
from .permissions import is_admin


def powiadomienia(request):
    if not request.user.is_authenticated:
        return {}
    nieprzeczytane = Powiadomienie.objects.filter(
        odbiorca=request.user, przeczytane=False
    ).count()
    return {'nieprzeczytane_count': nieprzeczytane, 'is_admin': is_admin(request.user)}
