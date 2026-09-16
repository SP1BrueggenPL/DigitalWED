from django.contrib import admin
from .models import (
    Zmiana, InspekcjaSekcja, InspekcjaPunkt, InspekcjaPodpunkt,
    Inspekcja, InspekcjaWynik,
)


class InspekcjaPodpunktInline(admin.TabularInline):
    model = InspekcjaPodpunkt
    extra = 1
    fields = ['tresc', 'kolejnosc']


class InspekcjaPunktInline(admin.TabularInline):
    model = InspekcjaPunkt
    extra = 1
    fields = ['tresc', 'kolejnosc']
    show_change_link = True


@admin.register(InspekcjaSekcja)
class InspekcjaSekcjaAdmin(admin.ModelAdmin):
    list_display = ['nazwa', 'typ_inspekcji', 'kolejnosc']
    list_filter = ['typ_inspekcji']
    inlines = [InspekcjaPunktInline]


@admin.register(InspekcjaPunkt)
class InspekcjaPunktAdmin(admin.ModelAdmin):
    list_display = ['tresc', 'sekcja', 'kolejnosc']
    inlines = [InspekcjaPodpunktInline]


@admin.register(Zmiana)
class ZmianaAdmin(admin.ModelAdmin):
    list_display = ['data', 'typ', 'osoby_count']
    list_filter = ['typ']
    filter_horizontal = ['osoby']

    def osoby_count(self, obj):
        return obj.osoby.count()
    osoby_count.short_description = 'Liczba osób'


@admin.register(Inspekcja)
class InspekcjaAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'typ', 'status', 'ukryta', 'created_at']
    list_filter = ['typ', 'status', 'ukryta']
    filter_horizontal = ['osoby_kontrolujace']


@admin.register(InspekcjaWynik)
class InspekcjaWynikAdmin(admin.ModelAdmin):
    list_display = ['inspekcja', 'sekcja', 'punkt', 'wynik', 'ai_pasuje']
    list_filter = ['wynik', 'ai_pasuje']
