from django.urls import path
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView
from . import views

app_name = 'matches'

urlpatterns = [
    path('robots.txt', views.RobotsView.as_view(), name='robots_txt'),
    path('sitemap.xml', views.SitemapView.as_view(), name='sitemap_xml'),
    path('ads.txt', TemplateView.as_view(template_name='matches/ads.txt', content_type='text/plain'), name='ads_txt'),
    
    path('privacy-policy/', TemplateView.as_view(template_name='matches/privacy_policy.html'), name='privacy_policy'),
    path('terms-of-use/', TemplateView.as_view(template_name='matches/terms_of_use.html'), name='terms_of_use'),
    path('about-us/', TemplateView.as_view(template_name='matches/about_us.html'), name='about_us'),
    path('calculadora-under/', TemplateView.as_view(template_name='matches/under_calculator.html'), name='under_calculator'),
    path('contact-us/', views.ContactView.as_view(), name='contact_us'),

    path('search/', views.GlobalSearchView.as_view(), name='global_search'),
    
    
    # Cache de 5 minutos foi removido das Views inteiras porque quebra o CSRF token do seletor de idioma.
    path('', views.HomeView.as_view(), name='home'),
    path('league/<int:pk>/', views.LeagueDetailView.as_view(), name='league_detail'),
    
    path('match/<int:pk>/video-script/', views.MatchVideoScriptView.as_view(), name='match_video_script'),
    path('api/match-video-script/status/<str:task_id>/', views.MatchVideoScriptStatusView.as_view(), name='match_video_script_status'),
    path('match/<int:pk>/<slug:slug>/', views.MatchDetailView.as_view(), name='match_detail'),
    path('match/<int:pk>/', views.MatchDetailView.as_view(), name='match_detail_short'),
    path('team/<int:pk>/', views.TeamDetailView.as_view(), name='team_detail'),
    
    # Rota genérica para Liga OU País (resolvido na View)
    path('stats/<str:slug>/', views.LeagueDetailView.as_view(), name='country_stats'),
    path('stats/<str:league_name>/', views.LeagueDetailView.as_view(), name='league_stats'),
    
    # Rota específica para Gols (deve vir ANTES do Dispatcher genérico)
    path('stats/<str:country_name>/<str:league_name>/goals/', views.LeagueGoalsView.as_view(), name='league_goals'),
    path('stats/<str:country_name>/<str:league_name>/detailed/', views.LeagueDetailedStatsView.as_view(), name='league_detailed'),

    # Alias para reverse url compatibility
    # O primeiro pattern captura a requisição (DispatchView recebe arg1, arg2)
    path('stats/<str:arg1>/<str:arg2>/', views.StatsDispatchView.as_view(), name='stats_dispatch'),
    
    # 3-segment paths for explicit disambiguation
    path('stats/<str:country_name>/<str:league_name>/<str:team_name>/', views.TeamDetailView.as_view(), name='team_stats_full'),
    path('stats/<str:country_name>/<str:league_name>/', views.LeagueDetailView.as_view(), name='league_stats_full'),

    # Estes patterns servem apenas para o 'reverse' (url template tag) funcionar com nomes de parâmetros antigos
    path('stats/<str:country_name>/<str:league_name>/', views.StatsDispatchView.as_view(), name='country_league_stats'),
    path('stats/<str:league_name>/<str:team_name>/', views.StatsDispatchView.as_view(), name='team_stats'),

    
    # Mantendo aliases nomeados para 'reverse' funcionar, mas apontando para o Dispatcher ou Views diretas se preferir
    # O ideal é que o reverse use nomes específicos.
    # Mas como o Dispatcher resolve dinamicamente, podemos manter os 'names' apontando para ele também se quisermos,
    # ou deixar rotas específicas abaixo se o Django permitir (mas regex igual conflita).
    # Então, removemos as rotas conflitantes e deixamos o Dispatcher assumir.
    
    path('stats/<str:country_name>/<str:league_name>/h2h/<str:team1_name>/<str:team2_name>/', views.HeadToHeadView.as_view(), name='h2h_detail'),
    path('live/', views.LiveMatchesView.as_view(), name='live_matches'),
    path('live-radar/<int:match_id>/', views.live_radar_partial, name='live_radar_partial'),
    path('debug-leagues/', views.debug_leagues_wrapper, name='debug_leagues'),
    
    # Novas rotas da Integração Paralela com o Kaggle GPU (Locução de Voz)
    path('api/update-voice-api/', views.KaggleUpdateUrlView.as_view(), name='kaggle_update_voice_api'),
    path('api/generate-match-audio/<int:match_id>/', views.KaggleGenerateVoiceView.as_view(), name='kaggle_generate_voice'),
    path('api/generate-match-audio/status/<str:task_id>/', views.KaggleVoiceStatusView.as_view(), name='kaggle_voice_status'),
]