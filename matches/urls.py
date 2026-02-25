from django.urls import path
from . import views

app_name = 'matches'

urlpatterns = [
    path('search/', views.GlobalSearchView.as_view(), name='global_search'),
    path('', views.HomeView.as_view(), name='home'),
    path('league/<int:pk>/', views.LeagueDetailView.as_view(), name='league_detail'),
    path('match/<int:pk>/<slug:slug>/', views.MatchDetailView.as_view(), name='match_detail'),
    path('match/<int:pk>/', views.MatchDetailView.as_view(), name='match_detail_short'),
    path('team/<int:pk>/', views.TeamDetailView.as_view(), name='team_detail'),
    # Rota genérica para Liga OU País (resolvido na View)
    # Mantemos múltiplos nomes para suportar 'reverse' nos templates existentes
    path('stats/<str:slug>/', views.LeagueDetailView.as_view(), name='country_stats'),
    path('stats/<str:league_name>/', views.LeagueDetailView.as_view(), name='league_stats'),
    
    # Rota específica para Gols (deve vir ANTES do Dispatcher genérico)
    path('stats/<str:league_name>/goals/', views.LeagueGoalsView.as_view(), name='league_goals'),

    # Alias para reverse url compatibility
    # O primeiro pattern captura a requisição (DispatchView recebe arg1, arg2)
    path('stats/<str:arg1>/<str:arg2>/', views.StatsDispatchView.as_view(), name='stats_dispatch'),
    
    # Estes patterns servem apenas para o 'reverse' (url template tag) funcionar com nomes de parâmetros antigos
    path('stats/<str:country_name>/<str:league_name>/', views.StatsDispatchView.as_view(), name='country_league_stats'),
    path('stats/<str:league_name>/<str:team_name>/', views.StatsDispatchView.as_view(), name='team_stats'),
    
    # Mantendo aliases nomeados para 'reverse' funcionar, mas apontando para o Dispatcher ou Views diretas se preferir
    # O ideal é que o reverse use nomes específicos.
    # Mas como o Dispatcher resolve dinamicamente, podemos manter os 'names' apontando para ele também se quisermos,
    # ou deixar rotas específicas abaixo se o Django permitir (mas regex igual conflita).
    # Então, removemos as rotas conflitantes e deixamos o Dispatcher assumir.
    
    path('stats/<str:league_name>/h2h/<str:team1_name>/<str:team2_name>/', views.HeadToHeadView.as_view(), name='h2h_detail'),
    # path('live/', views.LiveMatchesView.as_view(), name='live_matches'), # REMOVED per user request
    path('debug-leagues/', views.debug_leagues_wrapper, name='debug_leagues'),
]