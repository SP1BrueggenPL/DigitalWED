from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserProfile


class Command(BaseCommand):
    help = 'Dodaje użytkownika z numerem chip'

    def add_arguments(self, parser):
        parser.add_argument('--chip', required=True, help='Numer chip')
        parser.add_argument('--username', default=None, help='Nazwa użytkownika (domyślnie: chip_<numer>)')
        parser.add_argument('--admin', action='store_true', help='Uprawnienia superuser')

    def handle(self, *args, **options):
        chip = options['chip']
        username = options['username'] or f'chip_{chip}'
        is_admin = options['admin']

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'Użytkownik {username} już istnieje.'))
            user = User.objects.get(username=username)
        else:
            user = User.objects.create_user(
                username=username,
                password=None,
                is_staff=is_admin,
                is_superuser=is_admin,
            )
            user.set_unusable_password()
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Utworzono użytkownika: {username}'))

        profile, created = UserProfile.objects.get_or_create(user=user)
        if UserProfile.objects.filter(chip_number=chip).exclude(user=user).exists():
            self.stdout.write(self.style.ERROR(f'Numer chip {chip} jest już zajęty.'))
            return

        profile.chip_number = chip
        profile.auth_code_set = False
        profile.auth_code = ''
        profile.save()

        self.stdout.write(self.style.SUCCESS(
            f'Chip {chip} przypisany do {username} '
            f'({"admin" if is_admin else "użytkownik"}). '
            f'Kod autoryzacyjny zostanie ustawiony przy pierwszym logowaniu.'
        ))
