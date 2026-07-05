from django.urls import path
from . import views

app_name = 'widget_api'

urlpatterns = [
    path('standings/brasileirao/', views.widget_brasileirao_view, name='brasileirao_standings'),
    path('standings/<slug:country>/<slug:league>/', views.widget_league_view, name='league_standings'),
    path('matches/<slug:country>/<slug:league>/', views.widget_upcoming_matches_view, name='league_upcoming_matches'),
]
