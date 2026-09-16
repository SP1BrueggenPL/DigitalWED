from django.urls import path
from . import views

app_name = 'inspekcja'

urlpatterns = [
    # Zmiany
    path('zmiany/', views.zmiana_list, name='zmiana_list'),
    path('zmiany/nowa/', views.zmiana_create, name='zmiana_create'),
    path('zmiany/<int:pk>/edytuj/', views.zmiana_edit, name='zmiana_edit'),
    path('zmiany/<int:pk>/osoby/', views.zmiana_osoby_api, name='zmiana_osoby_api'),

    # Inspekcje
    path('', views.inspekcja_list, name='list'),
    path('nowa/', views.inspekcja_create, name='create'),
    path('<int:pk>/', views.inspekcja_detail, name='detail'),
    path('<int:pk>/ukryj/', views.inspekcja_toggle_ukryj, name='toggle_ukryj'),

    # AI
    path('wynik/<int:wynik_pk>/ai/', views.ai_analizuj_zdjecie, name='ai_analizuj'),
]
