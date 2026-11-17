from django.urls import path

from .views import (
    AccountView,
    GamesView,
    HealthView,
    LoginView,
    LogoutView,
    MeView,
    RecordsView,
    RegisterView,
)

urlpatterns = [
    path('api/health', HealthView.as_view(), name='health'),
    path('api/register', RegisterView.as_view(), name='register'),
    path('api/login', LoginView.as_view(), name='login'),
    path('api/me', MeView.as_view(), name='me'),
    path('api/logout', LogoutView.as_view(), name='logout'),
    path('api/account', AccountView.as_view(), name='account'),
    path('api/games', GamesView.as_view(), name='games'),
    path('api/records', RecordsView.as_view(), name='records'),
]
