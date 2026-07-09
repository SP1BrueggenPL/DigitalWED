import os, sys
from django.core.management import execute_from_command_line

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wed_platform.settings')
port = os.environ.get('PORT', '8000')
execute_from_command_line(['manage.py', 'runserver', f'0.0.0.0:{port}'])
