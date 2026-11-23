from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.core import signing
from django import forms
from .models import UserProfile
from .backends import ChipAuthBackend


class ZmienHasloForm(forms.Form):
    haslo_nowe = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'autofocus': True}),
        label='Nowe hasło',
        min_length=6,
    )
    haslo_powtorz = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Powtórz nowe hasło',
    )

    def clean(self):
        cd = super().clean()
        if cd.get('haslo_nowe') != cd.get('haslo_powtorz'):
            raise forms.ValidationError('Hasła się nie zgadzają.')
        return cd


CHIP_TOKEN_SALT = 'login-chip'

ALL_PROCESSES = [
    {
        'id': 'kotlownia',
        'name': 'Nadzór nad kotłownią',
        'doc_number': 'CD-00001498-4',
        'description': 'Formularz kontroli stanu technicznego kotłowni: zapasy surowców, urządzenia kotłowe, analiza laboratoryjna wody.',
        'url': 'kotlownia:list',
        'group': 'Kotłownia',
        'icon': '🔥',
    },
]


def chip_login_step1(request):
    """Krok 1: wpisanie numeru chip."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    error = None
    if request.method == 'POST':
        chip = request.POST.get('chip_number', '').strip()
        if not chip:
            error = 'Podaj numer chip.'
        else:
            try:
                UserProfile.objects.get(chip_number=chip)
                request.session['login_chip'] = chip
                return redirect('login_kod')
            except UserProfile.DoesNotExist:
                error = 'Nieznany numer chip.'
    return render(request, 'core/login_chip.html', {'error': error})


def chip_login_step2(request):
    """Krok 2: ustawienie lub weryfikacja kodu autoryzacyjnego."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    chip = request.session.get('login_chip')
    if not chip and request.method == 'POST':
        # Sesja mogła zostać utracona między krokami (np. podwójne wysłanie formularza).
        try:
            chip = signing.loads(request.POST.get('chip_token', ''), salt=CHIP_TOKEN_SALT, max_age=900)
        except signing.BadSignature:
            chip = None
    profile = UserProfile.objects.select_related('user').filter(chip_number=chip).first() if chip else None
    if not profile:
        return redirect('login')
    first_time = not profile.auth_code_set
    error = None

    if request.method == 'POST':
        kod = request.POST.get('auth_code', '').strip()
        if first_time:
            kod2 = request.POST.get('auth_code2', '').strip()
            if len(kod) < 4:
                error = 'Kod musi mieć co najmniej 4 znaki.'
            elif kod != kod2:
                error = 'Kody się nie zgadzają.'
            elif not profile.user.is_active:
                error = 'Konto jest nieaktywne. Skontaktuj się z administratorem.'
            else:
                profile.auth_code = make_password(kod)
                profile.auth_code_set = True
                profile.save()
                first_time = False
        if not error:
            user = ChipAuthBackend().authenticate(request, chip_number=chip, auth_code=kod)
            if user:
                login(request, user, backend='core.backends.ChipAuthBackend')
                request.session.pop('login_chip', None)
                return redirect('dashboard')
            error = 'Nieprawidłowy kod autoryzacyjny.'

    return render(request, 'core/login_kod.html', {
        'first_time': first_time,
        'error': error,
        'chip_token': signing.dumps(chip, salt=CHIP_TOKEN_SALT),
    })


@login_required
def dashboard(request):
    user = request.user
    if user.is_superuser:
        processes = ALL_PROCESSES
    else:
        user_groups = set(user.groups.values_list('name', flat=True))
        processes = [p for p in ALL_PROCESSES if p['group'] in user_groups]
    return render(request, 'core/dashboard.html', {'processes': processes})


@login_required
def zmien_haslo(request):
    if request.method == 'POST':
        form = ZmienHasloForm(request.POST)
        if form.is_valid():
            request.user.set_password(form.cleaned_data['haslo_nowe'])
            request.user.save()
            try:
                request.user.profile.must_change_password = False
                request.user.profile.save()
            except Exception:
                pass
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Hasło zostało zmienione. Możesz teraz korzystać z platformy.')
            return redirect('dashboard')
    else:
        form = ZmienHasloForm()
    return render(request, 'core/zmien_haslo.html', {'form': form})
