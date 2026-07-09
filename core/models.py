from django.db import models
from django.contrib.auth.models import User, Group


class Klaster(models.Model):
    nazwa = models.CharField(max_length=100, unique=True, verbose_name='Nazwa klastra')
    opis = models.TextField(blank=True, verbose_name='Opis')
    grupy = models.ManyToManyField(Group, blank=True, verbose_name='Role w klastrze')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Klaster'
        verbose_name_plural = 'Klastry'
        ordering = ['nazwa']

    def __str__(self):
        return self.nazwa


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    must_change_password = models.BooleanField(default=False)

    def __str__(self):
        return f'Profil: {self.user.username}'


class Powiadomienie(models.Model):
    odbiorca = models.ForeignKey(User, on_delete=models.CASCADE, related_name='powiadomienia')
    tytul = models.CharField(max_length=200)
    tresc = models.TextField(blank=True)
    url = models.CharField(max_length=500, blank=True)
    przeczytane = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.odbiorca} – {self.tytul}'
