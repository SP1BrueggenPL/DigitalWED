import json
import logging
import math

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from core.mail import clean_recipients, send_email
from core.permissions import GROUP_ELEKTRYCY, is_admin

from .models import LIMITS, NAMES, NASTAWY, REASONS, ElektrykUstawienia, KontrolaElektryka

logger = logging.getLogger(__name__)

DOC_NUMBER = 'CD-00001499'


def _has_access(user):
    return user.is_superuser or user.groups.filter(name=GROUP_ELEKTRYCY).exists()


def _no_access(request):
    messages.error(request, f'Brak dostępu do procesu Obsługa kotłowni. Wymagana rola: {GROUP_ELEKTRYCY}.')
    return redirect('dashboard')


def _fmt(n):
    return f'{n:g}'.replace('.', ',')


class Invalid(Exception):
    pass


def _number(data, key, label, maximum=None, integer=False):
    v = data.get(key)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise Invalid(f'{label}: wpisz liczbę.')
    if v < 0:
        raise Invalid(f'{label}: wartość nie może być ujemna.')
    if maximum is not None and v > maximum:
        raise Invalid(f'{label}: wartość za duża (maks. {maximum}).')
    if integer and v != int(v):
        raise Invalid(f'{label}: podaj liczbę całkowitą.')
    return float(v)


def _text(data, key, max_length):
    v = data.get(key, '')
    return v.strip()[:max_length] if isinstance(v, str) else ''


def _clean(data):
    """Walidacja po stronie serwera – te same reguły co w kreatorze w przeglądarce."""
    c = {
        'sol_duzy': _number(data, 'sol_duzy', 'Sól – zbiornik duży', maximum=100),
        'sol_maly': _number(data, 'sol_maly', 'Sól – zbiornik mały', maximum=100),
        'sol_mag': _number(data, 'sol_mag', 'Sól – magazyn', integer=True),
        'p138_zb': _number(data, 'p138_zb', 'Eurocept P138S – zbiornik', maximum=100),
        'p138_mag': _number(data, 'p138_mag', 'Eurocept P138S – magazyn'),
        'd280_zb': _number(data, 'd280_zb', 'Eurocept D280 – zbiornik', maximum=100),
        'd280_mag': _number(data, 'd280_mag', 'Eurocept D280 – magazyn'),
        'cisnienie': _number(data, 'cisnienie', 'Ciśnienie wody miejskiej', maximum=20),
        'licznik_schl': _number(data, 'licznik_schl', 'Licznik wody schładzacza'),
        'licznik_zm': _number(data, 'licznik_zm', 'Licznik stacji zmiękczania'),
    }
    c['zrzut'] = data.get('zrzut')
    if c['zrzut'] not in REASONS:
        raise Invalid('Wybierz przyczynę zrzutu wody.')
    c['zrzut_inna'] = _text(data, 'zrzut_inna', 200) if c['zrzut'] == 'Inna' else ''
    if c['zrzut'] == 'Inna' and not c['zrzut_inna']:
        raise Invalid('Opisz przyczynę zrzutu wody.')
    for key, label in NASTAWY:
        c[key + '_n'] = _text(data, key + '_n', 30)
        if not c[key + '_n']:
            raise Invalid(f'Wpisz wartość nastawy: {label}.')
    c['kolumna'] = data.get('kolumna')
    if c['kolumna'] not in ('1', '2'):
        raise Invalid('Wybierz numer pracującej kolumny.')
    c['czystosc'] = data.get('czystosc')
    if c['czystosc'] not in ('OK', 'Nie'):
        raise Invalid('Zaznacz czystość pomieszczenia.')
    c['uwagi'] = _text(data, 'uwagi', 500)
    if c['czystosc'] == 'Nie' and not c['uwagi']:
        raise Invalid('Opisz, co jest nie tak z czystością pomieszczenia.')
    start = parse_datetime(data.get('start')) if isinstance(data.get('start'), str) else None
    if start is None:
        start = timezone.now()
    elif timezone.is_naive(start):
        start = timezone.make_aware(start)
    c['start'] = start
    return c


def _wyslij_email(obj):
    start = timezone.localtime(obj.start)
    date_str, time_str = start.strftime('%d.%m.%Y'), start.strftime('%H:%M')
    kto = (obj.elektryk.get_full_name() or obj.elektryk.username) if obj.elektryk else '-'
    low = obj.niski_stan()
    uwagi_flag = obj.czystosc == 'Nie'

    if low:
        subject = f'Kotłownia (elektryk) {date_str} – NISKI STAN: ' + ', '.join(NAMES[k]['prod'] for k in low)
    elif uwagi_flag:
        subject = f'Kotłownia (elektryk) {date_str} – uwagi do czystości pomieszczenia'
    else:
        subject = f'Kotłownia (elektryk) {date_str} – kontrola dzienna, stany w normie'

    def mag(key):
        mark = '  <-- PONIŻEJ PROGU' if key in low else ''
        return f'{_fmt(getattr(obj, key))} {NAMES[key]["unit"]} (próg: {LIMITS[key]}){mark}'

    lines = [
        f'Obsługa kotłowni – kontrola dzienna elektryka, formularz {DOC_NUMBER}',
        f'Data: {date_str}  |  Godzina: {time_str}  |  Elektryk: {kto}',
        '',
    ]
    if low:
        lines.append('NISKI STAN MAGAZYNOWY – proszę o zamówienie:')
        for k in low:
            n = NAMES[k]
            lines.append(f'  • {n["prod"]}: {_fmt(getattr(obj, k))} {n["unit"]} (próg zamówienia: {LIMITS[k]} {n["unit"]})')
        lines.append('')
    else:
        lines += ['Stany magazynowe w normie.', '']
    zrzut = f'Inna: {obj.zrzut_inna}' if obj.zrzut == 'Inna' else obj.zrzut
    lines += [
        'Sól zmiękczająca',
        f'  Zbiornik duży: {_fmt(obj.sol_duzy)} %  |  Zbiornik mały: {_fmt(obj.sol_maly)} %',
        f'  Magazyn: {mag("sol_mag")}',
        'Eurocept P138S',
        f'  Zbiornik: {_fmt(obj.p138_zb)} %',
        f'  Magazyn: {mag("p138_mag")}',
        'Eurocept D280',
        f'  Zbiornik: {_fmt(obj.d280_zb)} %',
        f'  Magazyn: {mag("d280_mag")}',
        f'Zrzut wody do kanału – przyczyna: {zrzut}',
        'Kolektor C.O. – nastawy: ' + ', '.join(f'{label}: {getattr(obj, key + "_n")}' for key, label in NASTAWY),
        f'Ciśnienie wody miejskiej: {_fmt(obj.cisnienie)} bar',
        f'Licznik wody schładzacza: {_fmt(obj.licznik_schl)}',
        f'Licznik stacji zmiękczania wody: {_fmt(obj.licznik_zm)}',
        f'Pracująca kolumna: {obj.kolumna}',
        f'Czystość pomieszczenia: {obj.czystosc}' + ('  <-- WYMAGA UWAGI' if uwagi_flag else ''),
        f'Uwagi: {obj.uwagi or "–"}',
        '',
        'Rejestr wpisów: ' + settings.APP_BASE_URL + reverse('elektryk:rejestr'),
    ]
    return send_email(ElektrykUstawienia.get().odbiorcy, subject, '\n'.join(lines))


def _context(request):
    latest = KontrolaElektryka.objects.first()
    return {
        'doc_number': DOC_NUMBER,
        'low_count': len(latest.niski_stan()) if latest else 0,
    }


@login_required
def formularz(request):
    if not _has_access(request.user):
        return _no_access(request)
    config = {
        'limits': LIMITS,
        'submitUrl': reverse('elektryk:submit'),
        'rejestrUrl': reverse('elektryk:rejestr'),
    }
    return render(request, 'elektryk/form.html', {**_context(request), 'config': config})


@login_required
@require_POST
def wyslij(request):
    if not _has_access(request.user):
        return JsonResponse({'ok': False, 'error': 'Brak uprawnień do zapisu.'}, status=403)
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise ValueError
    except ValueError:
        return JsonResponse({'ok': False, 'error': 'Nieprawidłowe dane formularza.'}, status=400)
    try:
        cleaned = _clean(data)
    except Invalid as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)
    obj = KontrolaElektryka.objects.create(elektryk=request.user, **cleaned)
    logger.info('kontrola elektryka saved pk=%s user=%s niski_stan=%s', obj.pk, request.user, obj.niski_stan())
    mail_sent = _wyslij_email(obj)
    return JsonResponse({'ok': True, 'id': obj.pk, 'mailSent': mail_sent, 'entry': obj.as_dict()})


@login_required
def rejestr(request):
    if not _has_access(request.user):
        return _no_access(request)
    entries = [{'id': o.pk, 'd': o.as_dict()}
               for o in KontrolaElektryka.objects.select_related('elektryk')[:1000]]
    config = {
        'limits': LIMITS,
        'entries': entries,
        'isEditor': request.user.is_superuser,
        'deleteUrl': reverse('elektryk:delete', args=[0]),
    }
    return render(request, 'elektryk/rejestr.html', {**_context(request), 'config': config})


@login_required
@require_POST
def usun(request, pk):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Brak uprawnień do usuwania wpisów.'}, status=403)
    obj = get_object_or_404(KontrolaElektryka, pk=pk)
    logger.info('kontrola elektryka deleted pk=%s start=%s by=%s', obj.pk, obj.start, request.user)
    obj.delete()
    return JsonResponse({'ok': True})


@login_required
def ustawienia(request):
    if not is_admin(request.user):
        messages.error(request, 'Brak uprawnień do ustawień.')
        return redirect('dashboard')
    obj = ElektrykUstawienia.get()
    odbiorcy = obj.odbiorcy
    if request.method == 'POST':
        odbiorcy, invalid = clean_recipients(request.POST.getlist('odbiorcy'))
        if invalid:
            messages.error(request, 'Nieprawidłowy adres e-mail: ' + ', '.join(invalid))
        else:
            obj.odbiorcy = odbiorcy
            obj.save()
            messages.success(request, 'Ustawienia zapisane.')
            return redirect('elektryk:ustawienia')
    return render(request, 'kotlownia/ustawienia.html', {
        'odbiorcy': odbiorcy,
        'naglowek': 'Ustawienia – kontrola elektryka',
        'doc_number': DOC_NUMBER,
        'back_url': 'elektryk:rejestr',
        'opis': 'Po każdym wysłaniu formularza kontroli dziennej e-mail z wynikami jest wysyłany automatycznie '
                'do wszystkich poniższych adresów. Niski stan magazynowy jest wyróżniony w temacie wiadomości.',
    })
