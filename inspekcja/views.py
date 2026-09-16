import json
import base64
import os
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.timezone import localdate

from .models import (
    Zmiana, Inspekcja, InspekcjaSekcja, InspekcjaPunkt,
    InspekcjaPodpunkt, InspekcjaWynik, WED_MIEJSCA_CHOICES,
)

logger = logging.getLogger(__name__)


def _is_helpdesk(user):
    return user.groups.filter(name='Helpdesk').exists()

def _is_wed(user):
    return user.is_superuser or user.groups.filter(name__in=['WED', 'Administratorzy']).exists()

def _can_manage(user):
    return user.is_superuser or user.groups.filter(name='Administratorzy').exists()


# ── ZMIANY ──────────────────────────────────────────────────────

@login_required
def zmiana_list(request):
    if not (_is_wed(request.user) or _is_helpdesk(request.user)):
        messages.error(request, 'Brak dostępu.')
        return redirect('dashboard')

    zmiany = Zmiana.objects.prefetch_related('osoby').order_by('-data', 'typ')[:60]
    return render(request, 'inspekcja/zmiana_list.html', {'zmiany': zmiany})


@login_required
def zmiana_create(request):
    if not _is_wed(request.user):
        messages.error(request, 'Brak dostępu.')
        return redirect('dashboard')

    error = None
    if request.method == 'POST':
        data = request.POST.get('data', '').strip()
        typ = request.POST.get('typ', '').strip()
        osoby_ids = request.POST.getlist('osoby')

        if not data or not typ:
            error = 'Wybierz datę i typ zmiany.'
        elif Zmiana.objects.filter(data=data, typ=typ).exists():
            error = 'Zmiana na ten dzień i typ już istnieje.'
        else:
            zmiana = Zmiana.objects.create(data=data, typ=typ, created_by=request.user)
            if osoby_ids:
                zmiana.osoby.set(User.objects.filter(pk__in=osoby_ids))
            messages.success(request, f'Zmiana {zmiana} utworzona.')
            return redirect('inspekcja:zmiana_list')

    wszyscy = User.objects.filter(is_active=True).order_by('last_name', 'first_name')
    typy = Zmiana.TYPY
    return render(request, 'inspekcja/zmiana_form.html', {
        'error': error,
        'typy': typy,
        'wszyscy': wszyscy,
        'today': localdate().isoformat(),
    })


@login_required
def zmiana_edit(request, pk):
    if not _is_wed(request.user):
        messages.error(request, 'Brak dostępu.')
        return redirect('dashboard')

    zmiana = get_object_or_404(Zmiana, pk=pk)
    error = None

    if request.method == 'POST':
        osoby_ids = request.POST.getlist('osoby')
        zmiana.osoby.set(User.objects.filter(pk__in=osoby_ids))
        messages.success(request, f'Zmiana {zmiana} zaktualizowana.')
        return redirect('inspekcja:zmiana_list')

    wszyscy = User.objects.filter(is_active=True).order_by('last_name', 'first_name')
    return render(request, 'inspekcja/zmiana_form.html', {
        'error': error,
        'zmiana': zmiana,
        'typy': Zmiana.TYPY,
        'wszyscy': wszyscy,
        'today': zmiana.data.isoformat(),
    })


@login_required
def zmiana_osoby_api(request, pk):
    """JSON – zwraca listę osób przypisanych do zmiany (do dynamicznego ładowania)."""
    zmiana = get_object_or_404(Zmiana, pk=pk)
    osoby = [
        {'id': u.pk, 'label': u.get_full_name() or u.username}
        for u in zmiana.osoby.filter(is_active=True).order_by('last_name', 'first_name')
    ]
    return JsonResponse({'osoby': osoby})


# ── INSPEKCJE ────────────────────────────────────────────────────

@login_required
def inspekcja_list(request):
    if not (_is_wed(request.user) or _is_helpdesk(request.user)):
        messages.error(request, 'Brak dostępu.')
        return redirect('dashboard')

    qs = Inspekcja.objects.select_related('zmiana').prefetch_related('osoby_kontrolujace')

    # Helpdesk widzi wszystkie (w tym ukryte); WED widzi tylko nieukryte
    if not (_is_helpdesk(request.user) or request.user.is_superuser):
        qs = qs.filter(ukryta=False)

    inspekcje = qs.order_by('-created_at')
    return render(request, 'inspekcja/list.html', {
        'inspekcje': inspekcje,
        'is_helpdesk': _is_helpdesk(request.user),
    })


@login_required
def inspekcja_create(request):
    if not _is_wed(request.user):
        messages.error(request, 'Brak dostępu.')
        return redirect('dashboard')

    error = None
    zmiany = Zmiana.objects.prefetch_related('osoby').order_by('-data', 'typ')[:30]

    if request.method == 'POST':
        zmiana_pk = request.POST.get('zmiana')
        miejsce = request.POST.get('miejsce', '').strip()
        osoby_ids = request.POST.getlist('osoby')

        if not zmiana_pk:
            error = 'Wybierz zmianę.'
        elif not miejsce:
            error = 'Wybierz miejsce inspekcji.'
        elif not osoby_ids:
            error = 'Wybierz co najmniej jedną osobę kontrolującą.'
        else:
            zmiana = get_object_or_404(Zmiana, pk=zmiana_pk)
            ins = Inspekcja.objects.create(
                typ='wed',
                zmiana=zmiana,
                miejsce=miejsce,
                created_by=request.user,
            )
            ins.osoby_kontrolujace.set(User.objects.filter(pk__in=osoby_ids))

            # Utwórz puste wpisy wyników dla każdego punktu
            sekcje = InspekcjaSekcja.objects.filter(
                typ_inspekcji='wed'
            ).prefetch_related('punkty__podpunkty')
            for sekcja in sekcje:
                for punkt in sekcja.punkty.all():
                    podpunkty = list(punkt.podpunkty.all())
                    if podpunkty:
                        for podpunkt in podpunkty:
                            InspekcjaWynik.objects.get_or_create(
                                inspekcja=ins, sekcja=sekcja,
                                punkt=punkt, podpunkt=podpunkt,
                            )
                    else:
                        InspekcjaWynik.objects.get_or_create(
                            inspekcja=ins, sekcja=sekcja,
                            punkt=punkt, podpunkt=None,
                        )

            messages.success(request, 'Inspekcja WED utworzona.')
            return redirect('inspekcja:detail', pk=ins.pk)

    miejsca = WED_MIEJSCA_CHOICES
    return render(request, 'inspekcja/create.html', {
        'error': error,
        'zmiany': zmiany,
        'miejsca': miejsca,
    })


@login_required
def inspekcja_detail(request, pk):
    if not (_is_wed(request.user) or _is_helpdesk(request.user)):
        messages.error(request, 'Brak dostępu.')
        return redirect('dashboard')

    ins = get_object_or_404(Inspekcja, pk=pk)

    if request.method == 'POST' and ins.status == 'w_toku' and _is_wed(request.user):
        # Zapis wyników
        for wynik in ins.wyniki.all():
            key = f'wynik_{wynik.pk}'
            uwagi_key = f'uwagi_{wynik.pk}'
            wynik.wynik = request.POST.get(key, wynik.wynik)
            wynik.uwagi = request.POST.get(uwagi_key, wynik.uwagi)
            wynik.save(update_fields=['wynik', 'uwagi'])

        if request.POST.get('zakoncz'):
            ins.status = 'zakonczona'
            ins.save(update_fields=['status'])
            messages.success(request, 'Inspekcja zakończona.')
            return redirect('inspekcja:list')

        messages.success(request, 'Wyniki zapisane.')
        return redirect('inspekcja:detail', pk=ins.pk)

    # Grupowanie wyników wg sekcji
    sekcje_data = []
    for sekcja in InspekcjaSekcja.objects.filter(typ_inspekcji='wed').prefetch_related('punkty__podpunkty'):
        punkty_data = []
        for punkt in sekcja.punkty.all():
            podpunkty = list(punkt.podpunkty.all())
            if podpunkty:
                pod_data = []
                for pod in podpunkty:
                    wynik = ins.wyniki.filter(punkt=punkt, podpunkt=pod).first()
                    pod_data.append({'podpunkt': pod, 'wynik': wynik})
                punkty_data.append({'punkt': punkt, 'wynik': None, 'podpunkty': pod_data})
            else:
                wynik = ins.wyniki.filter(punkt=punkt, podpunkt=None).first()
                punkty_data.append({'punkt': punkt, 'wynik': wynik, 'podpunkty': []})
        sekcje_data.append({'sekcja': sekcja, 'punkty': punkty_data})

    return render(request, 'inspekcja/detail.html', {
        'ins': ins,
        'sekcje_data': sekcje_data,
        'is_helpdesk': _is_helpdesk(request.user),
        'is_wed': _is_wed(request.user),
        'wynik_choices': InspekcjaWynik.WYNIKI,
        'miejsca_dict': dict(WED_MIEJSCA_CHOICES),
    })


@login_required
@require_POST
def inspekcja_toggle_ukryj(request, pk):
    if not _is_helpdesk(request.user):
        return JsonResponse({'error': 'Brak uprawnień.'}, status=403)

    ins = get_object_or_404(Inspekcja, pk=pk)
    ins.ukryta = not ins.ukryta
    ins.save(update_fields=['ukryta'])
    return JsonResponse({'ukryta': ins.ukryta})


# ── AI – ANALIZA ZDJĘCIA ─────────────────────────────────────────

@login_required
@require_POST
def ai_analizuj_zdjecie(request, wynik_pk):
    """Analizuje przesłane zdjęcie w kontekście sekcji/punktu/podpunktu."""
    wynik = get_object_or_404(InspekcjaWynik, pk=wynik_pk)

    if not _is_wed(request.user):
        return JsonResponse({'error': 'Brak uprawnień.'}, status=403)

    zdjecie_file = request.FILES.get('zdjecie')
    if not zdjecie_file:
        return JsonResponse({'error': 'Brak zdjęcia.'}, status=400)

    # Zapisz zdjęcie
    wynik.zdjecie = zdjecie_file
    wynik.save(update_fields=['zdjecie'])

    # Zbuduj kontekst dla promptu
    sekcja_nazwa = wynik.sekcja.nazwa
    punkt_tresc = wynik.punkt.tresc if wynik.punkt else '—'
    podpunkt_tresc = wynik.podpunkt.tresc if wynik.podpunkt else None

    # Pobierz wszystkie dostępne sekcje (dla sugestii)
    wszystkie_sekcje = list(
        InspekcjaSekcja.objects.filter(typ_inspekcji='wed').values_list('nazwa', flat=True)
    )

    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        wynik.analiza_ai = 'Brak klucza API – analiza niedostępna.'
        wynik.save(update_fields=['analiza_ai'])
        return JsonResponse({
            'analiza': wynik.analiza_ai,
            'pasuje': None,
            'sugestia': '',
        })

    try:
        import anthropic

        # Odczytaj zdjęcie jako base64
        wynik.zdjecie.open('rb')
        img_data = base64.standard_b64encode(wynik.zdjecie.read()).decode('utf-8')
        wynik.zdjecie.close()

        # Ustal media type
        name = wynik.zdjecie.name.lower()
        if name.endswith('.png'):
            media_type = 'image/png'
        elif name.endswith('.gif'):
            media_type = 'image/gif'
        elif name.endswith('.webp'):
            media_type = 'image/webp'
        else:
            media_type = 'image/jpeg'

        kontekst_podpunkt = (
            f"\n- Podpunkt: {podpunkt_tresc}" if podpunkt_tresc else ""
        )
        sekcje_lista = '\n'.join(f'  • {s}' for s in wszystkie_sekcje)

        prompt = f"""Jesteś ekspertem ds. inspekcji przemysłowych w firmie H. & J. Brüggen KG (Dział WED).

Analizujesz zdjęcie przesłane przez inspektora w ramach inspekcji WED.

Kontekst przypisania zdjęcia:
- Sekcja: {sekcja_nazwa}
- Punkt: {punkt_tresc}{kontekst_podpunkt}

Dostępne sekcje inspekcji WED:
{sekcje_lista}

Twoje zadania:
1. Opisz krótko (max 80 słów) co widać na zdjęciu.
2. Oceń czy zdjęcie pasuje do podanego kontekstu (sekcja/punkt/podpunkt).
3. Jeśli NIE pasuje – wskaż do której sekcji powinno być przypisane.

Odpowiedz WYŁĄCZNIE w JSON (bez markdown, bez ```):
{{
  "opis": "krótki opis zdjęcia",
  "pasuje": true,
  "uzasadnienie": "dlaczego pasuje lub nie pasuje",
  "sugestia_sekcji": null
}}

Jeśli zdjęcie nie pasuje, ustaw "pasuje": false i "sugestia_sekcji": "nazwa odpowiedniej sekcji".
Jeśli pasuje, ustaw "pasuje": true i "sugestia_sekcji": null."""

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model='claude-haiku-4-5-20251001',
            max_tokens=512,
            messages=[{
                'role': 'user',
                'content': [
                    {
                        'type': 'image',
                        'source': {
                            'type': 'base64',
                            'media_type': media_type,
                            'data': img_data,
                        },
                    },
                    {'type': 'text', 'text': prompt},
                ],
            }],
        )

        raw = response.content[0].text.strip()
        data = json.loads(raw)

        wynik.analiza_ai = data.get('opis', '')
        wynik.ai_pasuje = data.get('pasuje', True)
        wynik.ai_sugestia = data.get('sugestia_sekcji') or ''
        wynik.save(update_fields=['analiza_ai', 'ai_pasuje', 'ai_sugestia'])

        return JsonResponse({
            'analiza': wynik.analiza_ai,
            'pasuje': wynik.ai_pasuje,
            'uzasadnienie': data.get('uzasadnienie', ''),
            'sugestia': wynik.ai_sugestia,
        })

    except Exception as exc:
        logger.exception('AI analiza zdjęcia – błąd')
        wynik.analiza_ai = f'Błąd analizy: {exc}'
        wynik.save(update_fields=['analiza_ai'])
        return JsonResponse({'error': str(exc)}, status=500)
