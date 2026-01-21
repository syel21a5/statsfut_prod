from django.urls import path
from . import views

app_name = 'matches'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('league/<int:pk>/', views.LeagueDetailView.as_view(), name='league_detail'),
    path('match/<int:pk>/', views.MatchDetailView.as_view(), name='match_detail'),
    path('team/<int:pk>/', views.TeamDetailView.as_view(), name='team_detail'),
    path('stats/<str:league_name>/', views.LeagueDetailView.as_view(), name='league_stats'),
    path('stats/<str:league_name>/<str:team_name>/', views.TeamDetailView.as_view(), name='team_stats'),
    path('live/', views.LiveMatchesView.as_view(), name='live_matches'),
]
