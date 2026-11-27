from django.urls import path
from . import views

app_name = 'elektryk'

urlpatterns = [
    path('', views.formularz, name='form'),
    path('wyslij/', views.wyslij, name='submit'),
    path('rejestr/', views.rejestr, name='rejestr'),
    path('rejestr/<int:pk>/usun/', views.usun, name='delete'),
    path('ustawienia/', views.ustawienia, name='ustawienia'),
]
