from .models import Powiadomienie


def powiadomienia(request):
    if not request.user.is_authenticated:
        return {}
    nieprzeczytane = Powiadomienie.objects.filter(
        odbiorca=request.user, przeczytane=False
    ).count()
    return {'nieprzeczytane_count': nieprzeczytane}
