"""Import zbiorczy użytkowników z pliku Excel (.xlsx)."""
import io
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render

from .models import UserProfile
from .permissions import is_admin
from .user_admin_views import FIXED_GROUPS

MAX_ROWS = 2000
MAX_SIZE = 5 * 1024 * 1024

# nagłówek w pliku (po normalizacji) -> pole
HEADERS = {
    'imie i nazwisko': 'full_name', 'imie nazwisko': 'full_name', 'nazwisko i imie': 'full_name_rev',
    'imie': 'first_name', 'nazwisko': 'last_name',
    'email': 'email', 'e-mail': 'email', 'mail': 'email', 'adres e-mail': 'email', 'adres email': 'email',
    'chip': 'chip', 'numer chip': 'chip', 'nr chip': 'chip', 'numer chipa': 'chip', 'nr chipa': 'chip',
    'grupy': 'groups', 'grupa': 'groups', 'role': 'groups', 'rola': 'groups',
}
_PL = str.maketrans('ąćęłńóśźż', 'acelnoszz')


def _norm(value):
    return re.sub(r'\s+', ' ', str(value or '').replace('*', '').strip().lower().translate(_PL))


def _text(value):
    """Wartość komórki jako tekst; liczby całkowite bez „.0”."""
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def _group_lookup():
    """Nazwy grup akceptowane w pliku: pełne oraz skrócone (np. „Elektrycy”)."""
    lookup = {}
    for g in Group.objects.filter(name__in=FIXED_GROUPS):
        lookup[_norm(g.name)] = g
        if ' - ' in g.name:
            lookup[_norm(g.name.split(' - ', 1)[1])] = g
    return lookup


def _import(rows):
    """rows: iterator krotek z arkusza. Zwraca (dodani, pominięci, błędy)."""
    header = None
    for header in rows:
        if any(c not in (None, '') for c in header):
            break
    if not header:
        raise ValueError('Plik jest pusty.')
    cols = {}
    for idx, cell in enumerate(header):
        field = HEADERS.get(_norm(cell))
        if field and field not in cols:
            cols[field] = idx
    if 'chip' not in cols:
        raise ValueError('W pierwszym wierszu brakuje kolumny „Chip”. Pobierz szablon i użyj jego nagłówków.')

    groups = _group_lookup()
    used_chips = set(UserProfile.objects.exclude(chip_number__isnull=True).values_list('chip_number', flat=True))
    used_names = set(User.objects.values_list('username', flat=True))
    used_mails = {e.lower() for e in User.objects.exclude(email='').values_list('email', flat=True)}
    added, skipped, errors = [], [], []

    def get(row, field):
        i = cols.get(field)
        return _text(row[i]) if i is not None and i < len(row) else ''

    for n, row in enumerate(rows, start=2):
        if n > MAX_ROWS:
            errors.append((n, '', f'Przerwano – plik ma więcej niż {MAX_ROWS} wierszy.'))
            break
        if not any(c not in (None, '') for c in row):
            continue
        first, last = get(row, 'first_name'), get(row, 'last_name')
        full = get(row, 'full_name')
        if full and not (first or last):
            first, _, last = full.partition(' ')
        rev = get(row, 'full_name_rev')
        if rev and not (first or last):
            last, _, first = rev.partition(' ')
        first, last = first.strip(), last.strip()
        label = f'{first} {last}'.strip()
        email, chip = get(row, 'email'), get(row, 'chip')

        problems = []
        if not chip:
            problems.append('brak numeru chip')
        elif len(chip) > 20:
            problems.append('numer chip dłuższy niż 20 znaków')
        if len(first) > 150 or len(last) > 150:
            problems.append('imię lub nazwisko za długie')
        if email:
            try:
                validate_email(email)
            except ValidationError:
                problems.append(f'niepoprawny e-mail „{email}”')
        row_groups = []
        for name in re.split(r'[;,\n]+', get(row, 'groups')):
            if not name.strip():
                continue
            g = groups.get(_norm(name))
            if g is None:
                problems.append(f'nieznana grupa „{name.strip()}”')
            elif g not in row_groups:
                row_groups.append(g)
        if problems:
            errors.append((n, label or chip, '; '.join(problems)))
            continue

        if chip in used_chips or f'chip_{chip}' in used_names:
            skipped.append((n, label or chip, 'numer chip już istnieje'))
            continue
        if email and email.lower() in used_mails:
            skipped.append((n, label or chip, 'e-mail już istnieje'))
            continue

        with transaction.atomic():
            u = User(username=f'chip_{chip}', first_name=first, last_name=last, email=email)
            u.set_unusable_password()
            u.save()
            u.groups.set(row_groups)
            UserProfile.objects.create(user=u, chip_number=chip)
        used_chips.add(chip)
        used_names.add(u.username)
        if email:
            used_mails.add(email.lower())
        added.append((n, label or chip, ', '.join(g.name for g in row_groups) or 'brak grup'))
    return added, skipped, errors


@login_required
@user_passes_test(is_admin)
def user_import(request):
    ctx = {'grupy': FIXED_GROUPS}
    if request.method == 'POST':
        f = request.FILES.get('plik')
        if not f:
            messages.error(request, 'Wybierz plik Excel (.xlsx).')
        elif not f.name.lower().endswith('.xlsx'):
            messages.error(request, 'Obsługiwany jest tylko format .xlsx (Excel).')
        elif f.size > MAX_SIZE:
            messages.error(request, 'Plik jest za duży (limit 5 MB).')
        else:
            try:
                from openpyxl import load_workbook
                wb = load_workbook(io.BytesIO(f.read()), read_only=True, data_only=True)
                added, skipped, errors = _import(wb.worksheets[0].iter_rows(values_only=True))
                ctx.update(wynik=True, added=added, skipped=skipped, errors=errors)
            except ValueError as e:
                messages.error(request, str(e))
            except Exception:
                messages.error(request, 'Nie udało się odczytać pliku. Upewnij się, że to poprawny plik .xlsx.')
    return render(request, 'core/user_import.html', ctx)


@login_required
@user_passes_test(is_admin)
def user_import_template(request):
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    ws = wb.active
    ws.title = 'Użytkownicy'
    ws.append(['Imię', 'Nazwisko', 'E-mail', 'Chip', 'Grupy'])
    ws.append(['Jan', 'Przykładowy', 'jan.przykladowy@example.com', '12345', 'Kotłownia - Elektrycy; Engineering'])
    for c in ws[1]:
        c.font = Font(bold=True)
    for col, width in zip('ABCDE', (18, 24, 34, 14, 48)):
        ws.column_dimensions[col].width = width
    for r in range(2, 502):  # chip jako tekst – zachowuje zera wiodące
        ws.cell(row=r, column=4).number_format = '@'
    info = wb.create_sheet('Instrukcja')
    for line in (
        'Wypełnij arkusz „Użytkownicy” – jeden wiersz to jedna osoba. Wiersz przykładowy usuń.',
        'Chip jest wymagany. E-mail, imię i nazwisko są opcjonalne.',
        'Grupy oddziel średnikiem lub przecinkiem. Puste pole = użytkownik bez grup.',
        'Osoby, których numer chip lub e-mail już jest w aplikacji, zostaną pominięte.',
        '',
        'Dostępne grupy:',
        *FIXED_GROUPS,
    ):
        info.append([line])
    info.column_dimensions['A'].width = 90
    buf = io.BytesIO()
    wb.save(buf)
    resp = HttpResponse(buf.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp['Content-Disposition'] = 'attachment; filename="import_uzytkownikow_szablon.xlsx"'
    return resp
