from django.contrib import admin
from .models import KotlowniaFormularz


@admin.register(KotlowniaFormularz)
class KotlowniaFormularzAdmin(admin.ModelAdmin):
    list_display = ['data', 'godzina', 'technician', 'created_at']
    list_filter = ['data', 'technician']
    date_hierarchy = 'data'
    ordering = ['-data', '-godzina']
