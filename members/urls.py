from django.urls import path
from . import views

app_name = 'members'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('premium/', views.premium_dashboard, name='premium_dashboard'),
    path('plans/', views.paywall_view, name='paywall'),
]
