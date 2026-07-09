from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms


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


ALL_PROCESSES = [
    {
        'id': 'kotlownia',
        'name': 'Nadzór nad kotłownią',
        'doc_number': 'CD-00001498-2',
        'description': 'Formularz kontroli stanu technicznego kotłowni: zapasy surowców, urządzenia kotłowe, analiza laboratoryjna wody.',
        'url': 'kotlownia:list',
        'group': 'Kotłownia',
        'icon': '🔥',
    },
]


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
