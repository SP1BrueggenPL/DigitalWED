import logging
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponse
from .models import KotlowniaFormularz, KotlowniaUstawienia
from .forms import EtapTechnicznyForm, EtapLaboratoriumForm
from core.notifications import powiadom_laboratorium
from core.models import Powiadomienie
from core.permissions import is_admin
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

B_ROWS = [
    (1,  'Wskaźnik poziomu wody'),
    (2,  'Regulator poziomu wody'),
    (3,  'Regulator temperatury lub ciśnienia'),
    (4,  'Urządzenie do opróżniania lub odsalania kotła'),
    (5,  'Aparatura kontroli obecności zanieczyszczeń stałych w wodzie kotłowej'),
    (6,  'Regulacja palnika (elementy wykonawcze do sterowania powietrzem lub paliwem)'),
    (7,  'Wentylator powietrza, spalania, wentylator zapłonowy, wentylator powietrza chłodzącego'),
    (8,  'Awaryjne urządzenie odcinające'),
    (9,  'Zapłon'),
    (10, 'Wentylacja'),
    (11, 'Kontrola płomienia'),
    (12, 'Ocena jakości spalania'),
    (13, 'Stan licznika: całkowita liczba godzin pracy'),
    (14, 'Stan licznika: całkowita liczba godzin pracy palnika'),
    (15, 'Stan licznika: całkowita liczba impulsów rozruchowych palnika'),
]

# B rows 5-11 use OK/NIE OK; 1-4 and 12-15 use numeric/text value
B_OK_NIE_OK = set(range(5, 12))

# ── Tolerance rules for Section C ─────────────────────────────────────────────

_TOLERANCES = {
    'wz_ph':          lambda v: v > 9,
    'wz_wapnioce_dh': lambda v: v < Decimal('0.05'),
    'wz_tlen_mg':     lambda v: v < Decimal('0.1'),
    'wz_przewodnosc': lambda v: v < 500,
    'wz_temperatura': lambda v: Decimal('23') <= v <= Decimal('27'),
    'wz_wyglad':      lambda v: v == 'ok',
    'k_wapnioce_dh':  lambda v: v < Decimal('0.05'),
    'k_przewodnosc':  lambda v: v < 500,
    'wk_ph':          lambda v: Decimal('10.5') <= v <= 12,
    'wk_wapnioce_dh': lambda v: v < Decimal('0.05'),
    'wk_przewodnosc': lambda v: 30 <= v <= 8000,
    'wk_wyglad':      lambda v: v == 'ok',
    'wu_wapnioce_dh': lambda v: v < Decimal('0.1'),
}

_ODCHYLKI_LABELS = {
    'wz_ph':          'Woda zasilająca – pH (25°C)',
    'wz_wapnioce_dh': 'Woda zasilająca – Wapniowce [°dH]',
    'wz_tlen_mg':     'Woda zasilająca – Tlen O₂ [mg/l]',
    'wz_przewodnosc': 'Woda zasilająca – Przewodność [µS/cm]',
    'wz_temperatura': 'Woda zasilająca – Temperatura [°C]',
    'wz_wyglad':      'Woda zasilająca – Wygląd',
    'k_wapnioce_dh':  'Kondensat – Wapniowce [°dH]',
    'k_przewodnosc':  'Kondensat – Przewodność [µS/cm]',
    'wk_ph':          'Woda kotłowa – pH (25°C)',
    'wk_wapnioce_dh': 'Woda kotłowa – Wapniowce [°dH]',
    'wk_przewodnosc': 'Woda kotłowa – Przewodność [µS/cm]',
    'wk_wyglad':      'Woda kotłowa – Wygląd',
    'wu_wapnioce_dh': 'Woda po uzdatnianiu – Wapniowce [°dH]',
}

_TOLERANCE_STRS = {
    'wz_ph':          '> 9',
    'wz_wapnioce_dh': '< 0,05',
    'wz_tlen_mg':     '< 0,1',
    'wz_przewodnosc': '< 500',
    'wz_temperatura': '≈ 25 °C (±2)',
    'wz_wyglad':      'Ok',
    'k_wapnioce_dh':  '< 0,05',
    'k_przewodnosc':  '< 500',
    'wk_ph':          '10,5 – 12',
    'wk_wapnioce_dh': '< 0,05',
    'wk_przewodnosc': '30 – 8000',
    'wk_wyglad':      'Ok',
    'wu_wapnioce_dh': '< 0,1',
}


def sprawdz_odchylki(obj):
    """Returns (all_ok, status_per_field dict, deviations list)."""
    status = {}
    deviations = []
    for field, check_fn in _TOLERANCES.items():
        val = getattr(obj, field)
        if val is None or val == '':
            status[field] = None
            continue
        try:
            ok = bool(check_fn(val))
        except Exception:
            status[field] = None
            continue
        status[field] = ok
        if not ok:
            deviations.append({
                'label': _ODCHYLKI_LABELS[field],
                'value': str(val),
                'tolerance': _TOLERANCE_STRS[field],
            })
    all_ok = all(v is not False for v in status.values())
    return all_ok, status, deviations


def _wyslij_email(subject, body, attachments=None):
    import os
    connection_string = os.environ.get('AZURE_CONNECTION_STRING', '')
    sender_address    = os.environ.get('AZURE_SENDER_ADDRESS', '')
    if not connection_string or not sender_address:
        logger.warning('Kotlownia email: brak AZURE_CONNECTION_STRING lub AZURE_SENDER_ADDRESS')
        return
    recipients = list(KotlowniaUstawienia.get().odbiorcy)
    if not recipients:
        logger.warning('Kotlownia email: brak odbiorców w ustawieniach')
        return
    try:
        from azure.communication.email import EmailClient
        client = EmailClient.from_connection_string(connection_string)
        message = {
            'senderAddress': sender_address,
            'recipients': {'to': [{'address': addr} for addr in recipients]},
            'content': {'subject': subject, 'plainText': body},
        }
        if attachments:
            message['attachments'] = attachments
        client.begin_send(message).result()
        logger.info('Kotlownia email sent: %s (%d odbiorców)', subject, len(recipients))
    except Exception as exc:
        logger.error('Kotlownia email send failed: %s', exc)


def _wyslij_email_zapowiedz_probek(obj):
    date_str  = obj.data.strftime('%d.%m.%Y')
    time_str  = obj.godzina.strftime('%H:%M')
    tech_name = (obj.technician.get_full_name() or obj.technician.username) if obj.technician else '-'
    body = '\n'.join([
        'Nadzór nad kotłownią – Formularz CD-00001498-4',
        '',
        f'Dział Techniczny zatwierdził Etap 1 wpisu z dnia {date_str}, godz. {time_str} (technik: {tech_name}).',
        'Wkrótce do Laboratorium zostaną dostarczone próbki wody do tego wpisu.',
        '',
        'Po wykonaniu analiz prosimy o uzupełnienie Etapu 2 w aplikacji:',
        settings.APP_BASE_URL + reverse('kotlownia:etap2', args=[obj.pk]),
        '',
        f'Aplikacja: {settings.APP_BASE_URL}',
    ])
    _wyslij_email(f'Kotłownia {date_str} {time_str} – próbki w drodze do Laboratorium', body)


def _wyslij_email_kotlownia(obj, all_ok, deviations):
    import base64
    from django.utils.timezone import localtime, now as dj_now

    date_str  = obj.data.strftime('%d.%m.%Y')  if obj.data       else '-'
    time_str  = obj.lab_godzina.strftime('%H:%M') if obj.lab_godzina else '-'
    tech_name = obj.technician.get_full_name()  if obj.technician else '-'
    lab_name  = obj.laborant.get_full_name()    if obj.laborant   else '-'

    if all_ok:
        subject = f'Kotłownia {date_str} – Wyniki w normie'
        status_line = 'WYNIKI W NORMIE – wszystkie parametry mieszczą się w granicach tolerancji.'
    else:
        subject = f'Kotłownia {date_str} – ODCHYŁKI od normy'
        status_line = 'ODCHYŁKI OD NORMY – co najmniej jeden parametr przekroczył granicę tolerancji.'

    lines = [
        'Nadzór nad kotłownią – Formularz CD-00001498-4',
        f'Data: {date_str}  |  Godzina analiz: {time_str}',
        f'Technik: {tech_name}  |  Laborant: {lab_name}',
        '',
        status_line,
        '',
    ]

    if deviations:
        lines.append('Wykryte odchyłki:')
        for d in deviations:
            lines.append(f'  • {d["label"]}: {d["value"]}  (norma: {d["tolerance"]})')

    body = '\n'.join(lines)

    # Generate PDF attachment
    attachments = []
    try:
        from .pdf_generator import generate_formularz_pdf
        _, odchylki_status, _ = sprawdz_odchylki(obj)
        now_str = localtime(dj_now()).strftime('%d.%m.%Y %H:%M')
        b_rows = _build_b_rows(obj)
        pdf_bytes = generate_formularz_pdf(obj, b_rows, odchylki_status, now_str)
        pdf_filename = f'CD-00001498-4_{obj.data.strftime("%Y-%m-%d")}.pdf' if obj.data else 'CD-00001498-4.pdf'
        attachments = [{
            'name': pdf_filename,
            'contentType': 'application/pdf',
            'contentInBase64': base64.b64encode(pdf_bytes).decode('utf-8'),
        }]
    except Exception as exc:
        logger.error('Kotlownia email: nie udało się wygenerować PDF: %s', exc)

    _wyslij_email(subject, body, attachments)


# ── Access helpers ─────────────────────────────────────────────────────────────

def _has_process_access(user):
    return user.is_superuser or user.groups.filter(name='Kotłownia').exists()


def _is_lab(user):
    return user.is_superuser or user.groups.filter(name='Laboratory').exists()


def _is_tech(user):
    return user.is_superuser or user.groups.filter(name='Engineering').exists()


def _can_edit_etap1(user):
    if user.is_superuser:
        return True
    in_eng = user.groups.filter(name='Engineering').exists()
    in_lab = user.groups.filter(name='Laboratory').exists()
    return in_eng or (not in_lab)


def _can_edit_etap2(user):
    return user.is_superuser or user.groups.filter(name='Laboratory').exists()


def _build_b_rows(obj):
    rows = []
    for lp, label in B_ROWS:
        wartosc = getattr(obj, f'b{lp}_wartosc')
        rows.append({
            'lp': lp,
            'label': label,
            'wartosc': wartosc,
            'uwagi': getattr(obj, f'b{lp}_uwagi'),
            'is_ok_nie_ok': lp in B_OK_NIE_OK,
        })
    return rows


# ── Views ──────────────────────────────────────────────────────────────────────

@login_required
def formularz_list(request):
    logger.info('list view user=%s auth=%s session=%s',
                request.user, request.user.is_authenticated, request.session.session_key)
    if not _has_process_access(request.user):
        logger.warning('list NO_PROCESS_ACCESS user=%s groups=%s',
                       request.user, list(request.user.groups.values_list('name', flat=True)))
        messages.error(request, 'Brak dostępu do procesu Nadzór kotłowni. Wymagana rola: Kotłownia.')
        return redirect('dashboard')

    if _is_lab(request.user) and not _is_tech(request.user) and not request.user.is_superuser:
        pending = KotlowniaFormularz.objects.filter(status=KotlowniaFormularz.STATUS_LABORATORIUM)
        done = KotlowniaFormularz.objects.filter(
            status=KotlowniaFormularz.STATUS_ZAKONCZONY,
            laborant=request.user,
        )
        for f in done:
            f.odchylki_ok = sprawdz_odchylki(f)[0]
        return render(request, 'kotlownia/list_lab.html', {
            'pending': pending, 'done': done,
        })
    formularze = KotlowniaFormularz.objects.all().order_by('-created_at')
    for f in formularze:
        if f.status == KotlowniaFormularz.STATUS_ZAKONCZONY:
            f.odchylki_ok = sprawdz_odchylki(f)[0]
        else:
            f.odchylki_ok = None
    return render(request, 'kotlownia/list.html', {
        'formularze': formularze,
        'is_superuser': request.user.is_superuser,
    })


@login_required
def etap_techniczny(request, pk=None):
    obj = get_object_or_404(KotlowniaFormularz, pk=pk) if pk else None

    if not _has_process_access(request.user):
        messages.error(request, 'Brak dostępu do procesu Nadzór kotłowni.')
        return redirect('dashboard')

    if obj and obj.status == KotlowniaFormularz.STATUS_ZAKONCZONY:
        messages.error(request, 'Formularz jest zakończony i nie może być edytowany.')
        return redirect('kotlownia:detail', pk=obj.pk)

    if not _can_edit_etap1(request.user):
        messages.error(request, 'Brak uprawnień do wypełniania Etapu 1.')
        return redirect('kotlownia:list')

    if request.method == 'POST':
        form = EtapTechnicznyForm(request.POST, instance=obj)
        if form.is_valid():
            saved = form.save(commit=False)
            if not pk:
                saved.technician = request.user
            sig = request.POST.get('podpis_techniczny_data', '').strip()
            if sig and not sig.endswith(','):
                saved.podpis_techniczny = sig
            already_accepted = bool(obj) and obj.status == KotlowniaFormularz.STATUS_LABORATORIUM
            if request.POST.get('action') == 'draft' and not already_accepted:
                saved.status = KotlowniaFormularz.STATUS_TECHNICZNY
                saved.save()
                messages.success(request, 'Wersja robocza Etapu 1 zapisana.')
                return redirect('kotlownia:etap1', pk=saved.pk)
            saved.status = KotlowniaFormularz.STATUS_LABORATORIUM
            saved.save()
            if already_accepted:
                messages.success(request, 'Zmiany w Etapie 1 zapisane.')
            else:
                logger.info('etap1 accepted pk=%s technician=%s', saved.pk, saved.technician_id)
                powiadom_laboratorium(saved)
                _wyslij_email_zapowiedz_probek(saved)
                messages.success(request, 'Etap 1 zatwierdzony. Powiadomienie wysłane do Laboratorium.')
            return redirect('kotlownia:detail', pk=saved.pk)
    else:
        form = EtapTechnicznyForm(instance=obj)

    return render(request, 'kotlownia/etap1.html', {
        'form': form, 'obj': obj,
        'title': 'Etap 1 – Dział Techniczny',
        'b_rows': B_ROWS,
        'B_OK_NIE_OK': B_OK_NIE_OK,
    })


def etap_laboratorium(request, pk):
    if not request.user.is_authenticated:
        logger.warning('etap2 UNAUTHENTICATED pk=%s method=%s session=%s',
                       pk, request.method, request.session.session_key)
        from django.contrib.auth.views import redirect_to_login
        return redirect_to_login(request.get_full_path())
    obj = get_object_or_404(KotlowniaFormularz, pk=pk)

    if not _has_process_access(request.user):
        messages.error(request, 'Brak dostępu do procesu Nadzór kotłowni.')
        return redirect('dashboard')

    if obj.status == KotlowniaFormularz.STATUS_ZAKONCZONY:
        messages.error(request, 'Formularz jest zakończony i nie może być edytowany.')
        return redirect('kotlownia:detail', pk=obj.pk)

    if obj.status == KotlowniaFormularz.STATUS_TECHNICZNY:
        messages.error(request, 'Etap 1 nie został jeszcze zatwierdzony przez Dział Techniczny.')
        return redirect('kotlownia:detail', pk=obj.pk)

    if not _can_edit_etap2(request.user):
        messages.error(request, 'Brak uprawnień do wypełniania Etapu 2 – wymagana rola Laboratorium.')
        return redirect('kotlownia:detail', pk=pk)

    Powiadomienie.objects.filter(
        odbiorca=request.user,
        url=reverse('kotlownia:etap2', args=[pk]),
        przeczytane=False,
    ).update(przeczytane=True)

    if request.method == 'POST':
        try:
            form = EtapLaboratoriumForm(request.POST, instance=obj)
            action = request.POST.get('action', 'finalize')
            if form.is_valid():
                saved = form.save(commit=False)
                saved.laborant = request.user
                sig = request.POST.get('podpis_laboratorium_data', '').strip()
                if sig and not sig.endswith(','):
                    saved.podpis_laboratorium = sig
                if action == 'draft':
                    saved.status = KotlowniaFormularz.STATUS_LABORATORIUM
                    saved.save()
                    messages.success(request, 'Wersja robocza zapisana.')
                    return redirect('kotlownia:etap2', pk=saved.pk)
                saved.status = KotlowniaFormularz.STATUS_ZAKONCZONY
                saved.save()
                logger.info('etap2 saved pk=%s laborant=%s technician=%s',
                            saved.pk, saved.laborant_id, saved.technician_id)
                all_ok, _status, deviations = sprawdz_odchylki(saved)
                _wyslij_email_kotlownia(saved, all_ok, deviations)
                messages.success(request, 'Etap 2 zapisany. Formularz zakończony.')
                return redirect('kotlownia:list')
            else:
                logger.warning('etap2 form invalid pk=%s errors=%s', pk, form.errors)
        except Exception:
            logger.exception('etap2 unhandled exception pk=%s user=%s', pk, request.user)
            raise
    else:
        form = EtapLaboratoriumForm(instance=obj)

    _, odchylki, _ = sprawdz_odchylki(obj)

    return render(request, 'kotlownia/etap2.html', {
        'form': form, 'obj': obj,
        'title': 'Etap 2 – Laboratorium',
        'odchylki': odchylki,
    })


@login_required
def formularz_detail(request, pk):
    logger.info('detail view pk=%s user=%s auth=%s', pk, request.user, request.user.is_authenticated)
    obj = get_object_or_404(KotlowniaFormularz, pk=pk)
    b_rows = _build_b_rows(obj)
    _, odchylki, _ = sprawdz_odchylki(obj)
    return render(request, 'kotlownia/detail.html', {
        'obj': obj,
        'b_rows': b_rows,
        'odchylki': odchylki,
        'can_etap1': _can_edit_etap1(request.user),
        'can_etap2': _can_edit_etap2(request.user),
    })


@login_required
def formularz_print(request, pk):
    obj = get_object_or_404(KotlowniaFormularz, pk=pk)
    b_rows = _build_b_rows(obj)
    return render(request, 'kotlownia/print.html', {'obj': obj, 'b_rows': b_rows})


@login_required
def formularz_pdf(request, pk):
    from django.utils.timezone import localtime, now
    from .pdf_generator import generate_formularz_pdf

    obj = get_object_or_404(KotlowniaFormularz, pk=pk)
    b_rows = _build_b_rows(obj)
    _, odchylki, _ = sprawdz_odchylki(obj)
    now_str = localtime(now()).strftime('%d.%m.%Y %H:%M')
    pdf_bytes = generate_formularz_pdf(obj, b_rows, odchylki, now_str)

    filename = f'CD-00001498-4_{obj.data.strftime("%Y-%m-%d")}.pdf'
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def powiadomienia_list(request):
    pows = Powiadomienie.objects.filter(odbiorca=request.user)
    pows.filter(przeczytane=False).update(przeczytane=True)
    return render(request, 'core/powiadomienia.html', {'powiadomienia': pows})


@login_required
def dashboard(request):
    import json
    from datetime import date, timedelta

    if not _has_process_access(request.user):
        messages.error(request, 'Brak dostępu.')
        return redirect('dashboard')

    # --- okres ---
    preset = request.GET.get('preset', '30')
    date_from_str = request.GET.get('date_from', '')
    date_to_str   = request.GET.get('date_to', '')
    today = date.today()

    if date_from_str and date_to_str:
        try:
            from datetime import datetime
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
            date_to   = datetime.strptime(date_to_str,   '%Y-%m-%d').date()
            preset = 'custom'
        except ValueError:
            date_from = today - timedelta(days=30)
            date_to   = today
    elif preset == '7':
        date_from = today - timedelta(days=7)
        date_to   = today
    elif preset == '90':
        date_from = today - timedelta(days=90)
        date_to   = today
    elif preset == '365':
        date_from = today - timedelta(days=365)
        date_to   = today
    else:
        preset = '30'
        date_from = today - timedelta(days=30)
        date_to   = today

    qs = KotlowniaFormularz.objects.filter(
        status=KotlowniaFormularz.STATUS_ZAKONCZONY,
        data__gte=date_from,
        data__lte=date_to,
    ).order_by('data', 'godzina')

    total = qs.count()
    ok_count  = 0
    nok_count = 0
    deviations_list = []

    # dane do wykresów
    chart_labels = []
    chart_data = {
        'wz_ph':          [],
        'wz_wapnioce_dh': [],
        'wz_tlen_mg':     [],
        'wz_przewodnosc': [],
        'wk_ph':          [],
        'wk_przewodnosc': [],
    }
    chart_tolerances = {
        'wz_ph':          {'min': None, 'max': 9,   'label': 'Woda zas. pH',       'unit': ''},
        'wz_wapnioce_dh': {'min': None, 'max': 0.05,'label': 'Woda zas. Wapniowce','unit': '°dH'},
        'wz_tlen_mg':     {'min': None, 'max': 0.1, 'label': 'Woda zas. Tlen O₂',  'unit': 'mg/l'},
        'wz_przewodnosc': {'min': None, 'max': 500, 'label': 'Woda zas. Przewodn.','unit': 'µS/cm'},
        'wk_ph':          {'min': 10.5, 'max': 12,  'label': 'Woda kot. pH',        'unit': ''},
        'wk_przewodnosc': {'min': 30,   'max': 8000,'label': 'Woda kot. Przewodn.', 'unit': 'µS/cm'},
    }

    for f in qs:
        all_ok, _, devs = sprawdz_odchylki(f)
        if all_ok:
            ok_count += 1
        else:
            nok_count += 1
            for d in devs:
                deviations_list.append({
                    'data': f.data.strftime('%d.%m.%Y'),
                    'label': d['label'],
                    'value': d['value'],
                    'tolerance': d['tolerance'],
                    'pk': f.pk,
                })

        label = f.data.strftime('%d.%m')
        chart_labels.append(label)
        for field in chart_data:
            val = getattr(f, field)
            chart_data[field].append(float(val) if val is not None else None)

    ok_pct = round(ok_count / total * 100) if total else None

    context = {
        'preset': preset,
        'date_from': date_from.strftime('%Y-%m-%d'),
        'date_to':   date_to.strftime('%Y-%m-%d'),
        'total': total,
        'ok_count': ok_count,
        'nok_count': nok_count,
        'ok_pct': ok_pct,
        'deviations_list': deviations_list,
        'chart_labels_json':     json.dumps(chart_labels),
        'chart_data_json':       json.dumps(chart_data),
        'chart_tolerances_json': json.dumps(chart_tolerances),
        'is_superuser': request.user.is_superuser,
    }
    return render(request, 'kotlownia/dashboard.html', context)


@login_required
def ustawienia(request):
    if not is_admin(request.user):
        messages.error(request, 'Brak uprawnień do ustawień.')
        return redirect('dashboard')
    obj = KotlowniaUstawienia.get()
    odbiorcy = obj.odbiorcy
    if request.method == 'POST':
        odbiorcy = list(dict.fromkeys(
            e.strip() for e in request.POST.getlist('odbiorcy') if e.strip()
        ))
        invalid = []
        for e in odbiorcy:
            try:
                validate_email(e)
            except ValidationError:
                invalid.append(e)
        if invalid:
            messages.error(request, 'Nieprawidłowy adres e-mail: ' + ', '.join(invalid))
        else:
            obj.odbiorcy = odbiorcy
            obj.save()
            messages.success(request, 'Ustawienia zapisane.')
            return redirect('kotlownia:ustawienia')
    return render(request, 'kotlownia/ustawienia.html', {'odbiorcy': odbiorcy})


@login_required
@require_POST
def formularz_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, 'Brak uprawnień do usuwania wpisów.')
        return redirect('kotlownia:list')
    obj = get_object_or_404(KotlowniaFormularz, pk=pk)
    logger.info('formularz deleted pk=%s data=%s by=%s', obj.pk, obj.data, request.user)
    Powiadomienie.objects.filter(url=reverse('kotlownia:etap2', args=[pk])).delete()
    obj.delete()
    messages.success(request, 'Wpis usunięty.')
    return redirect('kotlownia:list')
