from django.urls import path
from . import views

app_name = 'kotlownia'

urlpatterns = [
    path('', views.formularz_list, name='list'),
    path('nowy/', views.etap_techniczny, name='new'),
    path('<int:pk>/', views.formularz_detail, name='detail'),
    path('<int:pk>/etap1/', views.etap_techniczny, name='etap1'),
    path('<int:pk>/etap2/', views.etap_laboratorium, name='etap2'),
    path('<int:pk>/drukuj/', views.formularz_print, name='print'),
    path('<int:pk>/pobierz/', views.formularz_pdf, name='pdf'),
    path('powiadomienia/', views.powiadomienia_list, name='powiadomienia'),
]
