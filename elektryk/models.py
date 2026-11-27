from django.contrib.auth.models import User
from django.db import models

# Progi zamówienia: stan magazynowy poniżej progu oznacza „niski stan”.
LIMITS = {'sol_mag': 25, 'p138_mag': 60, 'd280_mag': 60}
NAMES = {
    'sol_mag':  {'prod': 'Sól zmiękczająca', 'unit': 'worków'},
    'p138_mag': {'prod': 'Eurocept P138S',   'unit': 'l'},
    'd280_mag': {'prod': 'Eurocept D280',    'unit': 'l'},
}
REASONS = ['Odsalanie', 'Kondensat', 'Inna']
NASTAWY = [
    ('pompa1', 'Pompa 1'), ('pompa2', 'Pompa 2'), ('pompa3', 'Pompa 3'),
    ('pompa4', 'Pompa 4'), ('zawor1', 'Zawór 1'), ('zawor2', 'Zawór 2'),
]


class KontrolaElektryka(models.Model):
    elektryk = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='kontrole_elektryka', verbose_name='Elektryk')
    start = models.DateTimeField(verbose_name='Rozpoczęto wpisywanie')
    zapisano = models.DateTimeField(auto_now_add=True, verbose_name='Zapisano')

    sol_duzy = models.FloatField(verbose_name='Sól – zbiornik duży [%]')
    sol_maly = models.FloatField(verbose_name='Sól – zbiornik mały [%]')
    sol_mag = models.FloatField(verbose_name='Sól – magazyn [worki]')
    p138_zb = models.FloatField(verbose_name='Eurocept P138S – zbiornik [%]')
    p138_mag = models.FloatField(verbose_name='Eurocept P138S – magazyn [l]')
    d280_zb = models.FloatField(verbose_name='Eurocept D280 – zbiornik [%]')
    d280_mag = models.FloatField(verbose_name='Eurocept D280 – magazyn [l]')

    zrzut = models.CharField(max_length=20, verbose_name='Zrzut wody do kanału – przyczyna')
    zrzut_inna = models.CharField(max_length=200, blank=True, verbose_name='Inna przyczyna zrzutu')

    pompa1_n = models.CharField(max_length=30, verbose_name='Pompa 1 – nastawa')
    pompa2_n = models.CharField(max_length=30, verbose_name='Pompa 2 – nastawa')
    pompa3_n = models.CharField(max_length=30, verbose_name='Pompa 3 – nastawa')
    pompa4_n = models.CharField(max_length=30, verbose_name='Pompa 4 – nastawa')
    zawor1_n = models.CharField(max_length=30, verbose_name='Zawór 1 – nastawa')
    zawor2_n = models.CharField(max_length=30, verbose_name='Zawór 2 – nastawa')

    cisnienie = models.FloatField(verbose_name='Ciśnienie wody miejskiej [bar]')
    licznik_schl = models.FloatField(verbose_name='Stan licznika wody schładzacza')
    licznik_zm = models.FloatField(verbose_name='Stan licznika stacji zmiękczania wody')
    kolumna = models.CharField(max_length=1, verbose_name='Nr pracującej kolumny')
    czystosc = models.CharField(max_length=3, verbose_name='Czystość pomieszczenia')
    uwagi = models.CharField(max_length=500, blank=True, verbose_name='Uwagi')

    class Meta:
        verbose_name = 'Kontrola dzienna elektryka'
        verbose_name_plural = 'Kontrole dzienne elektryka'
        ordering = ['-start']

    def __str__(self):
        return f'Kontrola elektryka {self.start:%Y-%m-%d %H:%M}'

    def niski_stan(self):
        return [k for k, limit in LIMITS.items() if getattr(self, k) < limit]

    def as_dict(self):
        d = {'start': self.start.isoformat()}
        for f in ('sol_duzy', 'sol_maly', 'sol_mag', 'p138_zb', 'p138_mag', 'd280_zb', 'd280_mag',
                  'zrzut', 'zrzut_inna', 'pompa1_n', 'pompa2_n', 'pompa3_n', 'pompa4_n', 'zawor1_n', 'zawor2_n',
                  'cisnienie', 'licznik_schl', 'licznik_zm', 'kolumna', 'czystosc', 'uwagi'):
            d[f] = getattr(self, f)
        d['niski_stan'] = self.niski_stan()
        return d


class ElektrykUstawienia(models.Model):
    odbiorcy = models.JSONField(default=list, blank=True, verbose_name='Odbiorcy e-mail')

    class Meta:
        verbose_name = 'Ustawienia kontroli elektryka'
        verbose_name_plural = 'Ustawienia kontroli elektryka'

    def __str__(self):
        return 'Ustawienia kontroli elektryka'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
