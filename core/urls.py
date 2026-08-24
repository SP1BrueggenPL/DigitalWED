from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import user_admin_views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.chip_login_step1, name='login'),
    path('login/kod/', views.chip_login_step2, name='login_kod'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('zmien-haslo/', views.zmien_haslo, name='zmien_haslo'),
    path('uzytkownicy/', user_admin_views.user_list, name='user_list'),
    path('uzytkownicy/nowy/', user_admin_views.user_create, name='user_create'),
    path('uzytkownicy/<int:pk>/edytuj/', user_admin_views.user_edit, name='user_edit'),
    path('uzytkownicy/<int:pk>/haslo/', user_admin_views.user_password, name='user_password'),
    path('klastry/nowy/', user_admin_views.klaster_create, name='klaster_create'),
    path('klastry/<int:pk>/edytuj/', user_admin_views.klaster_edit, name='klaster_edit'),
    path('klastry/<int:pk>/usun/', user_admin_views.klaster_delete, name='klaster_delete'),
]
