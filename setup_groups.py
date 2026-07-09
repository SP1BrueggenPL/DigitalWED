import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wed_platform.settings')
django.setup()

from django.contrib.auth.models import User, Group

# Utwórz grupy
for name in ['Administratorzy', 'Kotłownia', 'Techniczny', 'Laboratorium']:
    g, created = Group.objects.get_or_create(name=name)
    print(f"Grupa '{name}': {'utworzona' if created else 'już istnieje'}")

tech_group = Group.objects.get(name='Techniczny')
lab_group  = Group.objects.get(name='Laboratorium')

kotlownia_group = Group.objects.get(name='Kotłownia')

# Użytkownik: tech
if not User.objects.filter(username='tech').exists():
    u = User.objects.create_user('tech', 'tech@brueggen.com', 'tech123')
    u.first_name = 'Adam'
    u.last_name  = 'Nowak'
    u.groups.add(tech_group, kotlownia_group)
    u.save()
    print("Użytkownik 'tech' (hasło: tech123) utworzony → Techniczny + Kotłownia")
else:
    u = User.objects.get(username='tech')
    u.groups.add(tech_group, kotlownia_group)
    u.save()
    print("Użytkownik 'tech' zaktualizowany → Techniczny + Kotłownia")

# Użytkownik: lab
if not User.objects.filter(username='lab').exists():
    u = User.objects.create_user('lab', 'lab@brueggen.com', 'lab123')
    u.first_name = 'Jan'
    u.last_name  = 'Kowalski'
    u.groups.add(lab_group, kotlownia_group)
    u.save()
    print("Użytkownik 'lab' (hasło: lab123) utworzony → Laboratorium + Kotłownia")
else:
    u = User.objects.get(username='lab')
    u.groups.add(lab_group, kotlownia_group)
    u.save()
    print("Użytkownik 'lab' zaktualizowany → Laboratorium + Kotłownia")

# Stary użytkownik laborant
if User.objects.filter(username='laborant').exists():
    u = User.objects.get(username='laborant')
    u.groups.add(lab_group, kotlownia_group)
    u.save()
    print("Użytkownik 'laborant' zaktualizowany → Laboratorium + Kotłownia")

print("\nGotowe. Konta:")
print("  admin  / admin123  (superuser)")
print("  tech   / tech123   (Techniczny – Etap 1)")
print("  lab    / lab123    (Laboratorium – Etap 2)")
