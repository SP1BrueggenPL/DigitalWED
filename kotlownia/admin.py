from django.contrib import admin
from .models import KotlowniaFormularz, KotlowniaUstawienia


@admin.register(KotlowniaFormularz)
class KotlowniaFormularzAdmin(admin.ModelAdmin):
    list_display = ['data', 'godzina', 'technician', 'created_at']
    list_filter = ['data', 'technician']
    date_hierarchy = 'data'
    ordering = ['-data', '-godzina']


@admin.register(KotlowniaUstawienia)
class KotlowniaUstawieniaAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not KotlowniaUstawienia.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
