from django.contrib import admin
from .models import KontrolaElektryka, ElektrykUstawienia


@admin.register(KontrolaElektryka)
class KontrolaElektrykaAdmin(admin.ModelAdmin):
    list_display = ['start', 'elektryk', 'sol_mag', 'p138_mag', 'd280_mag', 'czystosc']
    date_hierarchy = 'start'


@admin.register(ElektrykUstawienia)
class ElektrykUstawieniaAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not ElektrykUstawienia.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
