from django.contrib.auth.models import User, Group
from django.urls import reverse
from .models import Powiadomienie


def powiadom_laboratorium(formularz):
    """Tworzy powiadomienie dla wszystkich użytkowników w grupie 'Laboratorium'."""
    try:
        grupa = Group.objects.get(name='Laboratorium')
        odbiorcy = User.objects.filter(groups=grupa, is_active=True)
    except Group.DoesNotExist:
        # Brak grupy – powiadom wszystkich aktywnych pracowników oprócz technika
        odbiorcy = User.objects.filter(is_active=True).exclude(pk=formularz.technician_id)

    url = reverse('kotlownia:etap2', args=[formularz.pk])
    tytul = f'Nowy formularz do uzupełnienia – {formularz.data.strftime("%d.%m.%Y")}'
    tresc = (
        f'Dział Techniczny ({formularz.technician}) zakończył Etap 1 formularza '
        f'CD-00001498-2 z dnia {formularz.data.strftime("%d.%m.%Y")} godz. {formularz.godzina.strftime("%H:%M")}. '
        f'Prosimy o uzupełnienie sekcji C – Analiza laboratoryjna wody.'
    )

    for odbiorca in odbiorcy:
        Powiadomienie.objects.create(
            odbiorca=odbiorca,
            tytul=tytul,
            tresc=tresc,
            url=url,
        )
