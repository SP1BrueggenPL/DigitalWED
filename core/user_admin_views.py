from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django import forms
from .models import UserProfile, Klaster


def _staff_only(user):
    return user.is_superuser or user.groups.filter(name='Administratorzy').exists()


def _fc(widget=None, **kwargs):
    w = widget or forms.TextInput
    return w(attrs={'class': 'form-control', **kwargs})


# ── FORMULARZE ────────────────────────────────────────────────

class UserCreateForm(forms.Form):
    username   = forms.CharField(max_length=150, label='Nazwa użytkownika', widget=_fc())
    first_name = forms.CharField(max_length=150, label='Imię', required=False, widget=_fc())
    last_name  = forms.CharField(max_length=150, label='Nazwisko', required=False, widget=_fc())
    email      = forms.EmailField(label='E-mail', required=False, widget=_fc(forms.EmailInput))
    password   = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label='Hasło tymczasowe')
    password2  = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label='Powtórz hasło')
    klaster    = forms.ModelChoiceField(
        queryset=Klaster.objects.all(),
        required=False,
        label='Klaster (opcjonalnie)',
        empty_label='— wybierz klaster lub ustaw role ręcznie —',
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_klaster'}),
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label='Role (ręcznie)',
        widget=forms.CheckboxSelectMultiple,
    )

    def clean(self):
        cd = super().clean()
        if cd.get('password') != cd.get('password2'):
            raise forms.ValidationError('Hasła się nie zgadzają.')
        return cd

    def clean_username(self):
        u = self.cleaned_data['username']
        if User.objects.filter(username=u).exists():
            raise forms.ValidationError('Użytkownik o tej nazwie już istnieje.')
        return u


class UserEditForm(forms.Form):
    first_name = forms.CharField(max_length=150, label='Imię', required=False, widget=_fc())
    last_name  = forms.CharField(max_length=150, label='Nazwisko', required=False, widget=_fc())
    email      = forms.EmailField(label='E-mail', required=False, widget=_fc(forms.EmailInput))
    klaster    = forms.ModelChoiceField(
        queryset=Klaster.objects.all(),
        required=False,
        label='Klaster',
        empty_label='— brak / ustaw role ręcznie —',
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_klaster'}),
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label='Role (ręcznie)',
        widget=forms.CheckboxSelectMultiple,
    )
    is_active = forms.BooleanField(required=False, label='Konto aktywne')


class PasswordResetForm(forms.Form):
    password  = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label='Nowe hasło')
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label='Powtórz hasło')

    def clean(self):
        cd = super().clean()
        if cd.get('password') != cd.get('password2'):
            raise forms.ValidationError('Hasła się nie zgadzają.')
        return cd


class KlasterForm(forms.ModelForm):
    class Meta:
        model = Klaster
        fields = ['nazwa', 'opis', 'grupy']
        widgets = {
            'nazwa': forms.TextInput(attrs={'class': 'form-control'}),
            'opis':  forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'grupy': forms.CheckboxSelectMultiple,
        }
        labels = {
            'nazwa': 'Nazwa klastra',
            'opis':  'Opis (opcjonalnie)',
            'grupy': 'Role w klastrze',
        }


# ── WIDOKI UŻYTKOWNIKÓW ───────────────────────────────────────

@login_required
@user_passes_test(_staff_only)
def user_list(request):
    users = User.objects.prefetch_related('groups').order_by('username')
    klastry = Klaster.objects.prefetch_related('grupy').all()
    return render(request, 'core/user_list.html', {'users': users, 'klastry': klastry})


@login_required
@user_passes_test(_staff_only)
def user_create(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            u = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
            )
            # Klaster ma priorytet; jeśli nie wybrano — bierz ręczne role
            klaster = form.cleaned_data.get('klaster')
            if klaster:
                u.groups.set(klaster.grupy.all())
            else:
                u.groups.set(form.cleaned_data['groups'])
            u.save()
            UserProfile.objects.create(user=u, must_change_password=True)
            messages.success(request, f'Użytkownik „{u.username}" utworzony. Przy pierwszym logowaniu zostanie poproszony o zmianę hasła.')
            return redirect('user_list')
    else:
        form = UserCreateForm()
    import json
    klastry_data = json.dumps({str(k.pk): list(k.grupy.values_list('pk', flat=True)) for k in Klaster.objects.prefetch_related('grupy')})
    return render(request, 'core/user_form.html', {
        'form': form,
        'action': 'Nowy użytkownik',
        'klastry_data': klastry_data,
    })


@login_required
@user_passes_test(_staff_only)
def user_edit(request, pk):
    u = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UserEditForm(request.POST)
        if form.is_valid():
            u.first_name = form.cleaned_data['first_name']
            u.last_name  = form.cleaned_data['last_name']
            u.email      = form.cleaned_data['email']
            u.is_active  = form.cleaned_data['is_active']
            klaster = form.cleaned_data.get('klaster')
            if klaster:
                u.groups.set(klaster.grupy.all())
            else:
                u.groups.set(form.cleaned_data['groups'])
            u.save()
            messages.success(request, f'Użytkownik „{u.username}" zaktualizowany.')
            return redirect('user_list')
    else:
        form = UserEditForm(initial={
            'first_name': u.first_name,
            'last_name':  u.last_name,
            'email':      u.email,
            'groups':     u.groups.all(),
            'is_active':  u.is_active,
        })
    import json
    klastry_data = json.dumps({str(k.pk): list(k.grupy.values_list('pk', flat=True)) for k in Klaster.objects.prefetch_related('grupy')})
    return render(request, 'core/user_form.html', {
        'form': form,
        'action': f'Edytuj: {u.username}',
        'edit_user': u,
        'klastry_data': klastry_data,
    })


@login_required
@user_passes_test(_staff_only)
def user_password(request, pk):
    u = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            u.set_password(form.cleaned_data['password'])
            u.save()
            messages.success(request, f'Hasło użytkownika „{u.username}" zmienione.')
            return redirect('user_list')
    else:
        form = PasswordResetForm()
    return render(request, 'core/user_form.html', {'form': form, 'action': f'Zmień hasło: {u.username}', 'edit_user': u})


# ── WIDOKI KLASTRÓW ───────────────────────────────────────────

@login_required
@user_passes_test(_staff_only)
def klaster_create(request):
    if request.method == 'POST':
        form = KlasterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Klaster „{form.cleaned_data["nazwa"]}" utworzony.')
            return redirect('user_list')
    else:
        form = KlasterForm()
    return render(request, 'core/klaster_form.html', {'form': form, 'action': 'Nowy klaster'})


@login_required
@user_passes_test(_staff_only)
def klaster_edit(request, pk):
    k = get_object_or_404(Klaster, pk=pk)
    if request.method == 'POST':
        form = KlasterForm(request.POST, instance=k)
        if form.is_valid():
            form.save()
            messages.success(request, f'Klaster „{k.nazwa}" zaktualizowany.')
            return redirect('user_list')
    else:
        form = KlasterForm(instance=k)
    return render(request, 'core/klaster_form.html', {'form': form, 'action': f'Edytuj klaster: {k.nazwa}', 'klaster': k})


@login_required
@user_passes_test(_staff_only)
def klaster_delete(request, pk):
    k = get_object_or_404(Klaster, pk=pk)
    if request.method == 'POST':
        nazwa = k.nazwa
        k.delete()
        messages.success(request, f'Klaster „{nazwa}" usunięty.')
    return redirect('user_list')
