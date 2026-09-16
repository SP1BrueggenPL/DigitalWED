from django.db import models
from django.contrib.auth.models import User


WED_MIEJSCA_CHOICES = [
    ('warsztat_elektryk',   'Warsztat elektryków (przy śluzie)'),
    ('regal_dt_magazyn',    'Regał DT w Magazynie (niedaleko magazynku aromatów)'),
    ('warsztat',            'Warsztat'),
    ('kontener_chemia',     'Kontener - magazynek chemii'),
    ('kontener_czesci',     'Kontener - magazynek części zamiennych'),
    ('magazynek_elektronika', 'Magazynek elektroniki'),
    ('biuro_dt',            'Biuro DT (sprawdzenie dokumentacji)'),
    ('warsztat_rampa1',     'Warsztat przy rampie 1'),
]


class Zmiana(models.Model):
    TYPY = [
        ('ranna',         'Ranna (06:00–14:00)'),
        ('popoludniowa',  'Popołudniowa (14:00–22:00)'),
        ('nocna',         'Nocna (22:00–06:00)'),
    ]
    data = models.DateField(verbose_name='Data')
    typ = models.CharField(max_length=20, choices=TYPY, verbose_name='Typ zmiany')
    osoby = models.ManyToManyField(
        User, blank=True, related_name='zmiany',
        verbose_name='Osoby na zmianie',
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Zmiana'
        verbose_name_plural = 'Zmiany'
        unique_together = [('data', 'typ')]
        ordering = ['-data', 'typ']

    def __str__(self):
        return f"{self.data} – {self.get_typ_display()}"


class InspekcjaSekcja(models.Model):
    """Szablon sekcji listy kontrolnej (konfigurowany przez admina)."""
    TYP_INSPEKCJI = [('wed', 'Inspekcja WED')]

    typ_inspekcji = models.CharField(
        max_length=20, choices=TYP_INSPEKCJI, default='wed',
        verbose_name='Typ inspekcji',
    )
    nazwa = models.CharField(max_length=200, verbose_name='Nazwa sekcji')
    kolejnosc = models.PositiveIntegerField(default=0, verbose_name='Kolejność')

    class Meta:
        verbose_name = 'Sekcja listy kontrolnej'
        verbose_name_plural = 'Sekcje listy kontrolnej'
        ordering = ['typ_inspekcji', 'kolejnosc']

    def __str__(self):
        return f"[{self.get_typ_inspekcji_display()}] {self.nazwa}"


class InspekcjaPunkt(models.Model):
    """Punkt kontrolny w sekcji."""
    sekcja = models.ForeignKey(
        InspekcjaSekcja, on_delete=models.CASCADE, related_name='punkty',
    )
    tresc = models.TextField(verbose_name='Treść punktu')
    kolejnosc = models.PositiveIntegerField(default=0, verbose_name='Kolejność')

    class Meta:
        verbose_name = 'Punkt kontrolny'
        verbose_name_plural = 'Punkty kontrolne'
        ordering = ['kolejnosc']

    def __str__(self):
        return f"{self.sekcja.nazwa} › {self.tresc[:60]}"


class InspekcjaPodpunkt(models.Model):
    """Podpunkt kontrolny (opcjonalny)."""
    punkt = models.ForeignKey(
        InspekcjaPunkt, on_delete=models.CASCADE, related_name='podpunkty',
    )
    tresc = models.TextField(verbose_name='Treść podpunktu')
    kolejnosc = models.PositiveIntegerField(default=0, verbose_name='Kolejność')

    class Meta:
        verbose_name = 'Podpunkt kontrolny'
        verbose_name_plural = 'Podpunkty kontrolne'
        ordering = ['kolejnosc']

    def __str__(self):
        return f"{self.punkt.sekcja.nazwa} › {self.punkt.tresc[:40]} › {self.tresc[:40]}"


class Inspekcja(models.Model):
    TYPY = [('wed', 'Inspekcja WED')]
    STATUSY = [('w_toku', 'W toku'), ('zakonczona', 'Zakończona')]

    typ = models.CharField(
        max_length=20, choices=TYPY, default='wed', verbose_name='Typ inspekcji',
    )
    zmiana = models.ForeignKey(
        Zmiana, on_delete=models.PROTECT, related_name='inspekcje',
        verbose_name='Zmiana',
    )
    osoby_kontrolujace = models.ManyToManyField(
        User, blank=True, related_name='inspekcje_kontrolowane',
        verbose_name='Osoby kontrolujące',
    )
    miejsce = models.CharField(
        max_length=100, blank=True,
        choices=WED_MIEJSCA_CHOICES,
        verbose_name='Miejsce inspekcji',
    )
    status = models.CharField(
        max_length=20, choices=STATUSY, default='w_toku', verbose_name='Status',
    )
    ukryta = models.BooleanField(default=False, verbose_name='Ukryta')
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='inspekcje_utworzone',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Inspekcja'
        verbose_name_plural = 'Inspekcje'
        ordering = ['-created_at']

    def __str__(self):
        return f"Inspekcja WED – {self.zmiana} ({self.get_status_display()})"

    def get_miejsce_display_value(self):
        return dict(WED_MIEJSCA_CHOICES).get(self.miejsce, self.miejsce)


class InspekcjaWynik(models.Model):
    """Wynik dla konkretnego punktu/podpunktu inspekcji + opcjonalne zdjęcie z analizą AI."""
    WYNIKI = [
        ('ok',  'OK'),
        ('nok', 'Niezgodne'),
        ('nd',  'Nie dotyczy'),
    ]

    inspekcja = models.ForeignKey(
        Inspekcja, on_delete=models.CASCADE, related_name='wyniki',
    )
    sekcja = models.ForeignKey(InspekcjaSekcja, on_delete=models.PROTECT)
    punkt = models.ForeignKey(
        InspekcjaPunkt, on_delete=models.PROTECT, null=True, blank=True,
    )
    podpunkt = models.ForeignKey(
        InspekcjaPodpunkt, on_delete=models.PROTECT, null=True, blank=True,
    )
    wynik = models.CharField(max_length=5, choices=WYNIKI, default='nd')
    uwagi = models.TextField(blank=True, verbose_name='Uwagi')
    zdjecie = models.ImageField(
        upload_to='inspekcje/', null=True, blank=True, verbose_name='Zdjęcie',
    )
    analiza_ai = models.TextField(blank=True, verbose_name='Analiza AI')
    ai_sugestia = models.CharField(
        max_length=400, blank=True, verbose_name='Sugestia AI (sekcja)',
    )
    ai_pasuje = models.BooleanField(null=True, blank=True)

    class Meta:
        verbose_name = 'Wynik inspekcji'
        verbose_name_plural = 'Wyniki inspekcji'
        unique_together = [('inspekcja', 'punkt', 'podpunkt')]

    def __str__(self):
        return (
            f"Wynik [{self.get_wynik_display()}] – "
            f"{self.punkt or self.sekcja}"
        )
