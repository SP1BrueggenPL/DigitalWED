import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wed_platform.settings')
django.setup()
from django.contrib.auth import get_user_model
U = get_user_model()
if not U.objects.filter(username='admin').exists():
    U.objects.create_superuser('admin', 'admin@brueggen.com', 'admin123')
    print('Superuser created: admin / admin123')
else:
    print('Admin already exists')
