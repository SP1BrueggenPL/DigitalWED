from django.db import models
from django.contrib.auth.models import User


class KotlowniaFormularz(models.Model):
    STATUS_TECHNICZNY   = 'techniczny'
    STATUS_LABORATORIUM = 'laboratorium'
    STATUS_ZAKONCZONY   = 'zakonczony'
    STATUS_CHOICES = [
        (STATUS_TECHNICZNY,   'Etap 1 – Dział Techniczny'),
        (STATUS_LABORATORIUM, 'Etap 2 – Laboratorium'),
        (STATUS_ZAKONCZONY,   'Zakończony'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_TECHNICZNY, verbose_name='Status')

    # Nagłówek - Dział Techniczny
    technician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='tech_forms', verbose_name='Technik')
    data = models.DateField(verbose_name='Data')
    godzina = models.TimeField(verbose_name='Godzina')
    podpis_techniczny = models.TextField(blank=True, verbose_name='Podpis cyfrowy (Dział Techniczny – base64)')

    # A. Woda miejska
    woda_socjalna_m3 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='Woda miejska - Pomieszczenie socjalne [m3]')
    woda_produkcja_m3 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='Woda miejska - Produkcja [m3]')

    # A. Olej opałowy
    olej_poziom_cm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='Olej opałowy - Poziom zbiornika [cm]')
    olej_licznik_litry = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Olej opałowy - Licznik oleju [litry]')

    # A. Gaz - zbiorniki 1-6
    gaz_cisnienie_1 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='Gaz zbiornik 1 - Ciśnienie [bar]')
    gaz_wypelnienie_1 = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='Gaz zbiornik 1 - Wypełnienie [%]')
    gaz_cisnienie_2 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    gaz_wypelnienie_2 = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    gaz_cisnienie_3 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    gaz_wypelnienie_3 = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    gaz_cisnienie_4 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    gaz_wypelnienie_4 = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    gaz_cisnienie_5 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    gaz_wypelnienie_5 = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    gaz_cisnienie_6 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    gaz_wypelnienie_6 = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)

    # B. Nadzór urządzeń kotłowych (wartość + uwagi dla poz. 1-15)
    b1_wartosc = models.CharField(max_length=100, blank=True, verbose_name='1. Wskaźnik poziomu wody - Wartość')
    b1_uwagi = models.TextField(blank=True, verbose_name='1. Wskaźnik poziomu wody - Uwagi')
    b2_wartosc = models.CharField(max_length=100, blank=True, verbose_name='2. Regulator poziomu wody - Wartość')
    b2_uwagi = models.TextField(blank=True)
    b3_wartosc = models.CharField(max_length=100, blank=True, verbose_name='3. Regulator temperatury lub ciśnienia - Wartość')
    b3_uwagi = models.TextField(blank=True)
    b4_wartosc = models.CharField(max_length=100, blank=True, verbose_name='4. Urządzenie do opróżniania lub odsalania kotła - Wartość')
    b4_uwagi = models.TextField(blank=True)
    b5_wartosc = models.CharField(max_length=100, blank=True, verbose_name='5. Aparatura kontroli zanieczyszczeń - Wartość')
    b5_uwagi = models.TextField(blank=True)
    b6_wartosc = models.CharField(max_length=100, blank=True, verbose_name='6. Regulacja palnika - Wartość')
    b6_uwagi = models.TextField(blank=True)
    b7_wartosc = models.CharField(max_length=100, blank=True, verbose_name='7. Wentylatory - Wartość')
    b7_uwagi = models.TextField(blank=True)
    b8_wartosc = models.CharField(max_length=100, blank=True, verbose_name='8. Awaryjne urządzenie odcinające - Wartość')
    b8_uwagi = models.TextField(blank=True)
    b9_wartosc = models.CharField(max_length=100, blank=True, verbose_name='9. Zapłon - Wartość')
    b9_uwagi = models.TextField(blank=True)
    b10_wartosc = models.CharField(max_length=100, blank=True, verbose_name='10. Wentylacja - Wartość')
    b10_uwagi = models.TextField(blank=True)
    b11_wartosc = models.CharField(max_length=100, blank=True, verbose_name='11. Kontrola płomienia - Wartość')
    b11_uwagi = models.TextField(blank=True)
    b12_wartosc = models.CharField(max_length=100, blank=True, verbose_name='12. Ocena jakości spalania - Wartość')
    b12_uwagi = models.TextField(blank=True)
    b13_wartosc = models.CharField(max_length=100, blank=True, verbose_name='13. Licznik - całk. godz. pracy - Wartość')
    b13_uwagi = models.TextField(blank=True)
    b14_wartosc = models.CharField(max_length=100, blank=True, verbose_name='14. Licznik - całk. godz. pracy palnika - Wartość')
    b14_uwagi = models.TextField(blank=True)
    b15_wartosc = models.CharField(max_length=100, blank=True, verbose_name='15. Licznik - impulsy rozruchowe palnika - Wartość')
    b15_uwagi = models.TextField(blank=True)

    # Laboratorium
    laborant = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='lab_forms', verbose_name='Laborant')
    lab_godzina = models.TimeField(null=True, blank=True, verbose_name='Godzina przeprowadzenia analiz')
    podpis_laboratorium = models.TextField(blank=True, verbose_name='Podpis cyfrowy (Laboratorium – base64)')

    # C. Woda zasilająca
    wz_ph = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Woda zasilająca - pH (25°C)')
    wz_wapnioce_dh = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Woda zasilająca - Wapniowce °dH')
    wz_tlen_mg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Woda zasilająca - Tlen O₂ mg/litr')
    wz_przewodnosc = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='Woda zasilająca - Przewodność µS/cm')
    wz_temperatura = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='Woda zasilająca - Temperatura °C')
    wz_wyglad = models.CharField(max_length=10, blank=True, choices=[('ok', 'Ok'), ('nie', 'Nie')], verbose_name='Woda zasilająca - Wygląd')

    # C. Kondensat
    k_ph = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Kondensat - pH (25°C)')
    k_wapnioce_dh = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Kondensat - Wapniowce °dH')
    k_przewodnosc = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='Kondensat - Przewodność µS/cm')

    # C. Woda kotłowa
    wk_ph = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Woda kotłowa - pH (25°C)')
    wk_wapnioce_dh = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Woda kotłowa - Wapniowce °dH')
    wk_przewodnosc = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='Woda kotłowa - Przewodność µS/cm')
    wk_wyglad = models.CharField(max_length=10, blank=True, choices=[('ok', 'Ok'), ('nie', 'Nie')], verbose_name='Woda kotłowa - Wygląd')

    # C. Woda po uzdatnianiu
    wu_ph = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Woda po uzdatnianiu - pH (25°C)')
    wu_wapnioce_dh = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Woda po uzdatnianiu - Wapniowce °dH')
    wu_przewodnosc = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, verbose_name='Woda po uzdatnianiu - Przewodność µS/cm')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Formularz nadzoru kotłowni'
        verbose_name_plural = 'Formularze nadzoru kotłowni'
        ordering = ['-data', '-godzina']

    def __str__(self):
        return f'Kotłownia {self.data} {self.godzina}'
