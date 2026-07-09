from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import user_admin_views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
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
