from django.contrib import admin
from .models import Powiadomienie


@admin.register(Powiadomienie)
class PowiadomieniAdmin(admin.ModelAdmin):
    list_display = ['odbiorca', 'tytul', 'przeczytane', 'created_at']
    list_filter = ['przeczytane', 'odbiorca']
