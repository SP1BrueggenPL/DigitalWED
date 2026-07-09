from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponse
from django.template.loader import render_to_string
from .models import KotlowniaFormularz
from .forms import EtapTechnicznyForm, EtapLaboratoriumForm
from core.notifications import powiadom_laboratorium
from core.models import Powiadomienie

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


def _has_process_access(user):
    """Dostęp do procesu Kotłownia wymaga roli Kotłownia lub superusera."""
    return user.is_superuser or user.groups.filter(name='Kotłownia').exists()


def _is_lab(user):
    return user.is_superuser or user.groups.filter(name='Laboratorium').exists()


def _is_tech(user):
    return user.is_superuser or user.groups.filter(name='Techniczny').exists()


def _can_edit_etap1(user):
    if user.is_superuser:
        return True
    in_tech = user.groups.filter(name='Techniczny').exists()
    in_lab  = user.groups.filter(name='Laboratorium').exists()
    return in_tech or (not in_lab)


def _can_edit_etap2(user):
    return user.is_superuser or user.groups.filter(name='Laboratorium').exists()


@login_required
def formularz_list(request):
    if not _has_process_access(request.user):
        messages.error(request, 'Brak dostępu do procesu Nadzór kotłowni. Wymagana rola: Kotłownia.')
        return redirect('dashboard')

    if _is_lab(request.user) and not _is_tech(request.user) and not request.user.is_superuser:
        pending = KotlowniaFormularz.objects.filter(status=KotlowniaFormularz.STATUS_LABORATORIUM)
        done = KotlowniaFormularz.objects.filter(
            status=KotlowniaFormularz.STATUS_ZAKONCZONY,
            laborant=request.user,
        )
        return render(request, 'kotlownia/list_lab.html', {'pending': pending, 'done': done})
    elif request.user.is_superuser:
        formularze = KotlowniaFormularz.objects.all()
        return render(request, 'kotlownia/list.html', {'formularze': formularze})
    else:
        formularze = KotlowniaFormularz.objects.filter(technician=request.user)
        return render(request, 'kotlownia/list.html', {'formularze': formularze})


@login_required
def etap_techniczny(request, pk=None):
    obj = get_object_or_404(KotlowniaFormularz, pk=pk) if pk else None

    if not _has_process_access(request.user):
        messages.error(request, 'Brak dostępu do procesu Nadzór kotłowni.')
        return redirect('dashboard')

    # Zablokuj edycję ukończonego formularza
    if obj and obj.status == KotlowniaFormularz.STATUS_ZAKONCZONY:
        messages.error(request, 'Formularz jest zakończony i nie może być edytowany.')
        return redirect('kotlownia:detail', pk=obj.pk)

    # Tylko technik lub admin może wypełniać etap 1
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
            saved.status = KotlowniaFormularz.STATUS_LABORATORIUM
            saved.save()
            powiadom_laboratorium(saved)
            messages.success(request, 'Etap 1 zapisany. Powiadomienie wysłane do Laboratorium.')
            return redirect('kotlownia:detail', pk=saved.pk)
    else:
        form = EtapTechnicznyForm(instance=obj)

    return render(request, 'kotlownia/etap1.html', {
        'form': form, 'obj': obj,
        'title': 'Etap 1 – Dział Techniczny',
        'b_rows': B_ROWS,
    })


@login_required
def etap_laboratorium(request, pk):
    obj = get_object_or_404(KotlowniaFormularz, pk=pk)

    if not _has_process_access(request.user):
        messages.error(request, 'Brak dostępu do procesu Nadzór kotłowni.')
        return redirect('dashboard')

    # Zablokuj edycję ukończonego formularza
    if obj.status == KotlowniaFormularz.STATUS_ZAKONCZONY:
        messages.error(request, 'Formularz jest zakończony i nie może być edytowany.')
        return redirect('kotlownia:detail', pk=obj.pk)

    # Tylko laboratorium lub admin może wypełniać etap 2
    if not _can_edit_etap2(request.user):
        messages.error(request, 'Brak uprawnień do wypełniania Etapu 2 – wymagana rola Laboratorium.')
        return redirect('kotlownia:detail', pk=pk)

    # Oznacz powiązane powiadomienia jako przeczytane
    Powiadomienie.objects.filter(
        odbiorca=request.user,
        url=reverse('kotlownia:etap2', args=[pk]),
        przeczytane=False,
    ).update(przeczytane=True)

    if request.method == 'POST':
        form = EtapLaboratoriumForm(request.POST, instance=obj)
        if form.is_valid():
            saved = form.save(commit=False)
            saved.laborant = request.user
            sig = request.POST.get('podpis_laboratorium_data', '').strip()
            if sig and not sig.endswith(','):
                saved.podpis_laboratorium = sig
            saved.status = KotlowniaFormularz.STATUS_ZAKONCZONY
            saved.save()
            messages.success(request, 'Etap 2 zapisany. Formularz zakończony.')
            return redirect('kotlownia:detail', pk=saved.pk)
    else:
        form = EtapLaboratoriumForm(instance=obj)

    return render(request, 'kotlownia/etap2.html', {
        'form': form, 'obj': obj,
        'title': 'Etap 2 – Laboratorium',
    })


@login_required
def formularz_detail(request, pk):
    obj = get_object_or_404(KotlowniaFormularz, pk=pk)
    b_rows = [
        {'lp': lp, 'label': label,
         'wartosc': getattr(obj, f'b{lp}_wartosc'),
         'uwagi':   getattr(obj, f'b{lp}_uwagi')}
        for lp, label in B_ROWS
    ]
    return render(request, 'kotlownia/detail.html', {
        'obj': obj,
        'b_rows': b_rows,
        'can_etap1': _can_edit_etap1(request.user),
        'can_etap2': _can_edit_etap2(request.user),
    })


@login_required
def formularz_print(request, pk):
    obj = get_object_or_404(KotlowniaFormularz, pk=pk)
    b_rows = [
        {'lp': lp, 'label': label,
         'wartosc': getattr(obj, f'b{lp}_wartosc'),
         'uwagi':   getattr(obj, f'b{lp}_uwagi')}
        for lp, label in B_ROWS
    ]
    return render(request, 'kotlownia/print.html', {'obj': obj, 'b_rows': b_rows})


@login_required
def formularz_pdf(request, pk):
    from django.utils.timezone import localtime, now
    from .pdf_generator import generate_formularz_pdf

    obj = get_object_or_404(KotlowniaFormularz, pk=pk)
    b_rows = [
        {'lp': lp, 'label': label,
         'wartosc': getattr(obj, f'b{lp}_wartosc'),
         'uwagi':   getattr(obj, f'b{lp}_uwagi')}
        for lp, label in B_ROWS
    ]
    now_str = localtime(now()).strftime('%d.%m.%Y %H:%M')
    pdf_bytes = generate_formularz_pdf(obj, b_rows, now_str)

    filename = f'CD-00001498-2_{obj.data.strftime("%Y-%m-%d")}.pdf'
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def powiadomienia_list(request):
    pows = Powiadomienie.objects.filter(odbiorca=request.user)
    pows.filter(przeczytane=False).update(przeczytane=True)
    return render(request, 'core/powiadomienia.html', {'powiadomienia': pows})
