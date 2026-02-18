from django.views.generic import ListView, DetailView, TemplateView, View
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import slugify
from django.http import JsonResponse
from django.db.models import Q
from datetime import datetime, timedelta
from .models import Match, League, Team, Season, LeagueStanding, Goal
from django.db import models
from matches.utils import COUNTRY_REVERSE_TRANSLATIONS

from .api_manager import APIManager
import json


FINISHED_STATUSES = ['Finished', 'FT', 'AET', 'PEN', 'FINISHED']


from django.http import HttpResponse


class GlobalSearchView(View):
    def get(self, request):
        query = request.GET.get('q', '')
        results = []
        
        from matches.utils import COUNTRY_TRANSLATIONS

        if len(query) >= 2:
            # Search Leagues
            leagues = League.objects.filter(name__icontains=query)[:5]
            for league in leagues:
                # Use stats_dispatch compatible URL with English Country
                country_en = COUNTRY_TRANSLATIONS.get(league.country, league.country)
                url = f"/stats/{slugify(country_en)}/{slugify(league.name)}/"
                
                results.append({
                    'type': 'League',
                    'name': f"{league.name} ({country_en})",
                    'url': url,
                    'icon': 'fa-trophy'
                })
                
            # Search Teams
            teams = Team.objects.filter(name__icontains=query).select_related('league')[:5]
            for team in teams:
                # Use stats_dispatch compatible URL (League/Team)
                country_en = COUNTRY_TRANSLATIONS.get(team.league.country, team.league.country)
                url = f"/stats/{slugify(team.league.name)}/{slugify(team.name)}/"
                results.append({
                    'type': 'Team',
                    'name': f"{team.name} ({country_en})",
                    'url': url,
                    'icon': 'fa-shirt'
                })
                
        return JsonResponse({'results': results})

def debug_leagues(request):
    try:
        from .models import League, Team, Match, Season, LeagueStanding
        from django.conf import settings
        import os
        
        # Helper to safely get DB info
        db_settings = settings.DATABASES['default']
        db_info = {
            'ENGINE': db_settings.get('ENGINE'),
            'NAME': db_settings.get('NAME'),
            'USER': db_settings.get('USER'),
            'HOST': db_settings.get('HOST'),
            'PORT': db_settings.get('PORT'),
        }

        # Seeding Logic triggered by button
        if request.method == "POST" and request.POST.get('action') == 'seed':
            
            # 1. Create Season
            season_2025, _ = Season.objects.get_or_create(year=2025)

            # 2. Create Leagues
            premier, _ = League.objects.get_or_create(name="Premier League", country="Inglaterra")
            brasileirao, _ = League.objects.get_or_create(name="Brasileirao", country="Brasil")
            la_liga, _ = League.objects.get_or_create(name="La Liga", country="Espanha")
            serie_a, _ = League.objects.get_or_create(name="Serie A", country="Italia")
            bundesliga, _ = League.objects.get_or_create(name="Bundesliga", country="Alemanha")
            ligue_1, _ = League.objects.get_or_create(name="Ligue 1", country="Franca")
            
            # Other European Leagues (Seed)
            League.objects.get_or_create(name="Liga Profesional", country="Argentina")
            League.objects.get_or_create(name="Bundesliga", country="Austria")
            League.objects.get_or_create(name="A League", country="Australia")
            League.objects.get_or_create(name="Pro League", country="Belgica")
            League.objects.get_or_create(name="Super League", country="Suica")
            League.objects.get_or_create(name="First League", country="Republica Tcheca")
            League.objects.get_or_create(name="Superliga", country="Dinamarca")
            League.objects.get_or_create(name="Veikkausliiga", country="Finlandia")
            League.objects.get_or_create(name="Super League", country="Grecia")
            League.objects.get_or_create(name="Eredivisie", country="Holanda")
            League.objects.get_or_create(name="J1 League", country="Japao")
            League.objects.get_or_create(name="Eliteserien", country="Noruega")
            League.objects.get_or_create(name="Ekstraklasa", country="Polonia")
            League.objects.get_or_create(name="Primeira Liga", country="Portugal")
            League.objects.get_or_create(name="Premier League", country="Russia")
            League.objects.get_or_create(name="Allsvenskan", country="Suecia")
            League.objects.get_or_create(name="Super Lig", country="Turquia")
            League.objects.get_or_create(name="Premier League", country="Ucrania")
            
            # 3. Create Teams
            arsenal, _ = Team.objects.get_or_create(name="Arsenal", league=premier)
            city, _ = Team.objects.get_or_create(name="Man City", league=premier)
            liverpool, _ = Team.objects.get_or_create(name="Liverpool", league=premier)
            palmeiras, _ = Team.objects.get_or_create(name="Palmeiras", league=brasileirao)
            flamengo, _ = Team.objects.get_or_create(name="Flamengo", league=brasileirao)
            
            # 4. Create Matches (Future and Past)
            now = timezone.now()
            
            # Future Match (Scheduled)
            Match.objects.get_or_create(
                league=premier, 
                season=season_2025,
                home_team=arsenal, 
                away_team=city, 
                defaults={'date': now + timedelta(days=2), 'status': 'Scheduled'}
            )
            
            # Past Match (Finished)
            m_past, created = Match.objects.get_or_create(
                league=premier, 
                season=season_2025,
                home_team=liverpool, 
                away_team=arsenal, 
                defaults={
                    'date': now - timedelta(days=5), 
                    'status': 'Finished',
                    'home_score': 2,
                    'away_score': 1
                }
            )
            
            # 5. Create Standings (Table)
            # Arsenal
            LeagueStanding.objects.get_or_create(
                league=premier,
                season=season_2025,
                team=arsenal,
                defaults={
                    'position': 2, 'played': 1, 'won': 0, 'drawn': 0, 'lost': 1,
                    'goals_for': 1, 'goals_against': 2, 'points': 0
                }
            )
            # Liverpool
            LeagueStanding.objects.get_or_create(
                league=premier,
                season=season_2025,
                team=liverpool,
                defaults={
                    'position': 1, 'played': 1, 'won': 1, 'drawn': 0, 'lost': 0,
                    'goals_for': 2, 'goals_against': 1, 'points': 3
                }
            )

            return HttpResponse("<h1>Dados Completos Semeados! (Ligas, Times, Jogos, Tabela)</h1><p><a href='/debug-leagues/'>Voltar</a></p>")

        # Display Logic - INSPECTOR MODE
        
        # Counts
        counts = {
            'leagues': League.objects.count(),
            'teams': Team.objects.count(),
            'matches': Match.objects.count(),
            'standings': LeagueStanding.objects.count(),
            'seasons': Season.objects.count(),
        }

        # Samples
        leagues = League.objects.all()[:20]
        teams = Team.objects.all()[:20]
        matches = Match.objects.all().order_by('-date')[:20]
        standings = LeagueStanding.objects.all()[:20]

        html = f"""
        <style>
            body {{ font-family: sans-serif; padding: 20px; line-height: 1.6; }}
            h1, h2 {{ color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            .card {{ background: #f9f9f9; padding: 15px; margin-bottom: 20px; border: 1px solid #ddd; border-radius: 5px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #f2f2f2; }}
            .warning {{ color: red; font-weight: bold; }}
            .success {{ color: green; font-weight: bold; }}
        </style>
        
        <h1>🕵️ Database Inspector (Prova dos Nove)</h1>
        
        <div class="card">
            <h2>🔌 Configuração de Conexão (settings.py)</h2>
            <p>Verifique se estes dados batem com o banco onde você importou os dados reais:</p>
            <ul>
                <li><strong>ENGINE:</strong> {db_info['ENGINE']}</li>
                <li><strong>NAME (Banco):</strong> {db_info['NAME']}</li>
                <li><strong>USER:</strong> {db_info['USER']}</li>
                <li><strong>HOST:</strong> {db_info['HOST']}</li>
                <li><strong>PORT:</strong> {db_info['PORT']}</li>
            </ul>
        </div>

        <div class="card">
            <h2>📊 Estatísticas (Contagem de Registros)</h2>
            <ul>
                <li><strong>Ligas:</strong> {counts['leagues']}</li>
                <li><strong>Times:</strong> {counts['teams']}</li>
                <li><strong>Partidas (Matches):</strong> {counts['matches']}</li>
                <li><strong>Tabela (Standings):</strong> {counts['standings']}</li>
                <li><strong>Temporadas:</strong> {counts['seasons']}</li>
            </ul>
            { "<p class='warning'>⚠️ Se os números estiverem baixos (ex: < 10), o Django NÃO está vendo seus dados reais!</p>" if counts['matches'] < 10 else "<p class='success'>✅ Parece que temos muitos dados! O problema pode ser filtro (ano/season).</p>" }
        </div>

        <h2>Ligas (Primeiras 20)</h2>
        <table>
            <tr><th>ID</th><th>Nome</th><th>Slug (Calculado)</th></tr>
            {''.join(f"<tr><td>{l.id}</td><td>{l.name} ({l.country})</td><td>{l.name.replace(' ', '-').lower()}</td></tr>" for l in leagues)}
        </table>

        <h2>Partidas Recentes (Primeiras 20)</h2>
        <table>
            <tr><th>Data</th><th>Casa</th><th>Fora</th><th>Placar</th><th>Status</th><th>Season</th></tr>
            {''.join(f"<tr><td>{m.date}</td><td>{m.home_team}</td><td>{m.away_team}</td><td>{m.home_score}x{m.away_score}</td><td>{m.status}</td><td>{m.season}</td></tr>" for m in matches)}
        </table>
        
        <div class="card">
             <h3>🔧 Ferramentas</h3>
            <form method="POST">
                <input type="hidden" name="action" value="seed">
                <input type="hidden" name="csrfmiddlewaretoken" value="">
                <button type="submit" style="padding: 10px 20px; background: #666; color: white; font-size: 14px; cursor: pointer;">
                    (Re)Criar Dados de Teste (Seed)
                </button>
                <small>Use apenas se o banco estiver vazio.</small>
            </form>
        </div>
        """
        
        return HttpResponse(html)
    except Exception as e:
        import traceback
        return HttpResponse(f"<h1>Erro Interno (500) - Detalhes:</h1><pre>{traceback.format_exc()}</pre>")

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def debug_leagues_wrapper(request):
    return debug_leagues(request)


class MatchDetailView(DetailView):
    model = Match
    template_name = 'matches/match_detail.html'
    context_object_name = 'match'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        match = self.object
        
        # Se não tem predictions e o jogo não é passado (ou é recente?), busca na API
        if not match.predictions_data:
            # So busca se tiver api_id (salvo pelo scraper)
            if match.api_id:
                print(f"Fetching predictions for match API_ID {match.api_id}...")
                api_manager = APIManager()
                
                try:
                    preds = api_manager.get_predictions(match.api_id)
                    if preds:
                        match.predictions_data = preds[0] # API retorna lista
                        match.save()
                except Exception as e:
                    print(f"Erro ao atualizar predictions: {e}")
            else:
                print(f"Match {match.id} sem API_ID. Ignorando fetch de predictions.")
        
        return context

class HomeView(ListView):

    model = Match
    template_name = 'matches/home.html'
    context_object_name = 'matches'
    
    def get_queryset(self):
        filter_type = self.request.GET.get('filter', 'today')
        now = timezone.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if filter_type == 'tomorrow':
            start_date = start_of_day + timedelta(days=1)
            end_date = start_date + timedelta(days=1)
            return Match.objects.filter(date__range=(start_date, end_date)).order_by('date')
            
        elif filter_type == 'next_round':
            # Próximos 14 dias para garantir
            start_date = start_of_day + timedelta(days=2)
            end_date = start_date + timedelta(days=14)
            return Match.objects.filter(date__range=(start_date, end_date)).order_by('date')
            
        else: # today
            end_date = start_of_day + timedelta(days=1)
            return Match.objects.filter(date__range=(start_of_day, end_date)).order_by('status', 'date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filter_type = self.request.GET.get('filter', 'today')
        context['current_filter'] = filter_type
        
        if filter_type == 'tomorrow':
            context['page_title'] = "Tomorrow's Matches"
        elif filter_type == 'next_round':
            context['page_title'] = 'Next Round'
        else:
            context['page_title'] = "Today\'s Matches"
            
        return context

class LiveMatchesView(ListView):
    model = Match
    template_name = 'matches/live_matches.html'
    context_object_name = 'matches'
    
    def get_queryset(self):
        # Todos os status que indicam jogo ao vivo
        live_statuses = [
            '1H', '2H', 'HT', 'ET', 'P', 'BT', 'LIVE', 'IN_PLAY', 'PAUSED', 
            'INT', 'SUSP', 'BREAK', 'PEN_LIVE'
        ]
        return Match.objects.filter(status__in=live_statuses).select_related('league', 'home_team', 'away_team').order_by('league__name', 'date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        matches = context['matches']
        
        # Agrupar por Liga
        grouped_matches = {}
        for match in matches:
            league_name = match.league.name
            if league_name not in grouped_matches:
                grouped_matches[league_name] = {'league': match.league, 'matches': []}
            grouped_matches[league_name]['matches'].append(match)
            
        context['grouped_matches'] = grouped_matches
        context['page_title'] = 'Live Matches'
        return context

class StatsDispatchView(View):
    """
    Dispatcher para rotas ambíguas /stats/<arg1>/<arg2>/
    Pode ser:
    1. /stats/Country/League/ -> LeagueDetailView
    2. /stats/League/Team/ -> TeamDetailView
    """
    def get(self, request, arg1=None, arg2=None, **kwargs):
        # Fallback para pegar argumentos nomeados se arg1/arg2 não vierem posicionais
        if not arg1:
            arg1 = kwargs.get('country_name') or kwargs.get('league_name')
        
        if not arg2:
            # Se temos country_name, arg2 é league_name
            if kwargs.get('country_name'):
                arg2 = kwargs.get('league_name')
            # Se temos league_name (e não country_name), arg2 é team_name
            elif kwargs.get('league_name'):
                arg2 = kwargs.get('team_name')

        if not arg1 or not arg2:
             from django.http import Http404
             raise Http404("Invalid URL arguments")

        slug1 = arg1.replace('-', ' ')
        slug2 = arg2.replace('-', ' ')

        # 1. Tenta identificar se arg1 é um PAÍS
        # Check Reverse Translation first (English -> DB Name)
        db_country = COUNTRY_REVERSE_TRANSLATIONS.get(slug1.lower(), slug1)
        
        is_country = League.objects.filter(country__iexact=db_country).exists()
        
        # Fallback: Slugify Match (robust against accents/formatting)
        if not is_country:
            from django.utils.text import slugify
            for l in League.objects.values('country').distinct():
                if slugify(l['country']) == arg1:
                    is_country = True
                    break
        
        # Se for país, assume estrutura Country/League
        if is_country:
            if db_country.strip().lower() in ['republica tcheca', 'república tcheca', 'czech republic', 'czechia']:
                from django.http import Http404
                raise Http404("Country disabled")
            view = LeagueDetailView.as_view()
            # Passa kwargs esperados pela LeagueDetailView
            return view(request, country_name=arg1, league_name=arg2)

        # 2. Se não for país, assume que é LIGA e arg2 é TIME
        # Verifica se existe liga com esse nome
        is_league = League.objects.filter(name__icontains=slug1).exists()
        
        if is_league:
            view = TeamDetailView.as_view()
            # Passa kwargs esperados pela TeamDetailView
            return view(request, league_name=arg1, team_name=arg2)
            
        # 3. Se nenhum match óbvio, tenta fallback agressivo
        # Tenta achar o time arg2 em qualquer liga que pareça arg1
        league = League.objects.filter(name__icontains=slug1).first()
        if league:
             team = Team.objects.filter(league=league, name__icontains=slug2).exists()
             if team:
                 view = TeamDetailView.as_view()
                 return view(request, league_name=arg1, team_name=arg2)
        
        # 4. Última tentativa: talvez arg1 seja país e arg2 seja liga, mas o check 'is_country' falhou por case/formatação?
        # Deixa o LeagueDetailView tentar resolver ou dar 404
        view = LeagueDetailView.as_view()
        return view(request, country_name=arg1, league_name=arg2)


def calculate_team_season_stats(team, league, season):
    """
    Helper to calculate comprehensive stats for a team in a season.
    Returns a dict with 'overall', 'home', 'away' and 'last_8' stats.
    """
    # Get all finished matches for the team in the season
    matches = Match.objects.filter(
        league=league,
        season=season,
        status__in=['Finished', 'FT', 'AET', 'PEN', 'FINISHED']
    ).filter(
        models.Q(home_team=team) | models.Q(away_team=team)
    ).order_by('date')

    # Helper to calculate stats for a list of matches
    def calc_stats(match_list, filter_type='all'):
        gp = len(match_list)
        if gp == 0:
            return {
                'gp': 0, 'w': 0, 'd': 0, 'l': 0, 
                'gf': 0, 'ga': 0, 'pts': 0, 'ppg': 0.0,
                'ppg_pct': 0,
                'w_pct': 0, 'd_pct': 0, 'l_pct': 0,
                'gf_avg': 0.0, 'ga_avg': 0.0, 'tg_avg': 0.0,
                'over_25_pct': 0,
                'form': []
            }

        w = 0; d = 0; l = 0; gf = 0; ga = 0; pts = 0
        over_25 = 0
        form = []

        # Sort matches by date descending for form
        sorted_matches = sorted(match_list, key=lambda x: (x.date if x.date else timezone.now(), x.id), reverse=True)

        # Calculate aggregates
        for m in match_list:
            is_home = m.home_team == team
            
            # Skip if filtering by home/away and match doesn't match
            if filter_type == 'home' and not is_home: continue
            if filter_type == 'away' and is_home: continue

            team_score = m.home_score if is_home else m.away_score
            opp_score = m.away_score if is_home else m.home_score
            
            # Handle None
            team_score = team_score or 0
            opp_score = opp_score or 0

            gf += team_score
            ga += opp_score
            
            if team_score > opp_score: 
                w += 1; pts += 3
            elif team_score == opp_score: 
                d += 1; pts += 1
            else: 
                l += 1
            
            if (team_score + opp_score) > 2.5:
                over_25 += 1

        # Calculate Form (Last 4)
        # Note: sorted_matches is already descending
        last_4_matches = sorted_matches[:4]
        for m in last_4_matches:
            is_home = m.home_team == team
            if filter_type == 'home' and not is_home: continue
            if filter_type == 'away' and is_home: continue
            
            ts = m.home_score if is_home else m.away_score
            os = m.away_score if is_home else m.home_score
            ts = ts or 0; os = os or 0
            
            if ts > os: form.append('W')
            elif ts == os: form.append('D')
            else: form.append('L')
        
        # Averages
        ppg = pts / gp
        return {
            'gp': gp, 'w': w, 'd': d, 'l': l,
            'gf': gf, 'ga': ga, 'pts': pts,
            'ppg': round(ppg, 2),
            'ppg_pct': int((ppg / 3) * 100),
            'w_pct': int((w / gp) * 100),
            'd_pct': int((d / gp) * 100),
            'l_pct': int((l / gp) * 100),
            'gf_avg': round(gf / gp, 2),
            'ga_avg': round(ga / gp, 2),
            'tg_avg': round((gf + ga) / gp, 2),
            'over_25_pct': int((over_25 / gp) * 100),
            'form': form
        }

    # Filter lists
    home_matches = [m for m in matches if m.home_team == team]
    away_matches = [m for m in matches if m.away_team == team]
    
    # Last 8 matches (overall)
    # Convert queryset to list and sort
    all_matches_sorted = sorted(matches, key=lambda x: (x.date if x.date else timezone.now(), x.id), reverse=True)
    last_8_matches = all_matches_sorted[:8]

    return {
        'overall': calc_stats(matches),
        'home': calc_stats(home_matches),
        'away': calc_stats(away_matches),
        'last_8': calc_stats(last_8_matches)
    }


class LeagueDetailView(DetailView):
    model = League
    template_name = 'matches/league_dashboard.html'
    context_object_name = 'league'
    
    def get_object(self):
        # Se pk foi passado, usa comportamento padrão
        if 'pk' in self.kwargs:
            return super().get_object()
            
        # Parâmetros da URL
        league_slug = self.kwargs.get('league_name') or self.kwargs.get('slug')
        country_slug = self.kwargs.get('country_name') # Para rota composta (país/liga)
        
        # Base query
        queryset = League.objects.all()

        # CASO 1: Rota com País e Liga explícitos (ex: /stats/brazil/brasileirao/)
        if country_slug and league_slug:
             # Tenta filtrar por país (com fallback)
             country_clean = country_slug.replace('-', ' ')
             
             # Resolve English -> DB Name
             country_clean = COUNTRY_REVERSE_TRANSLATIONS.get(country_clean.lower(), country_clean)
             
             if country_clean.strip().lower() in ['republica tcheca', 'república tcheca', 'czech republic', 'czechia']:
                 from django.http import Http404
                 raise Http404("Country disabled")

             if not queryset.filter(country__iexact=country_clean).exists():
                 # Fallback slugify
                 from django.utils.text import slugify
                 target_country = None
                 for c in queryset.values_list('country', flat=True).distinct():
                     if slugify(c) == country_slug:
                         target_country = c
                         break
                 if target_country:
                     queryset = queryset.filter(country=target_country)
                 else:
                     queryset = queryset.none()
             else:
                 queryset = queryset.filter(country__iexact=country_clean)

             name_query = league_slug.replace('-', ' ')
             league = queryset.filter(name__iexact=name_query).first() or \
                      queryset.filter(name__icontains=name_query).first()
            
             # Fallback League Slugify
             if not league:
                 from django.utils.text import slugify
                 for l in queryset:
                     if slugify(l.name) == league_slug:
                         league = l
                         break

             if league:
                 return league
             from django.http import Http404
             raise Http404(f"League '{league_slug}' not found in {country_slug}")

        # CASO 2: Rota genérica com um slug (ex: /stats/brazil/ OU /stats/premier-league/)
        if league_slug:
            slug_clean = league_slug.replace('-', ' ')
            
            # 2.1 Tenta achar LIGA primeiro
            league = queryset.filter(name__iexact=slug_clean).first() or \
                     queryset.filter(name__icontains=slug_clean).first()
            if league:
                if league.country.strip().lower() in ['republica tcheca', 'república tcheca', 'czech republic', 'czechia']:
                    from django.http import Http404
                    raise Http404("League disabled")
                return league
                
            # 2.2 Se não achou liga, tenta achar PAÍS e retorna a primeira liga dele
            # Tenta tradução reversa primeiro (English Slug -> Portuguese DB Name)
            # Ex: 'czech-republic' -> 'republica tcheca'
            
            # Normaliza o slug: substitui hifens por espaços para buscar no dicionário
            # Ex: 'czech-republic' vira 'czech republic', que bate com a chave do dicionário
            clean_name = slug_clean.replace('-', ' ')
            db_country_name = COUNTRY_REVERSE_TRANSLATIONS.get(clean_name.lower())
            
            if db_country_name:
                candidates = queryset.filter(country__iexact=db_country_name)
            else:
                candidates = queryset.filter(country__iexact=slug_clean)

            if candidates.exists():
                # Prefer league with most standings; if tie/zero, prefer with most upcoming matches
                league = candidates.annotate(s_count=models.Count('standings')).order_by('-s_count').first()
                if league and league.standings.count() > 0:
                    return league
                # Fallback by upcoming scheduled matches in next 30 days
                now = timezone.now()
                future = now + timedelta(days=30)
                candidates_with_counts = []
                for l in candidates:
                    cnt = Match.objects.filter(
                        league=l,
                        date__gte=now,
                        date__lte=future,
                        status__in=['Scheduled', 'Not Started', 'TIMED', 'UTC']
                    ).count()
                    candidates_with_counts.append((cnt, l))
                if candidates_with_counts:
                    candidates_with_counts.sort(key=lambda x: x[0], reverse=True)
                    return candidates_with_counts[0][1]
                
        # Fallback
        from django.http import Http404
        raise Http404(f"No league or country found matching: {league_slug}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        league = self.object
        now = timezone.now()
        
        context['upcoming_matches'] = Match.objects.filter(
            league=league,
            date__gte=now,
            status__in=['Scheduled', 'Not Started', 'TIMED', 'UTC']
        ).order_by('date')[:15]
        
        # Include all statuses that indicate a finished match
        context['latest_results'] = Match.objects.filter(
            league=league,
            status__in=FINISHED_STATUSES,
            date__lte=now
        ).order_by('-date')[:10]
        
        latest_season = league.standings.order_by('-season__year').first().season if league.standings.exists() else None
        context['latest_season'] = latest_season
        
        if latest_season:
            # Fetch all necessary data in bulk to avoid N+1 queries
            standings = list(league.standings.filter(season=latest_season).order_by('position'))
            all_matches = Match.objects.filter(
                league=league,
                season=latest_season,
                status__in=FINISHED_STATUSES,
                # date__lt=today # REMOVED: Allow test data with NULL dates
            ).select_related('home_team', 'away_team')

            # Initialize data structures for Home/Away tables
            from datetime import datetime
            epoch = timezone.make_aware(datetime(1900, 1, 1))
            team_stats = {} # Key: team_id, Value: {home_stats, away_stats}

            # Pre-calculate PPG for all teams for Relative Performance calculation
            team_ppg_map = {}
            for s in standings:
                if s.played > 0:
                    team_ppg_map[s.team.id] = s.points / s.played
                else:
                    team_ppg_map[s.team.id] = 0.0

            for standing in standings:
                team_id = standing.team.id
                team_stats[team_id] = {
                   'team': standing.team,
                   'team_slug': standing.team.name.replace(' ', '-'),
                   'league_slug': league.name.replace(' ', '-'),
                   'home': {'gp': 0, 'w': 0, 'd': 0, 'l': 0, 'gf': 0, 'ga': 0, 'pts': 0},
                   'away': {'gp': 0, 'w': 0, 'd': 0, 'l': 0, 'gf': 0, 'ga': 0, 'pts': 0},
                   'form': [] 
                }
                # Calculate Goal Diff for main table
                standing.goal_diff = standing.goals_for - standing.goals_against
                
                # --- NEW: Slugify names for custom URLs ---
                standing.team_slug = standing.team.name.replace(' ', '-')
                standing.league_slug = league.name.replace(' ', '-') # Assuming league object is available

                # Calculate Form (Last 5 for main table, Last 8 for Form tab)
                team_matches = [m for m in all_matches if m.home_team_id == team_id or m.away_team_id == team_id]
                # Sort by date/id descending - handle missing dates safely with compatible epoch
                team_matches.sort(key=lambda x: (x.date if x.date else epoch, x.id), reverse=True)
                
                # Last 5 for Main Table
                # --- NEW: POPULATE TEAM STATS (Home/Away Tables) ---
                t_stats = team_stats[team_id]
                for m in team_matches:
                    home_score = m.home_score or 0
                    away_score = m.away_score or 0
                    
                    if m.home_team_id == team_id:
                        s = t_stats['home']
                        s['gp'] += 1
                        s['gf'] += home_score
                        s['ga'] += away_score
                        if home_score > away_score: s['w'] += 1; s['pts'] += 3
                        elif home_score == away_score: s['d'] += 1; s['pts'] += 1
                        else: s['l'] += 1
                    else:
                        s = t_stats['away']
                        s['gp'] += 1
                        s['gf'] += away_score
                        s['ga'] += home_score
                        if away_score > home_score: s['w'] += 1; s['pts'] += 3
                        elif away_score == home_score: s['d'] += 1; s['pts'] += 1
                        else: s['l'] += 1

                form_5 = []
                form_details = []  # NEW: Detailed info for tooltips
                for m in team_matches[:5]:
                    # Determine if team was home or away
                    is_home = m.home_team_id == team_id
                    opponent = m.away_team if is_home else m.home_team
                    team_score = m.home_score if is_home else m.away_score
                    opp_score = m.away_score if is_home else m.home_score
                    
                    # Determine result
                    if team_score > opp_score:
                        result = 'W'
                    elif team_score == opp_score:
                        result = 'D'
                    else:
                        result = 'L'
                    
                    form_5.append(result)
                    
                    # Add detailed info
                    form_details.append({
                        'date': m.date.strftime('%d %b') if m.date else '-',
                        'opponent': opponent.name,
                        'score': f"{team_score}-{opp_score}",
                        'result': result,
                        'is_home': is_home
                    })
                
                standing.form_history = form_5
                standing.form_details = form_details  # NEW

                # Last 8 for Relative Form Tab
                form_8 = []
                pts_8 = 0
                for m in team_matches[:8]:
                    result = ''
                    if m.home_team_id == team_id:
                        if m.home_score > m.away_score: result = 'W'; pts_8 += 3
                        elif m.home_score == m.away_score: result = 'D'; pts_8 += 1
                        else: result = 'L'
                    else:
                        if m.away_score > m.home_score: result = 'W'; pts_8 += 3
                        elif m.away_score == m.home_score: result = 'D'; pts_8 += 1
                        else: result = 'L'
                    form_8.append(result)
                
                standing.form_8 = form_8
                standing.pts_8 = pts_8
                standing.ppg_8 = round(pts_8 / 8, 2) if len(team_matches) >= 8 else round(pts_8 / len(team_matches), 2) if team_matches else 0
                standing.ppg_season = round(standing.points / standing.played, 2) if standing.played > 0 else 0
                standing.ppg_diff = round(standing.ppg_8 - standing.ppg_season, 2)
                
                # Relative Form Percentage ((PPG8 - PPG_Season) / PPG_Season)
                if standing.ppg_season > 0:
                    standing.relative_form_pct = round(((standing.ppg_8 - standing.ppg_season) / standing.ppg_season) * 100, 0)
                    standing.relative_form_pct = int(standing.relative_form_pct)
                    # Bar width: 1% = 1.5px approx? Or just pass absolute value for flexible JS/CSS use.
                    # Let's pass a calc valid for 'px' usage.
                    # Using factor 2.0: 10% = 20px. 40% = 80px. 90% = 180px.
                    # Maybe cap at 100px?
                    standing.relative_form_bar_width = min(abs(standing.relative_form_pct) * 2, 120) 
                else:
                    standing.relative_form_pct = 0
                    standing.relative_form_bar_width = 0
                
                # Relative Performance metrics (SoccerStats style)
                # Points Performance Index = Team PPG x Opponents PPG
                
                opponents_ppg_sum = 0
                opponents_count = 0
                
                for m in team_matches:
                    opp_id = m.away_team_id if m.home_team_id == team_id else m.home_team_id
                    if opp_id in team_ppg_map:
                        opponents_ppg_sum += team_ppg_map[opp_id]
                        opponents_count += 1
                
                standing.opponents_ppg = round(opponents_ppg_sum / opponents_count, 2) if opponents_count > 0 else 0
                standing.performance_index = round(standing.ppg_season * standing.opponents_ppg, 2)
                # Calulca a porcentagem para a barra (máximo 4.0 = 100%)
                standing.perf_width_pct = min(round((standing.performance_index / 4.0) * 100, 1), 100) if standing.performance_index > 0 else 0

                # --- Run-in Analysis Logic ---
                # Get all matches for this team (including scheduled)
                team_all_matches = Match.objects.filter(
                    league=league,
                ).filter(models.Q(home_team_id=team_id) | models.Q(away_team_id=team_id)).select_related('home_team', 'away_team')

                played_opp_ppg_sum = 0
                played_count = 0
                remaining_opp_ppg_sum = 0
                remaining_count = 0
                
                # Sort upcoming by date/id
                upcoming_scheduled = []
                
                for m in team_all_matches:
                    opp_id = m.away_team_id if m.home_team_id == team_id else m.home_team_id
                    opp_ppg = team_ppg_map.get(opp_id, 0.0)
                    
                    if m.status == 'Finished':
                        played_opp_ppg_sum += opp_ppg
                        played_count += 1
                    elif m.status == 'Scheduled':
                        remaining_opp_ppg_sum += opp_ppg
                        remaining_count += 1
                        upcoming_scheduled.append({'match': m, 'opp_ppg': opp_ppg})

                # Opponents Played PPG
                standing.opp_played_ppg = round(played_opp_ppg_sum / played_count, 2) if played_count > 0 else 0
                
                # Opponents Remaining PPG
                standing.opp_remaining_ppg = round(remaining_opp_ppg_sum / remaining_count, 2) if remaining_count > 0 else 0
                standing.runin_width_pct = min(round((standing.opp_remaining_ppg / 3.0) * 100, 1), 100) if standing.opp_remaining_ppg > 0 else 0
                
                # Played vs Remaining (%)
                if standing.opp_remaining_ppg > 0:
                    diff_pct = (standing.opp_played_ppg / standing.opp_remaining_ppg - 1) * 100
                    standing.runin_diff_pct = round(diff_pct, 1)
                else:
                    standing.runin_diff_pct = 0
                
                # Next 4 Opponents average - use datetime-compatible epoch for sorting
                upcoming_scheduled.sort(key=lambda x: (x['match'].date if x['match'].date else epoch, x['match'].id))
                next_4 = upcoming_scheduled[:4]
                next_4_sum = sum(item['opp_ppg'] for item in next_4)
                standing.next_4_ppg = round(next_4_sum / len(next_4), 2) if next_4 else 0

                # --- Projected Points Logic ---
                # Ratio = Opponents Remaining PPG / Opponents Played PPG
                if standing.opp_played_ppg > 0:
                    standing.proj_ratio = round(standing.opp_remaining_ppg / standing.opp_played_ppg, 2)
                else:
                    standing.proj_ratio = 1.0
                
                # pPPG = Team PPG x Ratio
                standing.proj_ppg = round(standing.ppg_season * standing.proj_ratio, 2)
                
                # Games Remaining
                standing.games_remaining = 38 - standing.played
                
                # Projected Points = pPPG x Games Remaining
                standing.proj_points = round(standing.proj_ppg * standing.games_remaining, 2)
                
                # Projected Total = Current Points + Projected Points
                standing.proj_total = round(standing.points + standing.proj_points, 2)

                # --- Additional Stats for Main Table ---
                # Clean Sheets (CS): matches where GA = 0
                clean_sheets = sum(1 for m in team_matches if (
                    (m.home_team_id == team_id and m.away_score == 0) or
                    (m.away_team_id == team_id and m.home_score == 0)
                ))
                standing.clean_sheets = clean_sheets
                
                # Scoring Rate (SR): percentage of matches where team scored
                matches_scored = sum(1 for m in team_matches if (
                    (m.home_team_id == team_id and m.home_score > 0) or
                    (m.away_team_id == team_id and m.away_score > 0)
                ))
                standing.scoring_rate = f"{round((matches_scored / len(team_matches) * 100) if team_matches else 0)}%"
                
                # Maximum Possible Points (MPP)
                standing.max_possible_points = standing.points + (38 - standing.played) * 3


            # Calculate table averages
            total_teams = len(standings)
            if total_teams > 0:
                context['avg_played'] = sum(s.played for s in standings) / total_teams
                context['avg_won'] = sum(s.won for s in standings) / total_teams
                context['avg_drawn'] = sum(s.drawn for s in standings) / total_teams
                context['avg_lost'] = sum(s.lost for s in standings) / total_teams
                context['avg_gf'] = sum(s.goals_for for s in standings) / total_teams
                context['avg_ga'] = sum(s.goals_against for s in standings) / total_teams
                context['avg_gd'] = sum(s.goal_diff for s in standings) / total_teams
                context['avg_pts'] = sum(s.points for s in standings) / total_teams
                context['avg_ppg'] = sum(s.ppg_season for s in standings) / total_teams
                context['avg_ppg8'] = sum(s.ppg_8 for s in standings) / total_teams
                context['avg_cs'] = sum(s.clean_sheets for s in standings) / total_teams * 100 / context['avg_played'] if context['avg_played'] > 0 else 0
                # SR average: percentage of teams that scored in their matches
                total_sr = sum(int(s.scoring_rate.rstrip('%')) for s in standings)
                context['avg_sr'] = total_sr / total_teams if total_teams > 0 else 0


            # Prepare sorted lists for context
            home_table = []
            away_table = []
            for tid, data in team_stats.items():
                # Add calculated properties
                h = data['home']
                h['team'] = data['team']
                h['team_slug'] = data['team_slug']
                h['league_slug'] = data['league_slug']
                h['gd'] = h['gf'] - h['ga']
                h['ppg'] = round(h['pts'] / h['gp'], 2) if h['gp'] > 0 else 0
                home_table.append(h)

                a = data['away']
                a['team'] = data['team']
                a['team_slug'] = data['team_slug']
                a['league_slug'] = data['league_slug']
                a['gd'] = a['gf'] - a['ga']
                a['ppg'] = round(a['pts'] / a['gp'], 2) if a['gp'] > 0 else 0
                away_table.append(a)

            # Sort tables (Pts desc, GD desc, GF desc)
            home_table.sort(key=lambda x: (x['pts'], x['gd'], x['gf']), reverse=True)
            away_table.sort(key=lambda x: (x['pts'], x['gd'], x['gf']), reverse=True)

            # Add rank
            for i, row in enumerate(home_table, 1): row['position'] = i
            for i, row in enumerate(away_table, 1): row['position'] = i

            rf_override = None
            rp_override = None
            ri_override = None
            pp_override = None
            try:
                if league.name == 'First League' and league.country == 'Republica Tcheca':
                    relative_table_override = None
                    import requests as _rq
                    from bs4 import BeautifulSoup as _BS
                    import pandas as _pd
                    def _to_int(s):
                        try:
                            s = str(s).strip().replace('+', '').replace('–', '-').replace('—', '-').replace('−', '-')
                            s = ''.join(ch for ch in s if ch.isdigit() or ch in {'-', '+'})
                            if s in {'', '-'}: return None
                            return int(s)
                        except: 
                            return None
                    def _parse_table_el(tbl):
                        rows2 = []
                        for tr in tbl.find_all('tr'):
                            cells = [c.get_text(strip=True) for c in tr.find_all(['td','th'])]
                            if len(cells) < 8: 
                                continue
                            # Expect: [#, Team, GP, W, D, L, GF, GA, GD, Pts, ...]
                            try:
                                team_name = cells[1]
                                gp = _to_int(cells[2]); w = _to_int(cells[3]); d = _to_int(cells[4]); l = _to_int(cells[5])
                                gf = _to_int(cells[6]); ga = _to_int(cells[7])
                                # GD may be cells[8], Pts cells[9]
                                pts = None
                                if len(cells) > 9:
                                    pts = _to_int(cells[9])
                                if pts is None and len(cells) > 8:
                                    pts = _to_int(cells[8])
                                if gp is None or w is None or d is None or l is None or gf is None or ga is None or pts is None:
                                    continue
                                team = Team.objects.filter(name=team_name, league=league).first()
                                if not team:
                                    team = Team.objects.create(name=team_name, league=league)
                                item = {
                                    'team': team,
                                    'team_slug': team.name.lower().replace(' ', '-'),
                                    'league_slug': league.name.lower().replace(' ', '-'),
                                    'gp': gp, 'w': w, 'd': d, 'l': l, 'gf': gf, 'ga': ga,
                                    'gd': (gf - ga), 'pts': pts, 'ppg': round(pts/gp, 2) if gp else 0
                                }
                                rows2.append(item)
                            except:
                                continue
                        rows2 = [r for r in rows2 if r['gp'] is not None and 0 <= r['gp'] <= 60]
                        rows2.sort(key=lambda x:(x['pts'], x['gd'], x['gf']), reverse=True)
                        for i, it in enumerate(rows2, 1): it['position'] = i
                        return rows2
                    def _extract_rows(df):
                        out = []
                        for _, r in df.iterrows():
                            cells = [str(x).strip() for x in r.values.tolist()]
                            t_idx = None
                            for i, c in enumerate(cells):
                                if c and any(ch.isalpha() for ch in c) and c.lower() not in {'team','teams','#','average','avg'}:
                                    t_idx = i
                                    break
                            if t_idx is None: 
                                continue
                            nums = []
                            for c in cells[t_idx+1:]:
                                v = _to_int(c)
                                if v is not None: nums.append(v)
                            if len(nums) < 8: 
                                continue
                            gp,w,d,l,gf,ga = nums[0],nums[1],nums[2],nums[3],nums[4],nums[5]
                            pts = nums[7] if len(nums) >= 8 else nums[6]
                            if not (0 <= gp <= 60 and 0 <= w <= 60 and 0 <= d <= 60 and 0 <= l <= 60): 
                                continue
                            out.append((cells[t_idx], gp, w, d, l, gf, ga, pts))
                        return out
                    url = "https://www.soccerstats.com/latest.asp?league=czechrepublic"
                    r = _rq.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
                    if r.status_code == 200:
                        soup = _BS(r.text, 'html.parser')
                        home_el = None
                        away_el = None
                        for node in soup.find_all(text=True):
                            if isinstance(node, str):
                                t = node.strip().lower()
                                if t == 'home table' and home_el is None:
                                    home_el = node.parent.find_next('table')
                                elif t == 'away table' and away_el is None:
                                    away_el = node.parent.find_next('table')
                            if home_el is not None and away_el is not None:
                                break
                        parsed_home = _parse_table_el(home_el) if home_el else []
                        parsed_away = _parse_table_el(away_el) if away_el else []
                        if parsed_home and parsed_away:
                            home_table = parsed_home
                            away_table = parsed_away
                        else:
                            tables = _pd.read_html(r.text)
                            home_away_candidates = []
                            for t in tables:
                                rows = _extract_rows(t)
                                if not rows or len(rows) < 8:
                                    continue
                                avg_gp = sum(r[1] for r in rows) / len(rows)
                                if 9 <= avg_gp <= 13:
                                    home_away_candidates.append(rows)
                            if len(home_away_candidates) >= 2:
                                def _build(rows):
                                    rows2 = []
                                    for team_name, gp, w, d, l, gf, ga, pts in rows:
                                        team = Team.objects.filter(name=team_name, league=league).first()
                                        if not team:
                                            team = Team.objects.create(name=team_name, league=league)
                                        item = {
                                            'team': team,
                                            'team_slug': team.name.lower().replace(' ', '-'),
                                            'league_slug': league.name.lower().replace(' ', '-'),
                                            'gp': gp, 'w': w, 'd': d, 'l': l, 'gf': gf, 'ga': ga,
                                            'gd': gf - ga, 'pts': pts, 'ppg': round(pts/gp, 2) if gp else 0
                                        }
                                        rows2.append(item)
                                    rows2.sort(key=lambda x:(x['pts'], x['gd'], x['gf']), reverse=True)
                                    for i, it in enumerate(rows2, 1): it['position'] = i
                                    return rows2
                                built1 = _build(home_away_candidates[0])
                                built2 = _build(home_away_candidates[1])
                                home_table = built1
                                away_table = built2
                            home_idx = {r['team']: r for r in home_table}
                            away_idx = {r['team']: r for r in away_table}
                            rel_rows = []
                            for t in set(home_idx.keys()) & set(away_idx.keys()):
                                h = home_idx[t]
                                a = away_idx[t]
                                total_pts = h['pts'] + a['pts']
                                total_gp = h['gp'] + a['gp']
                                total_ppg = (total_pts / total_gp) if total_gp > 0 else 0
                                ppg_home = h['ppg']
                                ppg_away = a['ppg']
                                rel_rows.append({
                                    'team': h['team'],
                                    'team_slug': h['team_slug'],
                                    'league_slug': h['league_slug'],
                                    'gph': h['gp'],
                                    'gpa': a['gp'],
                                    'pts': total_pts,
                                    'ppg_home': ppg_home,
                                    'ppg_away': ppg_away,
                                    'ppg_diff': round(ppg_home - ppg_away, 2),
                                    'home_rel': round(((ppg_home - total_ppg)/total_ppg * 100), 1) if total_ppg > 0 else 0,
                                    'away_rel': round(((ppg_away - total_ppg)/total_ppg * 100), 1) if total_ppg > 0 else 0,
                                    'bar_width': min(int(abs(ppg_home - ppg_away) * 40), 100),
                                    'ppg_diff_abs': abs(round(ppg_home - ppg_away, 2))
                                })
                            rel_rows.sort(key=lambda x: (x['pts'], x['ppg_diff']), reverse=True)
                            for i, r in enumerate(rel_rows, 1):
                                r['position'] = i
                            relative_table_override = rel_rows
                        
                        def _clean_float(s):
                            try:
                                s = str(s).strip().replace(',', '.')
                                keep = ''.join(ch for ch in s if (ch.isdigit() or ch in {'.','-','+'}))
                                if keep in {'', '-', '+', '.', '+.', '-.'}: return None
                                return float(keep)
                            except:
                                return None
                        def _table_has_keywords(tbl, keywords):
                            txt = []
                            for th in tbl.find_all('th'):
                                txt.append(th.get_text(' ', strip=True))
                            # Also sample first 3 rows for context
                            for tr in tbl.find_all('tr')[:3]:
                                txt.extend(td.get_text(' ', strip=True) for td in tr.find_all(['td','th']))
                            blob = ' '.join(txt).lower()
                            return all(k in blob for k in keywords)
                        def _find_table_by_keywords(keyword_sets):
                            tables = soup.find_all('table')
                            for kws in keyword_sets:
                                for tbl in tables:
                                    try:
                                        if _table_has_keywords(tbl, kws):
                                            return tbl
                                    except Exception:
                                        continue
                            return None
                        def _find_table_by_label(labels):
                            for node in soup.find_all(text=True):
                                try:
                                    t = node.strip().lower()
                                except:
                                    continue
                                for lbl in labels:
                                    if lbl.lower() in t:
                                        el = node.parent.find_next('table')
                                        if el:
                                            return el
                            return None
                        def _is_runin_table(tbl):
                            txt = []
                            for th in tbl.find_all('th'):
                                txt.append(th.get_text(' ', strip=True).lower())
                            blob = ' '.join(txt)
                            bad = ['run-in', 'remaining', 'next 4', 'played']
                            return any(b in blob for b in bad)
                        def _parse_rows_float(tbl, min_cols=4):
                            out = []
                            if not tbl: return out
                            for tr in tbl.find_all('tr'):
                                tds = tr.find_all(['td','th'])
                                cells = [td.get_text(strip=True) for td in tds]
                                if len(cells) < min_cols: 
                                    continue
                                name = None
                                name_idx = None
                                for c in cells:
                                    if c and any(ch.isalpha() for ch in c):
                                        if c.lower() in {'team', 'teams', '#', 'avg', 'average'}:
                                            continue
                                        name = c
                                        name_idx = cells.index(c)
                                        break
                                if not name:
                                    continue
                                nums = []
                                # Considere apenas o que vem DEPOIS do nome do time (evita pegar posição/rank)
                                for c in cells[name_idx+1:]:
                                    if c == name: 
                                        continue
                                    v = _clean_float(c)
                                    if v is not None:
                                        nums.append(v)
                                if not nums:
                                    continue
                                out.append((name, nums))
                            return out
                        rf_tbl = _find_table_by_keywords([
                            ['relative form','last 8','all'],
                            ['relative form','points per game'],
                        ])
                        # Prefer exact “Points Performance Index” label if present
                        rp_tbl = _find_table_by_label([
                            'Points Performance Index',
                            'Relative Performance'
                        ])
                        if rp_tbl is None:
                            rp_tbl = _find_table_by_keywords([
                            ['relative performance','opponents ppg'],
                            ['points performance index','opponents ppg'],
                        ])
                        if rp_tbl is not None and _is_runin_table(rp_tbl):
                            rp_tbl = None
                            for tbl in soup.find_all('table'):
                                if _table_has_keywords(tbl, ['opponents ppg']) and not _is_runin_table(tbl):
                                    rp_tbl = tbl
                                    break
                        ri_tbl = _find_table_by_keywords([
                            ['run-in','opponents played ppg','opponents remaining ppg'],
                            ['run-in','remaining ppg'],
                        ])
                        pp_tbl = _find_table_by_keywords([
                            ['projected points','ratio','pppg'],
                            ['projected points','projected ppg','ratio'],
                        ])
                        rf_rows = _parse_rows_float(rf_tbl)
                        rp_rows = _parse_rows_float(rp_tbl)
                        ri_rows = _parse_rows_float(ri_tbl)
                        pp_rows = _parse_rows_float(pp_tbl)
                        rf_map = {}
                        for name, nums in rf_rows:
                            # Heurística: PPGs estão tipicamente <= 3.0; pegar dois primeiros nessa faixa
                            ppg_values = [x for x in nums if 0 <= x <= 3.5]
                            if len(ppg_values) >= 2:
                                last8_ppg = ppg_values[0]
                                season_ppg = ppg_values[1]
                                rf_map[name] = {'ppg_season': round(season_ppg,2), 'ppg_8': round(last8_ppg,2), 'ppg_diff': round(last8_ppg - season_ppg,2)}
                        rp_map = {}
                        for name, nums in rp_rows:
                            # Esperado: Team PPG, Opp PPG, Index
                            # Filtrar valores plausíveis
                            clean = [x for x in nums if -0.5 <= x <= 5.0]
                            if len(clean) >= 3:
                                team_ppg = clean[0]
                                opp_ppg = clean[1]
                                idx = team_ppg * opp_ppg
                                rp_map[name] = {'opponents_ppg': round(opp_ppg,2), 'performance_index': round(idx,2), 'ppg_season': round(team_ppg,2)}
                        ri_map = {}
                        for name, nums in ri_rows:
                            # Esperado: Team PPG, Opp played PPG, Opp remaining PPG, Diff%, Next4 PPG
                            # Pegamos os dois primeiros PPGs >0 e <=3.5 após o primeiro valor (team ppg)
                            ppgs = [x for x in nums if 0 <= x <= 3.5]
                            played_ppg = ppgs[1] if len(ppgs) > 1 else None
                            remain_ppg = ppgs[2] if len(ppgs) > 2 else None
                            # Diff% é um valor percentual; vamos buscar um número fora da faixa ppg (ex.: abs>3.5) mais próximo
                            diff_candidates = [x for x in nums if abs(x) > 3.5 and abs(x) < 200]
                            diff_pct = diff_candidates[0] if diff_candidates else 0
                            next4 = ppgs[3] if len(ppgs) > 3 else None
                            ri_map[name] = {
                                'opp_played_ppg': round(played_ppg,2) if played_ppg is not None else 0,
                                'opp_remaining_ppg': round(remain_ppg,2) if remain_ppg is not None else 0,
                                'runin_diff_pct': round(diff_pct,1) if diff_pct is not None else 0,
                                'next_4_ppg': round(next4,2) if next4 is not None else None
                            }
                        pp_map = {}
                        for name, nums in pp_rows:
                            # Esperado: ... Ratio, pPPG, Total (além de GP/Pts/GR etc.)
                            # Heurística: capturar primeiro valor de razão (0.3..1.5), depois pPPG (0..3.5), depois total (>=20)
                            ratio = None; proj_ppg = None; total = None
                            for x in nums:
                                if ratio is None and 0.3 <= x <= 1.5:
                                    ratio = x; continue
                                if proj_ppg is None and 0 <= x <= 3.5:
                                    proj_ppg = x; continue
                            # Para TOTAL, use o último número grande (evita confundir com GP/Pts no início)
                            for x in reversed(nums):
                                if x >= 20:
                                    total = x
                                    break
                            if ratio is not None and proj_ppg is not None and total is not None:
                                pp_map[name] = {
                                    'proj_ratio': round(ratio,2),
                                    'proj_ppg': round(proj_ppg,2),
                                    'proj_total': round(total,0)
                                }
                        rf_override = rf_map if rf_map else None
                        rp_override = rp_map if rp_map else None
                        ri_override = ri_map if ri_map else None
                        pp_override = pp_map if pp_map else None
            except:
                pass

            # --- LEAGUE WIDE STATS (New Cards) ---
            total_matches_played = len(all_matches)
            if total_matches_played > 0:
                total_goals = sum((m.home_score or 0) + (m.away_score or 0) for m in all_matches)
                btts_count = sum(1 for m in all_matches if (m.home_score or 0) > 0 and (m.away_score or 0) > 0)
                over15_count = sum(1 for m in all_matches if ((m.home_score or 0) + (m.away_score or 0)) > 1.5)
                over25_count = sum(1 for m in all_matches if ((m.home_score or 0) + (m.away_score or 0)) > 2.5)
                home_wins = sum(1 for m in all_matches if (m.home_score or 0) > (m.away_score or 0))
                draws = sum(1 for m in all_matches if (m.home_score or 0) == (m.away_score or 0))
                away_wins = sum(1 for m in all_matches if (m.away_score or 0) > (m.home_score or 0))
                
                context['league_stats'] = {
                    'avg_goals_match': round(total_goals / total_matches_played, 2),
                    'btts_pct': round((btts_count / total_matches_played) * 100, 1),
                    'over15_pct': round((over15_count / total_matches_played) * 100, 1),
                    'over25_pct': round((over25_count / total_matches_played) * 100, 1),
                    'home_win_pct': round((home_wins / total_matches_played) * 100, 1),
                    'draw_pct': round((draws / total_matches_played) * 100, 1),
                    'away_win_pct': round((away_wins / total_matches_played) * 100, 1),
                }
                
                # Common Scores
                from collections import Counter
                scores = [f"{m.home_score}-{m.away_score}" for m in all_matches]
                common_scores = Counter(scores).most_common(5)
                context['common_scores'] = [{'score': s, 'count': c, 'pct': round(c/total_matches_played*100, 1)} for s, c in common_scores]
            else:
                context['league_stats'] = {}
                context['common_scores'] = []

            context['standings'] = standings
            context['home_table'] = home_table
            context['away_table'] = away_table
            
            # Get upcoming matches_qs (Moved up for Pre-Match Analysis)
            # Limit to next 10 matches (approx 1 round) to avoid overcrowding the dashboard
            upcoming_matches_qs = Match.objects.filter(
                league=league,
                status__in=['Scheduled', 'Not Started'],
                date__gte=timezone.now()
            ).select_related('home_team', 'away_team').order_by('date')[:10]

            # --- PRE-MATCH ANALYSIS STATS ---
            pre_match_data = []
            for m in upcoming_matches_qs:
                h_stats = calculate_team_season_stats(m.home_team, league, latest_season)
                a_stats = calculate_team_season_stats(m.away_team, league, latest_season)
                if h_stats and a_stats:
                    pre_match_data.append({
                        'match': m,
                        'home': h_stats,
                        'away': a_stats
                    })
            context['pre_match_analysis'] = pre_match_data
            
            # Relative Home/Away Performance Table
            relative_table = []
            if 'relative_table_override' in locals() and relative_table_override:
                relative_table = relative_table_override
            else:
                for tid, data in team_stats.items():
                    row = {}
                    row['team'] = data['team']
                    row['team_slug'] = data['team_slug']
                    row['league_slug'] = data['league_slug']
                    
                    h = data['home']
                    a = data['away']
                    
                    # Relative Home Performance
                    total_pts = h['pts'] + a['pts']
                    total_gp = h['gp'] + a['gp']
                    total_ppg = total_pts / total_gp if total_gp > 0 else 0
                    
                    h_ppg = h['ppg']
                    h_rel = ((h_ppg - total_ppg) / total_ppg * 100) if total_ppg > 0 else 0
                    row['home_rel'] = round(h_rel, 1)
                    
                    # Relative Away Performance
                    a_ppg = a['ppg']
                    a_rel = ((a_ppg - total_ppg) / total_ppg * 100) if total_ppg > 0 else 0
                    row['away_rel'] = round(a_rel, 1)

                    # PPG Difference (Home vs Away)
                    ppg_home = round(h['pts'] / h['gp'], 2) if h['gp'] > 0 else 0
                    ppg_away = round(a['pts'] / a['gp'], 2) if a['gp'] > 0 else 0
                    
                    row['ppg_home'] = ppg_home
                    row['ppg_away'] = ppg_away
                    row['ppg_diff'] = round(ppg_home - ppg_away, 2)
                    row['ppg_diff_abs'] = abs(row['ppg_diff'])
                    
                    # Stats needed for relative table display
                    row['gph'] = h['gp']
                    row['gpa'] = a['gp']
                    row['pts'] = total_pts
                    
                    # Bar width
                    row['bar_width'] = min(int(abs(row['ppg_diff']) * 40), 100)
                    
                    relative_table.append(row)
                
                # Sort by Points (desc), then PPG Difference (desc)
                relative_table.sort(key=lambda x: (x['pts'], x['ppg_diff']), reverse=True)
                
                # Add Rank
                for i, row in enumerate(relative_table, 1): row['position'] = i
            
            context['relative_table'] = relative_table
            
            if league.name == 'First League' and league.country == 'Republica Tcheca':
                if rf_override:
                    by_name = {s.team.name: s for s in standings}
                    for name, vals in rf_override.items():
                        s = by_name.get(name)
                        if not s: 
                            continue
                        s.ppg_season = vals['ppg_season']
                        s.ppg_8 = vals['ppg_8']
                        s.ppg_diff = round(vals['ppg_8'] - vals['ppg_season'], 2)
                        s.relative_form_bar_width = min(abs(s.ppg_diff) * 40, 120)
                if rp_override:
                    by_name = {s.team.name: s for s in standings}
                    for name, vals in rp_override.items():
                        s = by_name.get(name)
                        if not s: 
                            continue
                        s.opponents_ppg = vals['opponents_ppg']
                        s.performance_index = vals['performance_index']
                        s.perf_width_pct = min(round((s.performance_index / 4.0) * 100, 1), 100) if s.performance_index > 0 else 0
                        s.ppg_season = vals.get('ppg_season', getattr(s, 'ppg_season', 0))
                if ri_override:
                    by_name = {s.team.name: s for s in standings}
                    for name, vals in ri_override.items():
                        s = by_name.get(name)
                        if not s: 
                            continue
                        s.opp_played_ppg = vals['opp_played_ppg']
                        s.opp_remaining_ppg = vals['opp_remaining_ppg']
                        s.runin_diff_pct = vals['runin_diff_pct']
                        s.next_4_ppg = vals.get('next_4_ppg', getattr(s, 'next_4_ppg', 0))
                if pp_override:
                    by_name = {s.team.name: s for s in standings}
                    for name, vals in pp_override.items():
                        s = by_name.get(name)
                        if not s:
                            continue
                        s.proj_ratio = vals['proj_ratio']
                        s.proj_ppg = vals['proj_ppg']
                        s.proj_total = vals['proj_total']

            # Group upcoming matches and calculate stats for each team (for Standings table)
            for standing in standings:
                team_id = standing.team.id
                team_matches = [m for m in upcoming_matches_qs if m.home_team_id == team_id or m.away_team_id == team_id][:5]
                standing.upcoming_matches = team_matches
                standing.empty_slots = range(5 - len(team_matches))
                
                # Projected points (current PPG * remaining games in 38-game season)
                remaining_games = 38 - standing.played
                projected_additional = standing.ppg_season * remaining_games
                standing.projected_total = round(standing.points + projected_additional, 0)
            
            # Prepare Statistics Tab Data (Upcoming Matches)
            stats_entries = []
            for match in upcoming_matches_qs:
                home_id = match.home_team_id
                away_id = match.away_team_id
                
                # Default stats if missing
                default_stats = {'gp': 0, 'w': 0, 'd': 0, 'l': 0, 'gf': 0, 'ga': 0, 'pts': 0}
                
                h_stats = team_stats[home_id]['home'] if home_id in team_stats else default_stats.copy()
                a_stats = team_stats[away_id]['away'] if away_id in team_stats else default_stats.copy()
                
                # PPG % (Base is 3 points)
                h_ppg = h_stats['pts'] / h_stats['gp'] if h_stats['gp'] > 0 else 0
                a_ppg = a_stats['pts'] / a_stats['gp'] if a_stats['gp'] > 0 else 0
                
                # WDL Distribution (Bar widths)
                h_gp = h_stats['gp'] if h_stats['gp'] > 0 else 1
                a_gp = a_stats['gp'] if a_stats['gp'] > 0 else 1
                
                h_w_pct = (h_stats['w'] / h_gp) * 100
                h_d_pct = (h_stats['d'] / h_gp) * 100
                h_l_pct = (h_stats['l'] / h_gp) * 100
                
                a_w_pct = (a_stats['w'] / a_gp) * 100
                a_d_pct = (a_stats['d'] / a_gp) * 100
                a_l_pct = (a_stats['l'] / a_gp) * 100
                
                # Goal Averages
                h_gf_avg = h_stats['gf'] / h_gp
                h_ga_avg = h_stats['ga'] / h_gp
                a_gf_avg = a_stats['gf'] / a_gp
                a_ga_avg = a_stats['ga'] / a_gp
                
                h_tg_avg = h_gf_avg + h_ga_avg
                a_tg_avg = a_gf_avg + a_ga_avg
                
                # Last 4 Form (From form_history, take last 4)
                # Note: form_history in context is Last 5 overall. We need Last 4 Home/Away specifically? 
                # The image says "Last 4" but subtab is "Home/Away". 
                # Assuming Last 4 Home matches for Home team, Last 4 Away matches for Away team.
                # We need to fetch specific form for H/A? view already calculated 'all_matches'.
                
                # Recalculate H/A specific form
                h_matches = [m for m in all_matches if m.home_team_id == home_id]
                h_matches.sort(key=lambda x: (x.date if x.date else 0, x.id), reverse=True)
                h_form_4 = []
                for m in h_matches[:4]:
                    if m.home_score > m.away_score: h_form_4.append('W')
                    elif m.home_score == m.away_score: h_form_4.append('D')
                    else: h_form_4.append('L')
                    
                a_matches = [m for m in all_matches if m.away_team_id == away_id]
                a_matches.sort(key=lambda x: (x.date if x.date else 0, x.id), reverse=True)
                a_form_4 = []
                for m in a_matches[:4]:
                    if m.away_score > m.home_score: a_form_4.append('W')
                    elif m.away_score == m.home_score: a_form_4.append('D')
                    else: a_form_4.append('L')
                        
                entry = {
                    'match': match,
                    'home_team': match.home_team,
                    'away_team': match.away_team,
                    'h_ppg_pct': int((h_ppg / 3) * 100),
                    'a_ppg_pct': int((a_ppg / 3) * 100),
                    'h_wdl': {'w': h_w_pct, 'd': h_d_pct, 'l': h_l_pct},
                    'a_wdl': {'w': a_w_pct, 'd': a_d_pct, 'l': a_l_pct},
                    'h_goals': {'gf': round(h_gf_avg, 2), 'ga': round(h_ga_avg, 2), 'tg': round(h_tg_avg, 2)},
                    'a_goals': {'gf': round(a_gf_avg, 2), 'ga': round(a_ga_avg, 2), 'tg': round(a_tg_avg, 2)},
                    'h_over_25': 0, # Placeholder
                    'a_over_25': 0, # Placeholder
                    'h_last_4': h_form_4,
                    'a_last_4': a_form_4
                }
                
                # Calculate Over 2.5 %
                h_over_count = sum(1 for m in h_matches if (m.home_score + m.away_score) > 2.5)
                entry['h_over_25'] = int((h_over_count / len(h_matches) * 100)) if h_matches else 0
                
                a_over_count = sum(1 for m in a_matches if (m.home_score + m.away_score) > 2.5)
                entry['a_over_25'] = int((a_over_count / len(a_matches) * 100)) if a_matches else 0
                
                stats_entries.append(entry)

            # Prepare Statistics Tab Data (Overall)
            stats_entries_overall = []
            
            # Map standings by team_id for easier access
            standings_map = {s.team.id: s for s in standings}
            
            for match in upcoming_matches_qs:
                home_id = match.home_team_id
                away_id = match.away_team_id
                
                # Default standing if missing (should use empty object-like struct)
                # But we can just use 0 values if not found.
                
                h_standing = standings_map.get(home_id)
                a_standing = standings_map.get(away_id)
                
                # Helper to get stats safely
                def get_safe_stats(standing):
                    if not standing:
                        return {'ppg': 0, 'w_pct': 0, 'd_pct': 0, 'l_pct': 0, 'gf_avg': 0, 'ga_avg': 0, 'tg_avg': 0}
                    gp = standing.played if standing.played > 0 else 1
                    return {
                        'ppg': standing.ppg_season,
                        'w_pct': (standing.won / gp) * 100,
                        'd_pct': (standing.drawn / gp) * 100,
                        'l_pct': (standing.lost / gp) * 100,
                        'gf_avg': standing.goals_for / gp,
                        'ga_avg': standing.goals_against / gp,
                        'tg_avg': (standing.goals_for + standing.goals_against) / gp
                    }

                h_s = get_safe_stats(h_standing)
                a_s = get_safe_stats(a_standing)
                
                # Last 4 Form (Overall)
                h_matches_all = [m for m in all_matches if m.home_team_id == home_id or m.away_team_id == home_id]
                h_matches_all.sort(key=lambda x: (x.date if x.date else 0, x.id), reverse=True)
                h_form_4 = []
                for m in h_matches_all[:4]:
                    is_home = m.home_team_id == home_id
                    team_score = m.home_score if is_home else m.away_score
                    opp_score = m.away_score if is_home else m.home_score
                    
                    if team_score > opp_score: h_form_4.append('W')
                    elif team_score == opp_score: h_form_4.append('D')
                    else: h_form_4.append('L')
                    
                a_matches_all = [m for m in all_matches if m.home_team_id == away_id or m.away_team_id == away_id]
                a_matches_all.sort(key=lambda x: (x.date if x.date else 0, x.id), reverse=True)
                a_form_4 = []
                for m in a_matches_all[:4]:
                    is_home = m.home_team_id == away_id
                    team_score = m.home_score if is_home else m.away_score
                    opp_score = m.away_score if is_home else m.home_score
                    
                    if team_score > opp_score: a_form_4.append('W')
                    elif team_score == opp_score: a_form_4.append('D')
                    else: a_form_4.append('L')

                # Calculate Over 2.5 % (Overall)
                h_over_count = sum(1 for m in h_matches_all if (m.home_score + m.away_score) > 2.5)
                h_over_pct = int((h_over_count / len(h_matches_all) * 100)) if h_matches_all else 0
                
                a_over_count = sum(1 for m in a_matches_all if (m.home_score + m.away_score) > 2.5)
                a_over_pct = int((a_over_count / len(a_matches_all) * 100)) if a_matches_all else 0

                entry = {
                    'match': match,
                    'home_team': match.home_team,
                    'away_team': match.away_team,
                    'h_ppg_pct': int((h_s['ppg'] / 3) * 100),
                    'a_ppg_pct': int((a_s['ppg'] / 3) * 100),
                    'h_wdl': {'w': h_s['w_pct'], 'd': h_s['d_pct'], 'l': h_s['l_pct']},
                    'a_wdl': {'w': a_s['w_pct'], 'd': a_s['d_pct'], 'l': a_s['l_pct']},
                    'h_goals': {'gf': round(h_s['gf_avg'], 2), 'ga': round(h_s['ga_avg'], 2), 'tg': round(h_s['tg_avg'], 2)},
                    'a_goals': {'gf': round(a_s['gf_avg'], 2), 'ga': round(a_s['ga_avg'], 2), 'tg': round(a_s['tg_avg'], 2)},
                    'h_over_25': h_over_pct,
                    'a_over_25': a_over_pct,
                    'h_last_4': h_form_4,
                    'a_last_4': a_form_4
                }
                stats_entries_overall.append(entry)

            # Prepare Statistics Tab Data (Last 8 Matches)
            stats_entries_last8 = []
            
            for match in upcoming_matches_qs:
                home_id = match.home_team_id
                away_id = match.away_team_id
                
                # Get last 8 matches for each team
                h_matches_all = [m for m in all_matches if m.home_team_id == home_id or m.away_team_id == home_id]
                h_matches_all.sort(key=lambda x: (x.date if x.date else 0, x.id), reverse=True)
                h_last8 = h_matches_all[:8]
                
                a_matches_all = [m for m in all_matches if m.home_team_id == away_id or m.away_team_id == away_id]
                a_matches_all.sort(key=lambda x: (x.date if x.date else 0, x.id), reverse=True)
                a_last8 = a_matches_all[:8]
                
                def calc_last8_stats(matches, team_id):
                    gp = len(matches)
                    if gp == 0:
                        return {'ppg': 0, 'w_pct': 0, 'd_pct': 0, 'l_pct': 0, 'gf_avg': 0, 'ga_avg': 0, 'tg_avg': 0}
                    
                    pts = 0; w = 0; d = 0; l = 0; gf = 0; ga = 0
                    for m in matches:
                        is_home = m.home_team_id == team_id
                        team_score = m.home_score if is_home else m.away_score
                        opp_score = m.away_score if is_home else m.home_score
                        
                        gf += team_score
                        ga += opp_score
                        
                        if team_score > opp_score: w += 1; pts += 3
                        elif team_score == opp_score: d +=1; pts += 1
                        else: l += 1
                        
                    return {
                        'ppg': pts / gp,
                        'w_pct': (w / gp) * 100,
                        'd_pct': (d / gp) * 100,
                        'l_pct': (l / gp) * 100,
                        'gf_avg': gf / gp,
                        'ga_avg': ga / gp,
                        'tg_avg': (gf + ga) / gp
                    }
                
                h_s = calc_last8_stats(h_last8, home_id)
                a_s = calc_last8_stats(a_last8, away_id)
                
                # Form (Last 4 of the Last 8 - effectively Last 4 overall)
                h_form_4 = []
                for m in h_last8[:4]:
                    is_home = m.home_team_id == home_id
                    team_score = m.home_score if is_home else m.away_score
                    opp_score = m.away_score if is_home else m.home_score
                    if team_score > opp_score: h_form_4.append('W')
                    elif team_score == opp_score: h_form_4.append('D')
                    else: h_form_4.append('L')
                    
                a_form_4 = []
                for m in a_last8[:4]:
                    is_home = m.home_team_id == away_id
                    team_score = m.home_score if is_home else m.away_score
                    opp_score = m.away_score if is_home else m.home_score
                    if team_score > opp_score: a_form_4.append('W')
                    elif team_score == opp_score: a_form_4.append('D')
                    else: a_form_4.append('L')
                
                # Over 2.5 % (in Last 8)
                h_over_count = sum(1 for m in h_last8 if (m.home_score + m.away_score) > 2.5)
                h_over_pct = int((h_over_count / len(h_last8) * 100)) if h_last8 else 0
                
                a_over_count = sum(1 for m in a_last8 if (m.home_score + m.away_score) > 2.5)
                a_over_pct = int((a_over_count / len(a_last8) * 100)) if a_last8 else 0

                entry = {
                    'match': match,
                    'home_team': match.home_team,
                    'away_team': match.away_team,
                    'h_ppg_pct': int((h_s['ppg'] / 3) * 100),
                    'a_ppg_pct': int((a_s['ppg'] / 3) * 100),
                    'h_wdl': {'w': h_s['w_pct'], 'd': h_s['d_pct'], 'l': h_s['l_pct']},
                    'a_wdl': {'w': a_s['w_pct'], 'd': a_s['d_pct'], 'l': a_s['l_pct']},
                    'h_goals': {'gf': round(h_s['gf_avg'], 2), 'ga': round(h_s['ga_avg'], 2), 'tg': round(h_s['tg_avg'], 2)},
                    'a_goals': {'gf': round(a_s['gf_avg'], 2), 'ga': round(a_s['ga_avg'], 2), 'tg': round(a_s['tg_avg'], 2)},
                    'h_over_25': h_over_pct,
                    'a_over_25': a_over_pct,
                    'h_last_4': h_form_4,
                    'a_last_4': a_form_4
                }
                stats_entries_last8.append(entry)
            
            context['stats_entries'] = stats_entries
            context['stats_entries_overall'] = stats_entries_overall
            context['stats_entries_last8'] = stats_entries_last8
            context['upcoming_matches'] = upcoming_matches_qs
        else:
            context['standings'] = []
            context['home_table'] = []
            context['away_table'] = []
            context['upcoming_matches'] = []
            
        return context



class TeamDetailView(DetailView):
    model = Team
    template_name = 'matches/team_detail.html'
    context_object_name = 'team'

    def get_object(self):
        # Captura os parâmetros da URL
        league_slug = self.kwargs.get('league_name')
        team_slug = self.kwargs.get('team_name')
        
        # Converte slugs para busca aproximada (ex: premier-league -> Premier League)
        league_name_query = league_slug.replace('-', ' ')
        team_name_query = team_slug.replace('-', ' ')
        team_key = team_name_query.strip().lower()
        
        name_map = {
            'la liga': {
                'barcelona': 'Barcelona',
                'real madrid': 'Real Madrid',
                'atletico madrid': 'Ath Madrid',
                'atlético madrid': 'Ath Madrid',
                'athletic bilbao': 'Ath Bilbao',
                'real sociedad': 'Sociedad',
                'espanyol': 'Espanol',
                'sevilla': 'Sevilla',
                'villarreal': 'Villarreal',
                'betis': 'Betis',
                'celta vigo': 'Celta',
                'alaves': 'Alaves',
                'mallorca': 'Mallorca',
                'osasuna': 'Osasuna',
                'getafe': 'Getafe',
                'granada': 'Granada',
                'valencia': 'Valencia',
                'rayo vallecano': 'Rayo Vallecano',
                'las palmas': 'Las Palmas',
            },
            'serie a': {
                'juventus': 'Juventus',
                'inter': 'Inter',
                'internazionale': 'Inter',
                'ac milan': 'Milan',
                'milan': 'Milan',
                'as roma': 'Roma',
                'roma': 'Roma',
                'napoli': 'Napoli',
                'lazio': 'Lazio',
                'atalanta': 'Atalanta',
                'fiorentina': 'Fiorentina',
                'bologna': 'Bologna',
                'torino': 'Torino',
                'udinese': 'Udinese',
                'sassuolo': 'Sassuolo',
                'lecce': 'Lecce',
                'empoli': 'Empoli',
                'genoa': 'Genoa',
                'monza': 'Monza',
                'cagliari': 'Cagliari',
                'verona': 'Verona',
                'hellas verona': 'Verona',
            }
        }
        
        league_key = league_name_query.strip().lower()
        if league_key in name_map and team_key in name_map[league_key]:
            team_name_query = name_map[league_key][team_key]
        
        # 1. Resolve League First (Robust com desambiguação)
        leagues_qs = League.objects.filter(name__iexact=league_name_query)
        if not leagues_qs.exists():
            leagues_qs = League.objects.filter(name__icontains=league_name_query)
        
        league = None
        if leagues_qs.exists():
            # Prioriza liga com mais times; empate quebra por ter standings
            from django.db.models import Count
            league = leagues_qs.annotate(
                team_count=Count('teams'),
                s_count=Count('standings')
            ).order_by('-team_count', '-s_count').first()
        
        if not league:
            from django.utils.text import slugify
            for l in League.objects.all():
                if slugify(l.name) == league_slug:
                    league = l
                    break
        
        qs = Team.objects.all()
        if league:
            qs = qs.filter(league=league)
        else:
            qs = qs.filter(league__name__icontains=league_name_query)

        # 2. Resolve Team
        team = qs.filter(name__iexact=team_name_query).first()
        
        if not team:
             team = qs.filter(name__icontains=team_name_query).first()
             
        if not team:
             from django.utils.text import slugify
             for t in qs:
                 if slugify(t.name) == team_slug:
                     team = t
                     break
         
        if not team:
             team = Team.objects.filter(name__iexact=team_name_query).first() or \
                    Team.objects.filter(name__icontains=team_name_query).first()
             if team:
                 league = team.league

        if team:
            return team
            
        from django.http import Http404
        raise Http404(f"Team '{team_slug}' not found in '{league_slug}'")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = self.object
        league = team.league
        
        # Latest Season
        latest_season = Season.objects.filter(standings__league=league).order_by('-year').distinct().first()
        
        # League Standing
        standing = LeagueStanding.objects.filter(
            league=league, season=latest_season, team=team
        ).first()
        
        context['standing'] = standing
        context['league'] = league

        # --- Comparison with Past Seasons Logic ---
        past_seasons_data = []
        past_seasons = Season.objects.none()  # Initialize to avoid UnboundLocalError
        if standing:
            current_gp = standing.played
            current_pts = standing.points
            
            # Get past seasons (exclude current)
            past_seasons = Season.objects.filter(standings__league=league).exclude(id=latest_season.id).distinct().order_by('-year')
            
            for s_obj in past_seasons:
                # Get matches for this season involving the team
                season_matches = Match.objects.filter(
                    league=league,
                    season=s_obj,
                    status__in=FINISHED_STATUSES
                ).filter(
                    models.Q(home_team=team) | models.Q(away_team=team)
                ).order_by('date')
                
                # Take the first 'current_gp' matches
                matches_subset = season_matches[:current_gp]
                gp = len(matches_subset)
                
                # Only include if there's at least one match to compare, 
                # though strictly we might want exactly 'current_gp'. 
                # We'll show what we have.
                if gp > 0:
                    w = 0; d = 0; l = 0; gf = 0; ga = 0; pts = 0
                    
                    for m in matches_subset:
                        is_home = m.home_team == team
                        my_score = m.home_score if is_home else m.away_score
                        opp_score = m.away_score if is_home else m.home_score
                        
                        # Handle potential None values safely
                        if my_score is None: my_score = 0
                        if opp_score is None: opp_score = 0
                        
                        gf += my_score
                        ga += opp_score
                        
                        if my_score > opp_score:
                            w += 1
                            pts += 3
                        elif my_score == opp_score:
                            d += 1
                            pts += 1
                        else:
                            l += 1
                    
                    # Comparison: Difference between CURRENT Pts and PAST Pts
                    # Example: Current 49, Past 51 -> Diff is -2. 
                    # Correct logic: Current - Past.
                    diff = current_pts - pts
                    
                    past_seasons_data.append({
                        'season_year': s_obj.year,
                        'gp': gp,
                        'w': w, 'd': d, 'l': l,
                        'gf': gf, 'ga': ga, 'pts': pts,
                        'diff': diff,
                        'is_partial': gp < current_gp
                    })
        
        context['past_seasons_data'] = past_seasons_data
        context['current_gp_comparison'] = current_gp if standing else 0

        
        # All Matches
        all_matches = Match.objects.filter(
             league=league, season=latest_season
         ).filter(
             models.Q(home_team=team) | models.Q(away_team=team)
         ).order_by('date').prefetch_related('goals')
         
        played_matches = [m for m in all_matches if m.status == 'Finished' and m.home_score is not None]
        
        # --- Stats Containers ---
        # Structure: 'home', 'away', 'total'
        cats = ['home', 'away', 'total']
        
        # Basic Stats
        stats = {c: {
            'gp': 0, 'w': 0, 'd': 0, 'l': 0, 'gf': 0, 'ga': 0, 'pts': 0,
            'win_margins': {}, 'loss_margins': {}, # Dicts to count margins
            'ht_w': 0, 'ht_d': 0, 'ht_l': 0,
            'corners_for_list': [], 'corners_against_list': [],
            'min_scored_first_list': [], 'min_conceded_first_list': []
        } for c in cats}
        
        # Goal Rates (Over/Under)
        thresholds = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
        ht_thresholds = [0.5, 1.5, 2.5]
        goal_stats = {
            'scored': {c: {t: 0 for t in thresholds} for c in cats},
            'conceded': {c: {t: 0 for t in thresholds} for c in cats},
            'match_total': {c: {t: 0 for t in thresholds} for c in cats},
            'ht_match_total': {c: {t: 0 for t in ht_thresholds} for c in cats}
        }
        
        # Special Rates
        rates = {c: {
            'cs': 0, 'fts': 0, 'bts': 0,
            'wtn': 0, 'ltn': 0,
            'scored_first': 0, 'conceded_first': 0,
            'score_1h': 0, 'score_2h': 0, 'score_both': 0,
            'concede_1h': 0, 'concede_2h': 0, 'concede_both': 0
        } for c in cats}
        
        # Total Goals Distribution (exact goals)
        total_goals_dist = {c: {i: 0 for i in range(6)} for c in cats} # 0, 1, 2, 3, 4, 5+
        
        # Timing of Goals (0-15, 16-30, 31-45, 46-60, 61-75, 76-90+)
        timing_stats = {
            'scored': {c: [0]*6 for c in cats},
            'conceded': {c: [0]*6 for c in cats}
        }
        
        # HT/FT Matrix (Home/Away/Total)
        # Structure: 3x3 matrix [HT_W, HT_D, HT_L] x [FT_W, FT_D, FT_L]
        # Indices: 0=W, 1=D, 2=L
        ht_ft_matrix = {c: [[0]*3 for _ in range(3)] for c in cats}
        
        # Goal Types (Simplified)
        goal_types = {
            'scored': {c: {'penalty': 0, 'own_goal': 0, 'regular': 0} for c in cats},
            'conceded': {c: {'penalty': 0, 'own_goal': 0, 'regular': 0} for c in cats}
        }
        
        # Card Stats
        card_stats = {
            'yellow': {c: 0 for c in cats},
            'red': {c: 0 for c in cats}
        }

        matches_data = [] # List for display
        chart_data = {'labels': [], 'values': [], 'results': [], 'gf': [], 'ga': []}
        chart_val = 0
        
        for m in played_matches:
            is_home = m.home_team == team
            cat = 'home' if is_home else 'away'
            
            gf = (m.home_score if is_home else m.away_score) or 0
            ga = (m.away_score if is_home else m.home_score) or 0
            
            # HT Scores (Assume None=0 if missing, though typically present)
            ht_gf = (m.ht_home_score if is_home else m.ht_away_score) or 0
            ht_ga = (m.ht_away_score if is_home else m.ht_home_score) or 0
            
            # 2nd Half Scores
            ft_gf_2h = gf - ht_gf
            ft_ga_2h = ga - ht_ga
            
            match_total = gf + ga
            result = 'W' if gf > ga else ('D' if gf == ga else 'L')
            opponent = m.away_team if is_home else m.home_team
            
            # --- Update Basic Stats ---
            for k in [cat, 'total']:
                s = stats[k]
                s['gp'] += 1
                s['gf'] += gf
                s['ga'] += ga
                if result == 'W': s['w'] += 1; s['pts'] += 3
                elif result == 'D': s['d'] += 1; s['pts'] += 1
                else: s['l'] += 1
                
                # Rates
                r = rates[k]
                if ga == 0: r['cs'] += 1
                if gf == 0: r['fts'] += 1
                if gf > 0 and ga > 0: r['bts'] += 1
                
                if result == 'W' and ga == 0: r['wtn'] += 1
                if result == 'L' and gf == 0: r['ltn'] += 1
                
                # First goal tracking (Using actual goal data if available)
                match_goals = list(m.goals.all())
                first_goal = None
                if match_goals:
                    # Sort by minute
                    match_goals.sort(key=lambda x: x.minute)
                    first_goal = match_goals[0]
                    
                    if first_goal.team == team:
                        r['scored_first'] += 1
                        s['min_scored_first_list'].append(first_goal.minute)
                    else:
                        r['conceded_first'] += 1
                        s['min_conceded_first_list'].append(first_goal.minute)
                else:
                    # Fallback approximation if goal details are missing
                    if gf > 0:
                        if gf > ga or (gf == ga and gf > 0):
                            r['scored_first'] += 1
                            s['min_scored_first_list'].append(30)
                    if ga > 0:
                        if ga > gf or (ga == gf and ga > 0):
                            r['conceded_first'] += 1
                            s['min_conceded_first_list'].append(35)
                
                if ht_gf > 0: r['score_1h'] += 1
                if ft_gf_2h > 0: r['score_2h'] += 1
                if ht_gf > 0 and ft_gf_2h > 0: r['score_both'] += 1
                
                if ht_ga > 0: r['concede_1h'] += 1
                if ft_ga_2h > 0: r['concede_2h'] += 1
                if ht_ga > 0 and ft_ga_2h > 0: r['concede_both'] += 1

                # Goal Thresholds
                gs = goal_stats['scored'][k]
                gc = goal_stats['conceded'][k]
                gm = goal_stats['match_total'][k]
                ght = goal_stats['ht_match_total'][k]
                
                for t in thresholds:
                    if gf > t: gs[t] += 1
                    if ga > t: gc[t] += 1
                    if match_total > t: gm[t] += 1
                
                ht_match_total = ht_gf + ht_ga
                for t in ht_thresholds:
                    if ht_match_total > t: ght[t] += 1
                    
                # Exact Goals Dist
                tg_idx = match_total if match_total < 5 else 5
                total_goals_dist[k][tg_idx] += 1
                
                # Update Margins
                margin = abs(gf - ga)
                if result == 'W':
                    s['win_margins'][margin] = s['win_margins'].get(margin, 0) + 1
                elif result == 'L':
                    s['loss_margins'][margin] = s['loss_margins'].get(margin, 0) + 1
                    
                if ht_gf > ht_ga: s['ht_w'] += 1
                elif ht_gf == ht_ga: s['ht_d'] += 1
                else: s['ht_l'] += 1
                
                # --- HT/FT Matrix Logic ---
                # HT Index: 0=W, 1=D, 2=L
                if ht_gf > ht_ga: ht_idx = 0
                elif ht_gf == ht_ga: ht_idx = 1
                else: ht_idx = 2
                
                # FT Index: 0=W, 1=D, 2=L
                if gf > ga: ft_idx = 0
                elif gf == ga: ft_idx = 1
                else: ft_idx = 2
                
                ht_ft_matrix[k][ht_idx][ft_idx] += 1
                
                # --- Timing & Goal Types ---
                if match_goals:
                    for g in match_goals:
                        # Determine if this goal belongs to the current team (for 'scored') or opponent (for 'conceded')
                        # Note: 'team' is the Team object for this view.
                        is_scored_by_us = (g.team == team)
                        
                        # Minute Segment
                        minute = max(1, g.minute)
                        t_idx = min((minute - 1) // 15, 5)
                        
                        # Type
                        g_type = 'regular'
                        if g.is_penalty: g_type = 'penalty'
                        elif g.is_own_goal: g_type = 'own_goal'
                        
                        if is_scored_by_us:
                            timing_stats['scored'][k][t_idx] += 1
                            goal_types['scored'][k][g_type] += 1
                        else:
                            timing_stats['conceded'][k][t_idx] += 1
                            goal_types['conceded'][k][g_type] += 1
                else:
                    # Fallback if no goal details but we have score
                    # We can't do accurate timing or types, so we skip or assume 'regular'
                    # For now, let's just skip to avoid bad data
                    pass

                # Card Stats Update
                if m.home_yellow is not None: # Assume if yellow is present, others are likely present or 0
                    my_yellow = (m.home_yellow if is_home else m.away_yellow) or 0
                    my_red = (m.home_red if is_home else m.away_red) or 0
                    card_stats['yellow'][k] += my_yellow
                    card_stats['red'][k] += my_red

                if m.home_corners is not None and m.away_corners is not None:
                    my_corners = m.home_corners if is_home else m.away_corners
                    opp_corners = m.away_corners if is_home else m.home_corners
                    s['corners_for_list'].append(my_corners)
                    s['corners_against_list'].append(opp_corners)

            # --- Match List Item ---
            matches_data.append({
                'id': m.id,
                'slug': m.slug,
                'date': m.date,
                'opponent': opponent,
                'is_home': is_home,
                'score': f"{m.home_score}-{m.away_score}",
                'ht_score': f"{m.ht_home_score}-{m.ht_away_score}" if m.ht_home_score is not None else "-",
                'result': result,
                'result_class': 'ss-green' if result == 'W' else ('ss-red' if result == 'L' else 'ss-orange'),
                'total_goals': match_total,
                'over_25': match_total > 2.5,
                'cs': ga == 0,
                'fts': gf == 0,
                'bts': gf > 0 and ga > 0
            })
            
            # --- Chart Data ---
            chart_change = 2 if result == 'W' else (0 if result == 'D' else -1)
            chart_val += chart_change
            chart_data['labels'].append(m.date.strftime('%d %b') if m.date else f"R{m.round}")
            chart_data['values'].append(chart_val)
            chart_data['results'].append(result)
            chart_data['gf'].append(gf)
            chart_data['ga'].append(-ga) # Negative for conceded


        # --- Helper for Percentages ---
        def calc_pct(val, gp):
            return round((val / gp) * 100) if gp > 0 else 0
            


        # Post-process Stats Dictionary
        for k in cats:
            gp = stats[k]['gp']
            stats[k]['ppg'] = round(stats[k]['pts'] / gp, 2) if gp > 0 else 0
            
            # Points Share
            total_pts = stats['total']['pts']
            stats[k]['points_pct_share'] = calc_pct(stats[k]['pts'], total_pts)

            stats[k]['avg_gf'] = round(stats[k]['gf'] / gp, 2) if gp > 0 else 0
            stats[k]['avg_ga'] = round(stats[k]['ga'] / gp, 2) if gp > 0 else 0
            stats[k]['win_pct'] = calc_pct(stats[k]['w'], gp)
            stats[k]['draw_pct'] = calc_pct(stats[k]['d'], gp)
            stats[k]['loss_pct'] = calc_pct(stats[k]['l'], gp)
            stats[k]['avg_total_goals'] = round(stats[k]['avg_gf'] + stats[k]['avg_ga'], 2)
            
            # Rates %
            for rk in list(rates[k].keys()):
                rates[k][rk + '_pct'] = calc_pct(rates[k][rk], gp)
            
            # Explicit Scoring/Conceding Rates (Complement of FTS/CS)
            rates[k]['scoring_rate_pct'] = 100 - rates[k]['fts_pct']
            rates[k]['conceding_rate_pct'] = 100 - rates[k]['cs_pct']
            
            # Average minute scored/conceded first
            if stats[k]['min_scored_first_list']:
                stats[k]['avg_min_scored_first'] = sum(stats[k]['min_scored_first_list']) / len(stats[k]['min_scored_first_list'])
            else:
                stats[k]['avg_min_scored_first'] = 0
                
            if stats[k]['min_conceded_first_list']:
                stats[k]['avg_min_conceded_first'] = sum(stats[k]['min_conceded_first_list']) / len(stats[k]['min_conceded_first_list'])
            else:
                stats[k]['avg_min_conceded_first'] = 0
            
            # Goal Rates %
            for type_ in ['scored', 'conceded', 'match_total']:
                for t in thresholds:
                    goal_stats[type_][k][f"{t}_pct"] = calc_pct(goal_stats[type_][k][t], gp)
            
            # HT %
            for t in ht_thresholds:
                goal_stats['ht_match_total'][k][f"{t}_pct"] = calc_pct(goal_stats['ht_match_total'][k][t], gp)
            
            # Goals Dist %
            for i in range(6):
                total_goals_dist[k][f"{i}_pct"] = calc_pct(total_goals_dist[k][i], gp)
                
            # Margins %
            # (Calculated in context generally, but percentages can be done here if needed)

        # --- Post-Loop aggregated stats ---
        
        # Helper for Margin aggregation
        def get_margin_counts(data):
            return {
                1: data.get(1, 0),
                2: data.get(2, 0),
                3: data.get(3, 0),
                4: sum(v for k, v in data.items() if k >= 4)
            }
        
        margin_stats = {
            'wins': {
                'home': get_margin_counts(stats['home']['win_margins']),
                'away': get_margin_counts(stats['away']['win_margins']),
                'total': get_margin_counts(stats['total']['win_margins'])
            },
            'defeats': {
                'home': get_margin_counts(stats['home']['loss_margins']),
                'away': get_margin_counts(stats['away']['loss_margins']),
                'total': get_margin_counts(stats['total']['loss_margins'])
            }
        }
        
        # HT Results Percentages
        ht_stats = {
            'leading': {'home': stats['home']['ht_w'], 'away': stats['away']['ht_w'], 'total': stats['total']['ht_w']},
            'drawing': {'home': stats['home']['ht_d'], 'away': stats['away']['ht_d'], 'total': stats['total']['ht_d']},
            'losing': {'home': stats['home']['ht_l'], 'away': stats['away']['ht_l'], 'total': stats['total']['ht_l']},
        }
        for res in ht_stats:
            for c in cats:
                gp = stats[c]['gp']
                ht_stats[res][f"{c}_pct"] = calc_pct(ht_stats[res][c], gp)
        
        # Card Averages
        card_avgs = {
            'yellow': {c: 0 for c in cats},
            'red': {c: 0 for c in cats}
        }
        for c in cats:
            gp = stats[c]['gp']
            if gp > 0:
                card_avgs['yellow'][c] = round(card_stats['yellow'][c] / gp, 2)
                card_avgs['red'][c] = round(card_stats['red'][c] / gp, 2)

        # Corner Stats Percentages & Avgs
        corner_thresholds = [2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 15.5]
        corner_data = {
            'for': {c: {'avg': 0, 'thresholds': {t: 0 for t in corner_thresholds}} for c in cats},
            'against': {c: {'avg': 0, 'thresholds': {t: 0 for t in corner_thresholds}} for c in cats},
            'total': {c: {'avg': 0, 'thresholds': {t: 0 for t in corner_thresholds}} for c in cats}
        }
        
        for c in cats:
            gp = stats[c]['gp']
            corners_for = stats[c]['corners_for_list']
            corners_against = stats[c]['corners_against_list']
            valid_gp = len(corners_for)
            if gp > 0 and valid_gp > 0:
                total_corners = [x + y for x, y in zip(corners_for, corners_against)]
                corner_data['for'][c]['avg'] = round(sum(corners_for) / valid_gp, 2)
                for t in corner_thresholds:
                    count = sum(1 for x in corners_for if x > t)
                    corner_data['for'][c]['thresholds'][t] = calc_pct(count, valid_gp)
                corner_data['against'][c]['avg'] = round(sum(corners_against) / valid_gp, 2)
                for t in corner_thresholds:
                    count = sum(1 for x in corners_against if x > t)
                    corner_data['against'][c]['thresholds'][t] = calc_pct(count, valid_gp)
                corner_data['total'][c]['avg'] = round(sum(total_corners) / valid_gp, 2)
                for t in corner_thresholds:
                    count = sum(1 for x in total_corners if x > t)
                    corner_data['total'][c]['thresholds'][t] = calc_pct(count, valid_gp)
        
        context['margin_stats'] = margin_stats
        context['timing_stats'] = timing_stats
        context['ht_ft_matrix'] = ht_ft_matrix
        context['goal_types'] = goal_types
        context['card_stats'] = card_stats
        context['card_avgs'] = card_avgs
        context['ht_stats'] = ht_stats
        context['corner_data'] = corner_data
        context['corner_thresholds'] = corner_thresholds

        context['stats'] = stats
        context['rates'] = rates
        context['goal_stats'] = goal_stats
        context['total_goals_dist'] = total_goals_dist
        context['thresholds'] = thresholds
        context['ht_thresholds'] = ht_thresholds
        # Últimos 20 jogos apenas (recorte da lista, em ordem do mais recente para o mais antigo)
        context['matches_list'] = matches_data[-20:][::-1]
        
        # Upcoming Matches
        upcoming_matches = Match.objects.filter(
            league=league,
            season=latest_season,
            status='Scheduled'
        ).filter(
            models.Q(home_team=team) | models.Q(away_team=team)
        ).order_by('date')[:10] # Next 10 matches
        context['upcoming_matches'] = upcoming_matches

        context['chart_data_json'] = json.dumps(chart_data)

        # --- League Averages for Descriptive Text ---
        league_matches = Match.objects.filter(league=league, season=latest_season, status__in=FINISHED_STATUSES, home_score__isnull=False)
        league_gp = league_matches.count()
        league_over25 = league_matches.annotate(total_g=models.F('home_score') + models.F('away_score')).filter(total_g__gt=2.5).count()
        league_over25_pct = round((league_over25 / league_gp) * 100) if league_gp > 0 else 0
        context['league_over25_pct'] = league_over25_pct
        
        # --- Relative Form ---
        # (Simplified reuse of existing logic or derived from played_matches)
        # Included in stats['total'] vs Last 8
        last_8 = played_matches[-8:]
        l8_pts = sum([3 if (m.home_team==team and m.home_score>m.away_score) or (m.away_team==team and m.away_score>m.home_score) else (1 if m.home_score==m.away_score else 0) for m in last_8])
        l8_gf = sum([(m.home_score if m.home_team==team else m.away_score) for m in last_8])
        l8_ga = sum([(m.away_score if m.home_team==team else m.home_score) for m in last_8])
        l8_gp = len(last_8)
        
        l8_ppg = round(l8_pts / l8_gp, 2) if l8_gp > 0 else 0
        l8_avg_gf = round(l8_gf / l8_gp, 2) if l8_gp > 0 else 0
        l8_avg_ga = round(l8_ga / l8_gp, 2) if l8_gp > 0 else 0
        
        season_ppg = stats['total']['ppg']
        season_avg_gf = stats['total']['avg_gf']
        season_avg_ga = stats['total']['avg_ga']
        
        def calc_diff(l8, season):
            if season == 0: return 0
            return round(((l8 - season) / season) * 100, 1)

        context['relative_form'] = {
            'ppg': {'all': season_ppg, 'l8': l8_ppg, 'diff': calc_diff(l8_ppg, season_ppg)},
            'avg_gf': {'all': season_avg_gf, 'l8': l8_avg_gf, 'diff': calc_diff(l8_avg_gf, season_avg_gf)},
            'avg_ga': {'all': season_avg_ga, 'l8': l8_avg_ga, 'diff': calc_diff(l8_avg_ga, season_avg_ga)},
        }

        # --- League Averages for Comparison Box ---
        # Get all teams in the league for this season
        all_league_standings = LeagueStanding.objects.filter(
            league=league,
            season=latest_season
        ).select_related('team')
        
        # Get all matches in the league for this season
        all_league_matches = Match.objects.filter(
            league=league,
            season=latest_season,
            status__in=FINISHED_STATUSES,
            home_score__isnull=False
        ).select_related('home_team', 'away_team')
        
        # Calculate league averages for each category (total, home, away)
        league_avg = {c: {
            'ppg': 0, 'win_pct': 0, 'draw_pct': 0, 'loss_pct': 0,
            'avg_gf': 0, 'avg_ga': 0, 'cs_pct': 0, 'fts_pct': 0,
            'wtn_pct': 0, 'ltn_pct': 0, 'scored_first_pct': 0, 'conceded_first_pct': 0,
            'avg_min_scored_first': 0, 'avg_min_conceded_first': 0
        } for c in cats}
        
        # Calculate stats for each team in the league
        team_count = all_league_standings.count()
        if team_count > 0:
            for standing in all_league_standings:
                league_team = standing.team
                team_matches = [m for m in all_league_matches if m.home_team == league_team or m.away_team == league_team]
                
                # Stats by category
                team_stats_calc = {c: {
                    'gp': 0, 'w': 0, 'd': 0, 'l': 0, 'gf': 0, 'ga': 0, 'pts': 0,
                    'cs': 0, 'fts': 0, 'wtn': 0, 'ltn': 0, 'scored_first': 0, 'conceded_first': 0,
                    'min_scored_first': [], 'min_conceded_first': []
                } for c in cats}
                
                for m in team_matches:
                    is_home = m.home_team == league_team
                    cat = 'home' if is_home else 'away'
                    
                    gf = (m.home_score if is_home else m.away_score) or 0
                    ga = (m.away_score if is_home else m.home_score) or 0
                    result = 'W' if gf > ga else ('D' if gf == ga else 'L')
                    
                    for k in [cat, 'total']:
                        s = team_stats_calc[k]
                        s['gp'] += 1
                        s['gf'] += gf
                        s['ga'] += ga
                        if result == 'W': s['w'] += 1; s['pts'] += 3
                        elif result == 'D': s['d'] += 1; s['pts'] += 1
                        else: s['l'] += 1
                        
                        # Special rates
                        if ga == 0: s['cs'] += 1
                        if gf == 0: s['fts'] += 1
                        if result == 'W' and ga == 0: s['wtn'] += 1
                        if result == 'L' and gf == 0: s['ltn'] += 1
                        
                        # First goal tracking (simplified - we'll use approximations)
                        # For now, assume team scored first if they won or drew and scored
                        if gf > 0:
                            if gf > ga or (gf == ga and gf > 0):
                                s['scored_first'] += 1
                                s['min_scored_first'].append(30)  # Approximate average
                        if ga > 0:
                            if ga > gf or (ga == gf and ga > 0):
                                s['conceded_first'] += 1
                                s['min_conceded_first'].append(35)  # Approximate average
                
                # Add to league averages
                for c in cats:
                    s = team_stats_calc[c]
                    gp = s['gp']
                    if gp > 0:
                        league_avg[c]['ppg'] += s['pts'] / gp
                        league_avg[c]['win_pct'] += (s['w'] / gp) * 100
                        league_avg[c]['draw_pct'] += (s['d'] / gp) * 100
                        league_avg[c]['loss_pct'] += (s['l'] / gp) * 100
                        league_avg[c]['avg_gf'] += s['gf'] / gp
                        league_avg[c]['avg_ga'] += s['ga'] / gp
                        league_avg[c]['cs_pct'] += (s['cs'] / gp) * 100
                        league_avg[c]['fts_pct'] += (s['fts'] / gp) * 100
                        league_avg[c]['wtn_pct'] += (s['wtn'] / gp) * 100
                        league_avg[c]['ltn_pct'] += (s['ltn'] / gp) * 100
                        league_avg[c]['scored_first_pct'] += (s['scored_first'] / gp) * 100
                        league_avg[c]['conceded_first_pct'] += (s['conceded_first'] / gp) * 100
                        if s['min_scored_first']:
                            league_avg[c]['avg_min_scored_first'] += sum(s['min_scored_first']) / len(s['min_scored_first'])
                        if s['min_conceded_first']:
                            league_avg[c]['avg_min_conceded_first'] += sum(s['min_conceded_first']) / len(s['min_conceded_first'])
            
            # Calculate final averages
            for c in cats:
                for key in league_avg[c]:
                    if team_count > 0:
                        league_avg[c][key] = round(league_avg[c][key] / team_count, 2)
                    else:
                        league_avg[c][key] = 0
        
        context['league_avg'] = league_avg

        # --- Player Stats (Top Scorers) ---
        from .models import Player
        from django.db.models import Count
        
        # Get goals for this team in this season
        # Filter matches first to get IDs
        match_ids = [m.id for m in all_matches]
        
        top_scorers = Goal.objects.filter(
            team=team,
            match__id__in=match_ids
        ).values('player_name').annotate(total=Count('id')).order_by('-total')[:15]
        
        # For each scorer, get home/away split (a bit expensive with loop queries but ok for 15 rows)
        players_data = []
        # PPG Calculation
        def calc_ppg(w, d, gp):
            if gp == 0: return 0
            return round(((w * 3) + d) / gp, 2)
        
        stats['home']['ppg'] = calc_ppg(stats['home']['w'], stats['home']['d'], stats['home']['gp'])
        stats['away']['ppg'] = calc_ppg(stats['away']['w'], stats['away']['d'], stats['away']['gp'])
        stats['total']['ppg'] = calc_ppg(stats['total']['w'], stats['total']['d'], stats['total']['gp'])

        # W/D/L Percentages for segmented bars
        for c in cats:
            gp = stats[c]['gp']
            if gp > 0:
                stats[c]['w_pct'] = (stats[c]['w'] / gp) * 100
                stats[c]['d_pct'] = (stats[c]['d'] / gp) * 100
                stats[c]['l_pct'] = (stats[c]['l'] / gp) * 100
            else:
                stats[c]['w_pct'] = stats[c]['d_pct'] = stats[c]['l_pct'] = 0

        total_team_goals = stats['total']['gf']
        
        for p in top_scorers:
            name = p['player_name']
            total = p['total']
            
            # Simple hack: count home/away via Python filtering of specific goal objects?
            # Better: separate aggregation. But for now, let's keep it simple.
            # We can run a second query for home goals.
            home_goals = Goal.objects.filter(team=team, match__id__in=match_ids, player_name=name, match__home_team=team).count()
            away_goals = total - home_goals
            
            # Get Last Goal Date
            last_goal = Goal.objects.filter(team=team, match__id__in=match_ids, player_name=name).select_related('match').order_by('-match__date').first()
            last_goal_date = last_goal.match.date if last_goal and last_goal.match.date else None
            
            # Get Player Details (Age, Nationality)
            player_obj = Player.objects.filter(team=team, name__iexact=name).first()
            age = player_obj.age if player_obj else "-"
            nationality = player_obj.nationality if player_obj else None

            players_data.append({
                'name': name,
                'total': total,
                'home': home_goals,
                'away': away_goals,
                'last_date': last_goal_date,
                'age': age,
                'nationality': nationality,
                'pct': round((total / total_team_goals * 100)) if total_team_goals > 0 else 0
            })
            
        context['top_scorers'] = players_data
        
        # --- League Standings (Results Table) ---
        standings_qs = LeagueStanding.objects.filter(
            league=league,
            season=latest_season
        ).select_related('team').order_by('position')[:20]
        
        # Prepare h2h data for the standings table
        h2h_map = {}
        # We use all_matches which is already filtered for just our team and already selected above
        for m in all_matches:
            if m.home_team == team:
                h2h_map.setdefault(m.away_team_id, {})['home'] = m
            else:
                h2h_map.setdefault(m.home_team_id, {})['away'] = m
        
        league_h2h = []
        for st in standings_qs:
            opp_id = st.team_id
            m_h = h2h_map.get(opp_id, {}).get('home')
            m_a = h2h_map.get(opp_id, {}).get('away')
            
            def format_h2h(m, is_home):
                if not m: return {'score': '-', 'bg': ''}
                if m.home_score is None: 
                    return {'score': m.date.strftime('%d %b'), 'bg': ''}
                
                # Check result from our team's view
                if is_home:
                    won = m.home_score > m.away_score
                    lost = m.home_score < m.away_score
                else:
                    won = m.away_score > m.home_score
                    lost = m.away_score < m.home_score
                
                bg = 'row-win' if won else ('row-loss' if lost else 'row-draw')
                return {'score': f"{m.home_score}:{m.away_score}", 'bg': bg}

            # Determine best match for H2H link (most recent)
            matches_pair = [m for m in [m_h, m_a] if m]
            matches_pair.sort(key=lambda x: x.date, reverse=True)
            last_match = matches_pair[0] if matches_pair else None

            league_h2h.append({
                'standing': st,
                'home': format_h2h(m_h, True),
                'away': format_h2h(m_a, False),
                'match_link': {'id': last_match.id, 'slug': last_match.slug} if last_match else None
            })

        context['league_h2h'] = league_h2h
        context['thresholds'] = thresholds
        context['cats'] = cats

        # --- NEW: Current Streaks ---
        context['streaks'] = self.calculate_streaks(all_matches, team)

        # Helper to calculate stats for a given season and matches
        def calc_historical(matches_qs, t):
            stats = {'pld': 0, 'pts': 0, 'gf': 0, 'ga': 0, 'w': 0, 'd': 0, 'l': 0, 'cs': 0, 'fts': 0}
            if not matches_qs: return stats
            stats['pld'] = len(matches_qs)
            for m in matches_qs:
                is_home = m.home_team == t
                my_score = m.home_score if is_home else m.away_score
                opp_score = m.away_score if is_home else m.home_score
                
                if my_score is None or opp_score is None: continue # Skip played but no score? (status check done in filter)
                
                stats['gf'] += my_score
                stats['ga'] += opp_score
                
                if my_score > opp_score: 
                    stats['w'] += 1
                    stats['pts'] += 3
                elif my_score == opp_score: 
                    stats['d'] += 1
                    stats['pts'] += 1
                else: 
                    stats['l'] += 1
                    
                if opp_score == 0: stats['cs'] += 1
                if my_score == 0: stats['fts'] += 1
            
            # Averages/Percents
            if stats['pld'] > 0:
                stats['avg_pts'] = stats['pts'] / stats['pld']
                stats['avg_gf'] = stats['gf'] / stats['pld']
                stats['avg_ga'] = stats['ga'] / stats['pld']
                stats['w_pct'] = int((stats['w'] / stats['pld']) * 100)
                stats['d_pct'] = int((stats['d'] / stats['pld']) * 100)
                stats['l_pct'] = int((stats['l'] / stats['pld']) * 100)
                stats['cs_pct'] = int((stats['cs'] / stats['pld']) * 100)
                stats['fts_pct'] = int((stats['fts'] / stats['pld']) * 100)
            return stats

        # Current Season Stats (ALWAYS CALCULATED)
        current_stats = {
            'overall': calc_historical(all_matches, team),
            'home': calc_historical([m for m in all_matches if m.home_team == team], team),
            'away': calc_historical([m for m in all_matches if m.away_team == team], team)
        }
        
        # Historical Statistics (Current vs Prev Season)
        previous_stats = None
        season_name = f"{latest_season.year-1}/{latest_season.year}" if latest_season else "-"
        prev_season_name = "-"

        if past_seasons:
            prev_season = past_seasons[0] # Assuming ordered by -year
            
            # Previous Season Stats
            prev_matches = Match.objects.filter(
                models.Q(home_team=team) | models.Q(away_team=team),
                season=prev_season,
                status__in=FINISHED_STATUSES
            )
            previous_stats = {
                'overall': calc_historical(prev_matches, team),
                'home': calc_historical([m for m in prev_matches if m.home_team == team], team),
                'away': calc_historical([m for m in prev_matches if m.away_team == team], team)
            }
            prev_season_name = f"{prev_season.year-1}/{prev_season.year}"
            
            context['historical_stats'] = {
                'current': current_stats,
                'previous': previous_stats,
                'season_name': season_name,
                'prev_season_name': prev_season_name
            }

        # --- Upcoming Matches & Run-in Analysis ---
        upcoming_matches = Match.objects.filter(
            models.Q(home_team=team) | models.Q(away_team=team),
            status='Scheduled',
            date__gte=datetime.now()
        ).order_by('date')
        
        run_in_data = []
        sum_opp_ppg_home = 0
        sum_opp_ppg_away = 0
        remaining_home = 0
        remaining_away = 0

        # Helper to get opponent PPG (using current season stats)
        # We need a robust way to get opponent stats. 
        # Ideally, we'd have a helper method or cache. 
        # For now, let's just calc it on the fly or use a simplified approach.
        # IMPROVEMENT: Use the 'current_stats' logic but for opponent.
        
        def get_team_ppg(t, is_home_venue):
             # Calculate opponent stats for specific venue
            opp_matches = Match.objects.filter(season=latest_season, status__in=FINISHED_STATUSES)
            if is_home_venue:
                opp_matches = opp_matches.filter(home_team=t)
                pts = 0
                pld = 0
                for om in opp_matches:
                    pld += 1
                    if om.home_score > om.away_score: pts += 3
                    elif om.home_score == om.away_score: pts += 1
                return round(pts / pld, 2) if pld > 0 else 0
            else:
                opp_matches = opp_matches.filter(away_team=t)
                pts = 0
                pld = 0
                for om in opp_matches:
                    pld += 1
                    if om.away_score > om.home_score: pts += 3
                    elif om.away_score == om.home_score: pts += 1
                return round(pts / pld, 2) if pld > 0 else 0

        for m in upcoming_matches:
            is_home = m.home_team == team
            opponent = m.away_team if is_home else m.home_team
            
            # Context: Stats for US
            my_stats = current_stats['home'] if is_home else current_stats['away']
            my_ppg = my_stats.get('avg_pts', 0)
            
            # Context: Stats for OPPONENT
            # If we are Home, Opponent is Away. We want Opponent's Away PPG.
            opp_venue_is_home = not is_home
            opp_ppg = get_team_ppg(opponent, opp_venue_is_home)
            
            # For table columns
            if is_home:
                col_home_ppg = f"{my_ppg:.2f}"
                col_away_ppg = f"{opp_ppg:.2f}"
                remaining_home += 1
                sum_opp_ppg_home += opp_ppg
            else:
                col_home_ppg = f"{opp_ppg:.2f}"
                col_away_ppg = f"{my_ppg:.2f}"
                remaining_away += 1
                sum_opp_ppg_away += opp_ppg

            run_in_data.append({
                'match': m,
                'is_home': is_home,
                'opponent': opponent,
                'col_home_ppg': col_home_ppg,
                'col_away_ppg': col_away_ppg,
                'opp_strength_pct': min(100, int((opp_ppg / 3.0) * 100))
            })

        avg_opp_ppg_home = round(sum_opp_ppg_home / remaining_home, 2) if remaining_home > 0 else 0
        avg_opp_ppg_away = round(sum_opp_ppg_away / remaining_away, 2) if remaining_away > 0 else 0
        avg_total_opp_ppg = round((sum_opp_ppg_home + sum_opp_ppg_away) / (remaining_home + remaining_away), 2) if (remaining_home + remaining_away) > 0 else 0

        context['run_in'] = {
            'matches': run_in_data,
            'avg_opp_ppg_home': avg_opp_ppg_home,
            'avg_opp_ppg_away': avg_opp_ppg_away,
            'avg_total_opp_ppg': avg_total_opp_ppg,
            'analysis': "Analysis placeholder..." # We can elaborate this later or use the template logic
        }

        # Calculate streaks
        context['streaks'] = self.calculate_streaks(all_matches, team)

        return context

    def calculate_streaks(self, all_matches_qs, team):
        # We need finished matches sorted by date (most recent LAST) to iterate backwards easily
        # or most recent FIRST. Let's ensure order.
        # all_matches_qs is ordered by 'date' (asc)
        
        matches = [m for m in all_matches_qs if m.status == 'Finished' and m.home_score is not None]
        
        # Helper to get streaks
        def get_seq(match_list, condition_func):
            count = 0
            # Iterate backwards (newest to oldest)
            for m in reversed(match_list):
                if condition_func(m):
                    count += 1
                else:
                    break
            return count

        home_matches = [m for m in matches if m.home_team == team]
        away_matches = [m for m in matches if m.away_team == team]
        
        categories = {'total': matches, 'home': home_matches, 'away': away_matches}
        result = {}

        for cat, m_list in categories.items():
            # Define conditions
            # Helper for scores to handle None
            def scores(m):
                h = m.home_score if m.home_score is not None else 0
                a = m.away_score if m.away_score is not None else 0
                return (h, a)

            is_win = lambda m: (m.home_team == team and scores(m)[0] > scores(m)[1]) or \
                               (m.away_team == team and scores(m)[1] > scores(m)[0])
            
            is_draw = lambda m: scores(m)[0] == scores(m)[1]
            
            is_loss = lambda m: (m.home_team == team and scores(m)[0] < scores(m)[1]) or \
                                (m.away_team == team and scores(m)[1] < scores(m)[0])
            
            # No Win (Draw or Loss) -> NOT Win
            is_no_win = lambda m: not is_win(m)
            
            # No Draw -> Win or Loss
            is_no_draw = lambda m: not is_draw(m)
            
            # No Defeat -> Win or Draw
            is_no_defeat = lambda m: not is_loss(m)
            
            # 1 goal or more (Scored)
            scored_1plus = lambda m: (scores(m)[0] if m.home_team == team else scores(m)[1]) >= 1
            
            # 1 goal conceded or more
            conceded_1plus = lambda m: (scores(m)[1] if m.home_team == team else scores(m)[0]) >= 1
            
            # No goal scored (0)
            no_goal_scored = lambda m: (scores(m)[0] if m.home_team == team else scores(m)[1]) == 0
            
            # No goal conceded (Clean Sheet)
            no_goal_conceded = lambda m: (scores(m)[1] if m.home_team == team else scores(m)[0]) == 0
            
            # GF+GA over 2.5
            over_25 = lambda m: sum(scores(m)) > 2.5
            
            # GF+GA under 2.5
            under_25 = lambda m: sum(scores(m)) < 2.5
            
            # Scored at least twice
            scored_2plus = lambda m: (scores(m)[0] if m.home_team == team else scores(m)[1]) >= 2

            result[cat] = {
                'win': get_seq(m_list, is_win),
                'draw': get_seq(m_list, is_draw),
                'loss': get_seq(m_list, is_loss),
                'no_win': get_seq(m_list, is_no_win),
                'no_draw': get_seq(m_list, is_no_draw),
                'no_defeat': get_seq(m_list, is_no_defeat),
                'scored_1plus': get_seq(m_list, scored_1plus),
                'conceded_1plus': get_seq(m_list, conceded_1plus),
                'no_goal_scored': get_seq(m_list, no_goal_scored),
                'no_goal_conceded': get_seq(m_list, no_goal_conceded),
                'over_25': get_seq(m_list, over_25),
                'under_25': get_seq(m_list, under_25),
                'scored_2plus': get_seq(m_list, scored_2plus),
            }
            
        return result




class LeagueGoalsView(TemplateView):
    template_name = 'matches/league_goals.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        league_slug = self.kwargs.get('league_name')
        stats_type = self.request.GET.get('type', 'total')
        ht_stats_type = self.request.GET.get('ht_type', 'total')
        bts_type = self.request.GET.get('bts_type', 'total')
        cs_type = self.request.GET.get('cs_type', 'total')
        fts_type = self.request.GET.get('fts_type', 'total')
        wtn_type = self.request.GET.get('wtn_type', 'total')
        
        context['stats_type'] = stats_type
        context['ht_stats_type'] = ht_stats_type
        context['bts_type'] = bts_type
        context['cs_type'] = cs_type
        context['fts_type'] = fts_type
        context['wtn_type'] = wtn_type
        
        # Get League
        name_query = league_slug.replace('-', ' ')
        
        # New Logic: Prioritize League with Data (Standings)
        # annotations allow us to count related objects
        from django.db.models import Count
        
        candidates = League.objects.filter(name__iexact=name_query).annotate(s_count=Count('standings')).order_by('-s_count')
        if not candidates.exists():
             candidates = League.objects.filter(name__icontains=name_query).annotate(s_count=Count('standings')).order_by('-s_count')
        
        league = candidates.first()
        
        context['league'] = league
        if not league:
            return context

        # Get Latest Season
        latest_season = Season.objects.filter(standings__league=league).order_by('-year').first()
        context['season'] = latest_season

        # Get Standings
        if latest_season:
            standings = LeagueStanding.objects.filter(
                league=league,
                season=latest_season
            ).select_related('team').order_by('position')
        else:
            standings = LeagueStanding.objects.none()
        context['standings'] = standings
        
        # Get all finished matches ordered by date
        if latest_season:
            matches = Match.objects.filter(
                league=league, 
                season=latest_season, 
                status__in=FINISHED_STATUSES
            ).select_related('home_team', 'away_team').order_by('date')
        else:
            matches = Match.objects.filter(
                league=league, 
                status__in=FINISHED_STATUSES
            ).select_related('home_team', 'away_team').order_by('date')

        # Helper to init stats
        def init_stats():
            return {
                'gp': 0, 'gf': 0, 'ga': 0, 'total_goals': 0,
                'over05': 0, 'over15': 0, 'over25': 0, 'over35': 0, 'over45': 0, 'over55': 0,
                'bts': 0, 'cs': 0, 'fts': 0, 'wtn': 0, 'ltn': 0
            }

        # Organize matches by team
        # Store as list of (match, side) tuples
        # side is 'home' or 'away'
        team_matches = {}
        
        for m in matches:
            h_id = m.home_team.id
            a_id = m.away_team.id
            
            if h_id not in team_matches:
                team_matches[h_id] = {'team': m.home_team, 'matches': []}
            if a_id not in team_matches:
                team_matches[a_id] = {'team': m.away_team, 'matches': []}
                
            team_matches[h_id]['matches'].append((m, 'home'))
            team_matches[a_id]['matches'].append((m, 'away'))

        # --- New Tables Overview Calculation ---
        
        # 1. Define ranking containers
        # We need 12 lists
        rank_points = []
        rank_form8 = []
        rank_home = []
        rank_away = []
        
        rank_offence = []
        rank_defence = []
        rank_offence8 = []
        rank_defence8 = []
        
        rank_offence_home = []
        rank_defence_home = []
        rank_offence_away = []
        rank_defence_away = []
        
        # Helper to calc simple stats for a list of matches
        def calc_mini_stats(match_list, side_filter=None):
            # side_filter: 'home', 'away', or None (all)
            stats = {'gp': 0, 'pts': 0, 'gf': 0, 'ga': 0}
            for m, side in match_list:
                if side_filter and side != side_filter:
                    continue
                
                is_home = (side == 'home')
                my_score = m.home_score if is_home else m.away_score
                opp_score = m.away_score if is_home else m.home_score
                
                if my_score is None: my_score = 0
                if opp_score is None: opp_score = 0
                
                stats['gp'] += 1
                stats['gf'] += my_score
                stats['ga'] += opp_score
                
                if my_score > opp_score:
                    stats['pts'] += 3
                elif my_score == opp_score:
                    stats['pts'] += 1
            return stats

        for t_id, data in team_matches.items():
            team = data['team']
            matches = data['matches'] # Sorted by date ascending
            
            # Re-sort matches by date descending for "last 8" slicing
            matches_desc = sorted(matches, key=lambda x: x[0].date if x[0].date else datetime.min, reverse=True)
            
            # 1. Points (All matches)
            s = calc_mini_stats(matches)
            if s['gp'] > 0:
                rank_points.append({'team': team, 'gp': s['gp'], 'val': s['pts']})
            
            # 2. Form (Last 8)
            s = calc_mini_stats(matches_desc[:8])
            if s['gp'] > 0:
                rank_form8.append({'team': team, 'gp': s['gp'], 'val': s['pts']})
                
            # 3. Home
            s = calc_mini_stats(matches, 'home')
            if s['gp'] > 0:
                rank_home.append({'team': team, 'gp': s['gp'], 'val': s['pts']})
                
            # 4. Away
            s = calc_mini_stats(matches, 'away')
            if s['gp'] > 0:
                rank_away.append({'team': team, 'gp': s['gp'], 'val': s['pts']})
            
            # 5. Offence (All)
            s = calc_mini_stats(matches)
            if s['gp'] > 0:
                rank_offence.append({'team': team, 'gp': s['gp'], 'val': s['gf']})
                
            # 6. Defence (All)
            if s['gp'] > 0:
                rank_defence.append({'team': team, 'gp': s['gp'], 'val': s['ga']})
                
            # 7. Offence (Last 8)
            s = calc_mini_stats(matches_desc[:8])
            if s['gp'] > 0:
                rank_offence8.append({'team': team, 'gp': s['gp'], 'val': s['gf']})
                
            # 8. Defence (Last 8)
            if s['gp'] > 0:
                rank_defence8.append({'team': team, 'gp': s['gp'], 'val': s['ga']})
                
            # 9. Offence (Home)
            s = calc_mini_stats(matches, 'home')
            if s['gp'] > 0:
                rank_offence_home.append({'team': team, 'gp': s['gp'], 'val': s['gf']})
            
            # 10. Defence (Home)
            if s['gp'] > 0:
                rank_defence_home.append({'team': team, 'gp': s['gp'], 'val': s['ga']})
                
            # 11. Offence (Away)
            s = calc_mini_stats(matches, 'away')
            if s['gp'] > 0:
                rank_offence_away.append({'team': team, 'gp': s['gp'], 'val': s['gf']})
                
            # 12. Defence (Away)
            if s['gp'] > 0:
                rank_defence_away.append({'team': team, 'gp': s['gp'], 'val': s['ga']})

        # Sorting
        # Descending for Points, GF
        # Ascending for GA (Defence)
        
        rank_points.sort(key=lambda x: x['val'], reverse=True)
        rank_form8.sort(key=lambda x: x['val'], reverse=True)
        rank_home.sort(key=lambda x: x['val'], reverse=True)
        rank_away.sort(key=lambda x: x['val'], reverse=True)
        
        rank_offence.sort(key=lambda x: x['val'], reverse=True)
        rank_defence.sort(key=lambda x: x['val']) # Low is good
        
        rank_offence8.sort(key=lambda x: x['val'], reverse=True)
        rank_defence8.sort(key=lambda x: x['val'])
        
        rank_offence_home.sort(key=lambda x: x['val'], reverse=True)
        rank_defence_home.sort(key=lambda x: x['val'])
        
        rank_offence_away.sort(key=lambda x: x['val'], reverse=True)
        rank_defence_away.sort(key=lambda x: x['val'])
        
        # Group into overview tables for template iteration
        overview_tables = [
            {'title': 'Points', 'rows': rank_points, 'col_label': 'pts', 'col_key': 'val', 'header_color': '#333'},
            {'title': 'Form (last 8)', 'rows': rank_form8, 'col_label': 'pts', 'col_key': 'val', 'header_color': '#333'},
            {'title': 'Home', 'rows': rank_home, 'col_label': 'pts', 'col_key': 'val', 'header_color': '#333'},
            {'title': 'Away', 'rows': rank_away, 'col_label': 'pts', 'col_key': 'val', 'header_color': '#333'},
            {'title': 'Offence', 'rows': rank_offence, 'col_label': 'GF', 'col_key': 'val', 'header_color': '#1e40af'},
            {'title': 'Defence', 'rows': rank_defence, 'col_label': 'GA', 'col_key': 'val', 'header_color': '#dc2626'},
            
            {'title': 'Offence (last 8)', 'rows': rank_offence8, 'col_label': 'GF', 'col_key': 'val', 'header_color': '#1e40af'},
            {'title': 'Defence (last 8)', 'rows': rank_defence8, 'col_label': 'GA', 'col_key': 'val', 'header_color': '#dc2626'},
            {'title': 'Offence (home)', 'rows': rank_offence_home, 'col_label': 'GF', 'col_key': 'val', 'header_color': '#1e40af'},
            {'title': 'Defence (home)', 'rows': rank_defence_home, 'col_label': 'GA', 'col_key': 'val', 'header_color': '#dc2626'},
            {'title': 'Offence (away)', 'rows': rank_offence_away, 'col_label': 'GF', 'col_key': 'val', 'header_color': '#1e40af'},
            {'title': 'Defence (away)', 'rows': rank_defence_away, 'col_label': 'GA', 'col_key': 'val', 'header_color': '#dc2626'},
        ]
        context['overview_tables'] = overview_tables

        # Aggregate Stats per Team
        rows = []
        ht_rows = []
        bts_rows = []
        cs_rows = []
        fts_rows = []
        wtn_rows = []
        league_totals = init_stats()
        ht_league_totals = init_stats()

        for t_id, data in team_matches.items():
            team = data['team']
            all_matches = data['matches']
            
            # --- Full Time Stats Calculation ---
            ft_matches = all_matches[:]
            if stats_type == 'last8':
                ft_matches = ft_matches[-8:]
            
            s = init_stats()
            for m, side in ft_matches:
                if stats_type == 'home' and side != 'home': continue
                if stats_type == 'away' and side != 'away': continue
                
                is_home = (side == 'home')
                my_score = m.home_score if is_home else m.away_score
                opp_score = m.away_score if is_home else m.home_score
                
                if my_score is None: my_score = 0
                if opp_score is None: opp_score = 0
                
                total_g = my_score + opp_score
                bts_val = (my_score > 0 and opp_score > 0)
                
                s['gp'] += 1
                s['gf'] += my_score
                s['ga'] += opp_score
                s['total_goals'] += total_g
                
                if total_g > 0.5: s['over05'] += 1
                if total_g > 1.5: s['over15'] += 1
                if total_g > 2.5: s['over25'] += 1
                if total_g > 3.5: s['over35'] += 1
                if total_g > 4.5: s['over45'] += 1
                if total_g > 5.5: s['over55'] += 1
                
                if bts_val: s['bts'] += 1
                if opp_score == 0: s['cs'] += 1
                if my_score == 0: s['fts'] += 1
                
                if my_score > opp_score and opp_score == 0: s['wtn'] += 1
                if my_score < opp_score and my_score == 0: s['ltn'] += 1

            # --- Half Time Stats Calculation ---
            ht_matches = all_matches[:]
            if ht_stats_type == 'last8':
                ht_matches = ht_matches[-8:]

            ht_s = init_stats()
            for m, side in ht_matches:
                if ht_stats_type == 'home' and side != 'home': continue
                if ht_stats_type == 'away' and side != 'away': continue

                is_home = (side == 'home')
                ht_my = m.ht_home_score if is_home else m.ht_away_score
                ht_opp = m.ht_away_score if is_home else m.ht_home_score

                if ht_my is None: ht_my = 0
                if ht_opp is None: ht_opp = 0

                ht_total = ht_my + ht_opp
                ht_bts = (ht_my > 0 and ht_opp > 0)

                ht_s['gp'] += 1
                ht_s['gf'] += ht_my
                ht_s['ga'] += ht_opp
                ht_s['total_goals'] += ht_total

                if ht_total > 0.5: ht_s['over05'] += 1
                if ht_total > 1.5: ht_s['over15'] += 1
                if ht_total > 2.5: ht_s['over25'] += 1
                if ht_total > 3.5: ht_s['over35'] += 1
                if ht_total > 4.5: ht_s['over45'] += 1
                if ht_total > 5.5: ht_s['over55'] += 1

                if ht_bts: ht_s['bts'] += 1
                if ht_opp == 0: ht_s['cs'] += 1
                if ht_my == 0: ht_s['fts'] += 1
                
                if ht_my > ht_opp and ht_opp == 0: ht_s['wtn'] += 1
                if ht_my < ht_opp and ht_my == 0: ht_s['ltn'] += 1

            # --- BTS Stats Calculation (New) ---
            bts_s = init_stats()
            for m, side in all_matches:
                 if bts_type == 'home' and side != 'home': continue
                 if bts_type == 'away' and side != 'away': continue
                 
                 is_home = (side == 'home')
                 my_score = m.home_score if is_home else m.away_score
                 opp_score = m.away_score if is_home else m.home_score
                 if my_score is None: my_score = 0
                 if opp_score is None: opp_score = 0
                 
                 if my_score > 0 and opp_score > 0:
                     bts_s['bts'] += 1
                 bts_s['gp'] += 1

            # --- CS Stats Calculation (New) ---
            cs_s = init_stats()
            for m, side in all_matches:
                 if cs_type == 'home' and side != 'home': continue
                 if cs_type == 'away' and side != 'away': continue
                 
                 is_home = (side == 'home')
                 opp_score = m.away_score if is_home else m.home_score
                 if opp_score is None: opp_score = 0
                 
                 if opp_score == 0:
                     cs_s['cs'] += 1
                 cs_s['gp'] += 1

            # --- FTS Stats Calculation (New) ---
            fts_s = init_stats()
            for m, side in all_matches:
                 if fts_type == 'home' and side != 'home': continue
                 if fts_type == 'away' and side != 'away': continue
                 
                 is_home = (side == 'home')
                 my_score = m.home_score if is_home else m.away_score
                 if my_score is None: my_score = 0
                 
                 if my_score == 0:
                     fts_s['fts'] += 1
                 fts_s['gp'] += 1

            # --- WTN Stats Calculation (Now: Scored in Both Halves - SBH) ---
            # Keeping variable name 'wtn' to avoid massive refactor, but logic is SBH
            wtn_s = init_stats()
            for m, side in all_matches:
                 if wtn_type == 'home' and side != 'home': continue
                 if wtn_type == 'away' and side != 'away': continue
                 
                 is_home = (side == 'home')
                 
                 # Full Time Score
                 my_score = m.home_score if is_home else m.away_score
                 if my_score is None: my_score = 0
                 
                 # Half Time Score
                 my_ht_score = m.ht_home_score if is_home else m.ht_away_score
                 if my_ht_score is None: my_ht_score = 0
                 
                 # 2nd Half Score
                 my_2h_score = my_score - my_ht_score
                 
                 # Scored in Both Halves Logic: >0 in 1st AND >0 in 2nd
                 if my_ht_score > 0 and my_2h_score > 0:
                     wtn_s['wtn'] += 1
                 wtn_s['gp'] += 1

            gp = s['gp']
            if gp == 0: continue
            
            # Helper to create row dict
            def make_row(team_obj, stats_dict):
                g_played = stats_dict['gp']
                if g_played == 0: return None
                return {
                    'team': team_obj,
                    'gp': g_played,
                    'avg_total': stats_dict['total_goals'] / g_played,
                    'over05_pct': (stats_dict['over05'] / g_played) * 100,
                    'over15_pct': (stats_dict['over15'] / g_played) * 100,
                    'over25_pct': (stats_dict['over25'] / g_played) * 100,
                    'over35_pct': (stats_dict['over35'] / g_played) * 100,
                    'over45_pct': (stats_dict['over45'] / g_played) * 100,
                    'over55_pct': (stats_dict['over55'] / g_played) * 100,
                    'bts_pct': (stats_dict['bts'] / g_played) * 100,
                    'cs_pct': (stats_dict['cs'] / g_played) * 100,
                    'fts_pct': (stats_dict['fts'] / g_played) * 100,
                    'wtn_pct': (stats_dict['wtn'] / g_played) * 100,
                    'ltn_pct': (stats_dict['ltn'] / g_played) * 100,
                }

            row = make_row(team, s)
            if row: rows.append(row)

            ht_row = make_row(team, ht_s)
            if ht_row: ht_rows.append(ht_row)

            # BTS Row
            if bts_s['gp'] > 0:
                bts_rows.append({
                    'team': team,
                    'gp': bts_s['gp'],
                    'bts': bts_s['bts'],
                    'bts_pct': (bts_s['bts'] / bts_s['gp']) * 100
                })

            # CS Row
            if cs_s['gp'] > 0:
                cs_rows.append({
                    'team': team,
                    'gp': cs_s['gp'],
                    'cs': cs_s['cs'],
                    'cs_pct': (cs_s['cs'] / cs_s['gp']) * 100
                })
            
            # FTS Row
            if fts_s['gp'] > 0:
                fts_rows.append({
                    'team': team,
                    'gp': fts_s['gp'],
                    'fts': fts_s['fts'],
                    'fts_pct': (fts_s['fts'] / fts_s['gp']) * 100
                })

            # WTN Row
            if wtn_s['gp'] > 0:
                wtn_rows.append({
                    'team': team,
                    'gp': wtn_s['gp'],
                    'wtn': wtn_s['wtn'],
                    'wtn_pct': (wtn_s['wtn'] / wtn_s['gp']) * 100
                })

            # League Totals Accumulation
            for k in league_totals:
                league_totals[k] += s[k]
                ht_league_totals[k] += ht_s[k]

        # Sort by Avg Total Goals Descending
        rows.sort(key=lambda x: x['avg_total'], reverse=True)
        ht_rows.sort(key=lambda x: x['avg_total'], reverse=True)
        
        # Sort BTS and CS
        bts_rows.sort(key=lambda x: x['bts'], reverse=True)
        cs_rows.sort(key=lambda x: x['cs'], reverse=True)
        fts_rows.sort(key=lambda x: x['fts'], reverse=True)
        wtn_rows.sort(key=lambda x: x['wtn'], reverse=True)
        
        # Calculate League Average Row
        def make_league_avg(totals_dict):
            lg_gp = totals_dict['gp']
            if lg_gp > 0:
                return {
                    'team_name': 'League average',
                    'gp': lg_gp, 
                    'avg_total': totals_dict['total_goals'] / lg_gp,
                    'over05_pct': (totals_dict['over05'] / lg_gp) * 100,
                    'over15_pct': (totals_dict['over15'] / lg_gp) * 100,
                    'over25_pct': (totals_dict['over25'] / lg_gp) * 100,
                    'over35_pct': (totals_dict['over35'] / lg_gp) * 100,
                    'over45_pct': (totals_dict['over45'] / lg_gp) * 100,
                    'over55_pct': (totals_dict['over55'] / lg_gp) * 100,
                    'bts_pct': (totals_dict['bts'] / lg_gp) * 100,
                    'cs_pct': (totals_dict['cs'] / lg_gp) * 100,
                    'fts_pct': (totals_dict['fts'] / lg_gp) * 100,
                    'wtn_pct': (totals_dict['wtn'] / lg_gp) * 100,
                    'ltn_pct': (totals_dict['ltn'] / lg_gp) * 100,
                }
            return {}

        context['goal_stats_rows'] = rows
        context['league_avg_row'] = make_league_avg(league_totals)
        
        context['ht_goal_stats_rows'] = ht_rows
        context['ht_league_avg_row'] = make_league_avg(ht_league_totals)
        
        context['bts_rows'] = bts_rows
        context['cs_rows'] = cs_rows
        context['fts_rows'] = fts_rows
        context['wtn_rows'] = wtn_rows
        
        # --- General League Stats (for the new container) ---
        # Re-fetch all_matches as a queryset to ensure it's not a list of tuples
        all_matches_qs = Match.objects.filter(
            league=league,
            season=latest_season,
            status__in=FINISHED_STATUSES
        ).prefetch_related('goals', 'home_team', 'away_team')
        total_matches_played = all_matches_qs.count()
        total_season_matches = 380 # Assuming a standard 20-team league
        
        home_wins = 0
        away_wins = 0
        draws = 0
        total_goals = 0
        over_1_5 = 0
        over_2_5 = 0
        over_3_5 = 0
        btts_yes = 0
        home_goals_total = 0
        away_goals_total = 0
        no_goal_scored = 0

        # First Goal Stats
        home_scored_first = 0
        away_scored_first = 0
        home_first_goal_mins = []
        away_first_goal_mins = []

        # New: Correct Score & Timing
        correct_score_counts = {}
        timing_counts = {
            '0-15': 0, '16-30': 0, '31-45': 0,
            '46-60': 0, '61-75': 0, '76-90+': 0
        }

        for m in all_matches_qs:
            if m.home_score is not None and m.away_score is not None:
                total_goals += m.home_score + m.away_score
                home_goals_total += m.home_score
                away_goals_total += m.away_score

                # Correct Score
                score_str = f"{m.home_score}-{m.away_score}"
                correct_score_counts[score_str] = correct_score_counts.get(score_str, 0) + 1

                if m.home_score == 0 and m.away_score == 0:
                    no_goal_scored += 1

                # Determine who scored first & Timing
                match_goals = list(m.goals.all())
                # Sort by minute just in case, though usually insertion order or Meta ordering handles it
                # Assuming Meta ordering might not be set for minute, let's sort
                match_goals.sort(key=lambda g: g.minute)
                
                for g in match_goals:
                    # Timing
                    minute = g.minute
                    if minute <= 15: timing_counts['0-15'] += 1
                    elif minute <= 30: timing_counts['16-30'] += 1
                    elif minute <= 45: timing_counts['31-45'] += 1
                    elif minute <= 60: timing_counts['46-60'] += 1
                    elif minute <= 75: timing_counts['61-75'] += 1
                    else: timing_counts['76-90+'] += 1

                if match_goals:
                    first_goal = match_goals[0]
                    # Check if home or away team scored first
                    if first_goal.team_id == m.home_team_id:
                        home_scored_first += 1
                        home_first_goal_mins.append(first_goal.minute)
                    elif first_goal.team_id == m.away_team_id:
                        away_scored_first += 1
                        away_first_goal_mins.append(first_goal.minute)

                if m.home_score > m.away_score:
                    home_wins += 1
                elif m.away_score > m.home_score:
                    away_wins += 1
                else:
                    draws += 1

                if (m.home_score + m.away_score) > 1.5:
                    over_1_5 += 1
                if (m.home_score + m.away_score) > 2.5:
                    over_2_5 += 1
                if (m.home_score + m.away_score) > 3.5:
                    over_3_5 += 1
                
                if m.home_score > 0 and m.away_score > 0:
                    btts_yes += 1

        # Calculate Averages for First Goal Minutes
        avg_home_first_min = sum(home_first_goal_mins) / len(home_first_goal_mins) if home_first_goal_mins else 0
        avg_away_first_min = sum(away_first_goal_mins) / len(away_first_goal_mins) if away_first_goal_mins else 0

        # Process Correct Score Stats
        sorted_scores = sorted(correct_score_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        correct_score_stats = []
        for score, count in sorted_scores:
            correct_score_stats.append({
                'score': score,
                'count': count,
                'pct': (count / total_matches_played) * 100 if total_matches_played > 0 else 0
            })
        context['correct_score_stats'] = correct_score_stats

        # Process Timing Stats
        total_goals_timing = sum(timing_counts.values())
        timing_stats_list = []
        for period in ['0-15', '16-30', '31-45', '46-60', '61-75', '76-90+']:
            count = timing_counts.get(period, 0)
            timing_stats_list.append({
                'period': period,
                'count': count,
                'pct': (count / total_goals_timing) * 100 if total_goals_timing > 0 else 0
            })
        context['timing_stats_list'] = timing_stats_list

        # Prepare context data
        if total_matches_played > 0:
            context['league_stats'] = {
                'matches_played': total_matches_played,
                'total_season_matches': total_season_matches,
                'matches_played_pct': (total_matches_played / total_season_matches) * 100 if total_season_matches > 0 else 0,
                'home_wins_pct': (home_wins / total_matches_played) * 100,
                'draws_pct': (draws / total_matches_played) * 100,
                'away_wins_pct': (away_wins / total_matches_played) * 100,
                'total_goals': total_goals,
                'goals_per_match': total_goals / total_matches_played,
                'over_1_5_pct': (over_1_5 / total_matches_played) * 100,
                'over_2_5_pct': (over_2_5 / total_matches_played) * 100,
                'over_3_5_pct': (over_3_5 / total_matches_played) * 100,
                'btts_pct': (btts_yes / total_matches_played) * 100,
                'no_goal_scored_pct': (no_goal_scored / total_matches_played) * 100,
                'home_goals_per_match': home_goals_total / total_matches_played,
                'away_goals_per_match': away_goals_total / total_matches_played,
                
                # First Goal Stats
                'home_scored_first_pct': (home_scored_first / total_matches_played) * 100,
                'away_scored_first_pct': (away_scored_first / total_matches_played) * 100,
                'avg_home_first_min': avg_home_first_min,
                'avg_away_first_min': avg_away_first_min,
            }
        else:
            # Default empty state
            context['league_stats'] = {
                'matches_played': 0, 'total_season_matches': total_season_matches, 'matches_played_pct': 0,
                'home_wins_pct': 0, 'draws_pct': 0, 'away_wins_pct': 0, 'total_goals': 0,
                'goals_per_match': 0, 'over_1_5_pct': 0, 'over_2_5_pct': 0, 'over_3_5_pct': 0,
                'btts_pct': 0, 'no_goal_scored_pct': 0, 'home_goals_per_match': 0, 'away_goals_per_match': 0,
                'home_scored_first_pct': 0, 'away_scored_first_pct': 0, 'avg_home_first_min': 0, 'avg_away_first_min': 0,
            }

        # --- Segments Table Logic ---
        segments_data = []
        if standings.exists():
            max_pts = standings[0].points
            if max_pts > 0:
                step = max_pts / 5.0
                # Initialize 5 segments (0: Lowest/5th, 4: Highest/1st)
                # Display order will be 5th -> 1st (Low -> High)
                segments = [{'teams': [], 'min': i*step, 'max': (i+1)*step, 'rank': 5-i} for i in range(5)]
                
                for standing in standings:
                    p = standing.points
                    idx = int(p / step)
                    if idx >= 5: idx = 4 # Cap at max
                    # If points exactly 0? int(0) = 0. Correct.
                    # If points close to boundary? 9.99 / 10 = 0. 10.0 / 10 = 1.
                    # Boundary check: strict inequality?
                    # The standard: [0, step), [step, 2step)... [4step, 5step]
                    # int() behaves like floor.
                    # 50/10 = 5. -> index 4.
                    # 49/10 = 4.9 -> index 4.
                    # 40/10 = 4. -> index 4.
                    # 39/10 = 3.9 -> index 3.
                    # So range is [40, 50]. [30, 40).
                    # Actually typically segments are inclusive of upper bound if it's the max.
                    # But int() logic puts 40 into index 4 (1st segment).
                    # 39 into index 3 (2nd segment).
                    # So 1st Segment is [40, 50].
                    # 2nd Segment is [30, 40).
                    # This seems correct.
                    
                    segments[idx]['teams'].append(standing)
                
                context['segments_table'] = segments
                context['max_pts'] = max_pts
        
        return context

def calculate_team_season_stats(team, league, season):
    """
    Helper to calculate comprehensive stats for a team in a season.
    Returns a dict with 'home', 'away', 'total' and 'last_8' stats.
    """
    if not team or not league or not season:
        return None

    all_matches = Match.objects.filter(
        league=league, season=season
    ).filter(
        models.Q(home_team=team) | models.Q(away_team=team)
    ).order_by('date').prefetch_related('goals')
    
    played_matches = [m for m in all_matches if m.status == 'Finished' and m.home_score is not None]
    
    cats = ['home', 'away', 'total']
    stats = {c: {
        'gp': 0, 'w': 0, 'd': 0, 'l': 0, 'gf': 0, 'ga': 0, 'pts': 0,
        'ppg': 0.0, 'avg_gf': 0.0, 'avg_ga': 0.0,
        'cs': 0, 'fts': 0, 'bts': 0,
        'over_05': 0, 'over_15': 0, 'over_25': 0, 'over_35': 0,
        'over_05_pct': 0, 'over_15_pct': 0, 'over_25_pct': 0, 'over_35_pct': 0,
        'cs_pct': 0, 'fts_pct': 0, 'bts_pct': 0, 'win_pct': 0,
        'form': []
    } for c in cats}

    # Last 8 Matches (for Relative Form)
    last_8_matches = played_matches[-8:] if len(played_matches) >= 8 else played_matches
    stats['last_8'] = {
        'gp': 0, 'w': 0, 'd': 0, 'l': 0, 'gf': 0, 'ga': 0, 'pts': 0,
        'ppg': 0.0, 'avg_gf': 0.0, 'avg_ga': 0.0
    }

    def process_match(m, container, is_last_8=False):
        is_home = m.home_team == team
        # If looking at home/away specific stats, skip if not matching
        # But 'container' is a specific dict passed in.
        # We need to handle category selection outside.
        pass

    # Process All Matches
    for m in played_matches:
        is_home = m.home_team == team
        cat = 'home' if is_home else 'away'
        
        gf = (m.home_score if is_home else m.away_score) or 0
        ga = (m.away_score if is_home else m.home_score) or 0
        result = 'W' if gf > ga else ('D' if gf == ga else 'L')
        match_total = gf + ga
        
        # Update Home/Away and Total
        for k in [cat, 'total']:
            s = stats[k]
            s['gp'] += 1
            s['gf'] += gf
            s['ga'] += ga
            if result == 'W': s['w'] += 1; s['pts'] += 3
            elif result == 'D': s['d'] += 1; s['pts'] += 1
            else: s['l'] += 1
            
            s['form'].append(result)
            
            if ga == 0: s['cs'] += 1
            if gf == 0: s['fts'] += 1
            if gf > 0 and ga > 0: s['bts'] += 1
            
            if match_total > 0.5: s['over_05'] += 1
            if match_total > 1.5: s['over_15'] += 1
            if match_total > 2.5: s['over_25'] += 1
            if match_total > 3.5: s['over_35'] += 1

    # Process Last 8
    for m in last_8_matches:
        is_home = m.home_team == team
        gf = (m.home_score if is_home else m.away_score) or 0
        ga = (m.away_score if is_home else m.home_score) or 0
        result = 'W' if gf > ga else ('D' if gf == ga else 'L')
        
        s = stats['last_8']
        s['gp'] += 1
        s['gf'] += gf
        s['ga'] += ga
        if result == 'W': s['w'] += 1; s['pts'] += 3
        elif result == 'D': s['d'] += 1; s['pts'] += 1
        else: s['l'] += 1

    # Calculate Averages
    for k, s in stats.items():
        if s['gp'] > 0:
            s['ppg'] = round(s['pts'] / s['gp'], 2)
            s['ppg_pct'] = int((s['ppg'] / 3.0) * 100)
            s['avg_gf'] = round(s['gf'] / s['gp'], 2)
            s['avg_ga'] = round(s['ga'] / s['gp'], 2)
            if 'over_25' in s:
                s['over_05_pct'] = int((s['over_05'] / s['gp']) * 100)
                s['over_15_pct'] = int((s['over_15'] / s['gp']) * 100)
                s['over_25_pct'] = int((s['over_25'] / s['gp']) * 100)
                s['over_35_pct'] = int((s['over_35'] / s['gp']) * 100)
                s['cs_pct'] = int((s['cs'] / s['gp']) * 100)
                s['fts_pct'] = int((s['fts'] / s['gp']) * 100)
                s['bts_pct'] = int((s['bts'] / s['gp']) * 100)
                s['win_pct'] = int((s['w'] / s['gp']) * 100)

    # Relative Form Diffs (Last 8 vs Season Total)
    total = stats['total']
    l8 = stats['last_8']
    if total['gp'] > 0 and l8['gp'] > 0:
        stats['diff'] = {
            'ppg': round(((l8['ppg'] - total['ppg']) / total['ppg']) * 100, 1) if total['ppg'] > 0 else 0,
            'avg_gf': round(((l8['avg_gf'] - total['avg_gf']) / total['avg_gf']) * 100, 1) if total['avg_gf'] > 0 else 0,
            'avg_ga': round(((l8['avg_ga'] - total['avg_ga']) / total['avg_ga']) * 100, 1) if total['avg_ga'] > 0 else 0,
        }
    
    # Progression Data (for graph)
    # 2 for Win, 0 for Draw, -1 for Loss
    progression = []
    current_val = 0
    for res in total['form']:
        val = 2 if res == 'W' else (0 if res == 'D' else -1)
        current_val += val
        progression.append(current_val)
    stats['progression'] = progression

    return stats


class HeadToHeadView(TemplateView):
    template_name = 'matches/h2h_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        league_slug = self.kwargs.get('league_name')
        team1_slug = self.kwargs.get('team1_name')
        team2_slug = self.kwargs.get('team2_name')

        # Helper to find team by slug/name
        def get_league(slug):
            if not slug: return None
            name = slug.replace('-', ' ')
            
            # Robust Selection: Prioritize League with Data (Standings)
            from django.db.models import Count
            candidates = League.objects.filter(name__iexact=name).annotate(s_count=Count('standings')).order_by('-s_count')
            if not candidates.exists():
                 candidates = League.objects.filter(name__icontains=name).annotate(s_count=Count('standings')).order_by('-s_count')
            
            return candidates.first()

        def get_team(slug, league=None):
            if not slug: return None
            name = slug.replace('-', ' ')
            
            # 1. Try finding in the specific league first
            if league:
                t = Team.objects.filter(league=league, name__iexact=name).first()
                if not t:
                    t = Team.objects.filter(league=league, name__icontains=name).first()
                if t: return t
            
            # 2. Global Fallback
            t = Team.objects.filter(name__iexact=name).first()
            if not t:
                t = Team.objects.filter(name__icontains=name).first()
            return t

        league = get_league(league_slug)
        team1 = get_team(team1_slug, league)
        team2 = get_team(team2_slug, league)

        context['league'] = league
        context['team1'] = team1
        context['team2'] = team2

        if team1 and team2:
            # Direct Matches
            matches = Match.objects.filter(
                (models.Q(home_team=team1) & models.Q(away_team=team2)) |
                (models.Q(home_team=team2) & models.Q(away_team=team1))
            ).filter(status__in=FINISHED_STATUSES).order_by('-date')
            context['matches'] = matches
            
            # Calculate H2H Summary
            h2h_stats = {
                'gp': 0, 't1_wins': 0, 't2_wins': 0, 'draws': 0,
                't1_goals': 0, 't2_goals': 0,
                't1_win_pct': 0, 't2_win_pct': 0, 'draw_pct': 0, 'avg_goals': 0.0
            }
            
            for m in matches:
                h2h_stats['gp'] += 1
                
                # Determine scores relative to Team 1
                if m.home_team == team1:
                    s1 = m.home_score
                    s2 = m.away_score
                else:
                    s1 = m.away_score
                    s2 = m.home_score
                    
                if s1 is None: s1 = 0
                if s2 is None: s2 = 0
                
                h2h_stats['t1_goals'] += s1
                h2h_stats['t2_goals'] += s2
                
                if s1 > s2: h2h_stats['t1_wins'] += 1
                elif s2 > s1: h2h_stats['t2_wins'] += 1
                else: h2h_stats['draws'] += 1
            
            if h2h_stats['gp'] > 0:
                h2h_stats['t1_win_pct'] = int((h2h_stats['t1_wins'] / h2h_stats['gp']) * 100)
                h2h_stats['t2_win_pct'] = int((h2h_stats['t2_wins'] / h2h_stats['gp']) * 100)
                h2h_stats['draw_pct'] = int((h2h_stats['draws'] / h2h_stats['gp']) * 100)
                h2h_stats['avg_goals'] = round((h2h_stats['t1_goals'] + h2h_stats['t2_goals']) / h2h_stats['gp'], 2)
                
            context['h2h_stats'] = h2h_stats

            if h2h_stats['gp'] == 0 and league and league.name == 'First League' and league.country == 'Republica Tcheca':
                try:
                    ss_urls = []
                    u1 = self.request.GET.get('ss_team1') or self.request.GET.get('ss_url_t1') or self.request.GET.get('ss_url')
                    u2 = self.request.GET.get('ss_team2') or self.request.GET.get('ss_url_t2')
                    if u1: ss_urls.append(u1)
                    if u2: ss_urls.append(u2)
                    if ss_urls:
                        import requests as _rq
                        import pandas as _pd
                        from io import StringIO as _SIO
                        season_guess = Season.objects.order_by('-year').first()
                        if not season_guess:
                            from django.utils import timezone as _tz
                            season_guess, _ = Season.objects.get_or_create(year=_tz.now().year)
                        def _process_df(df):
                            if df.shape[1] < 3: 
                                return 0
                            saved = 0
                            for idx, row in df.iterrows():
                                try:
                                    vals = [str(x).strip() for x in row.values.tolist()]
                                    if len(vals) < 3: 
                                        continue
                                    score_idx = None
                                    for i, v in enumerate(vals):
                                        vv = v.replace('–', '-').replace('—', '-').replace('−', '-')
                                        if vv and ((':' in vv) or ('-' in vv)):
                                            p = vv.replace(' ', '')
                                            if ':' in p:
                                                parts = p.split(':')
                                            else:
                                                parts = p.split('-')
                                            if len(parts) == 2 and all(part.isdigit() for part in parts):
                                                score_idx = i
                                                break
                                    if score_idx is None:
                                        continue
                                    raw_score_val = vals[score_idx]
                                    score_val = raw_score_val.replace('–', '-').replace(':', '-')
                                    home_name = None
                                    for i in range(score_idx - 1, -1, -1):
                                        c = vals[i]
                                        if c and c.lower() not in {'vs','v'}:
                                            home_name = c
                                            break
                                    away_name = None
                                    for i in range(score_idx + 1, len(vals)):
                                        c = vals[i]
                                        if c:
                                            away_name = c
                                            break
                                    if not home_name or not away_name:
                                        continue
                                    names = {home_name.lower(): home_name, away_name.lower(): away_name}
                                    def _same(a, b):
                                        return a.strip().lower() == b.strip().lower()
                                    if not ((_same(home_name, team1.name) and _same(away_name, team2.name)) or (_same(home_name, team2.name) and _same(away_name, team1.name))):
                                        continue
                                    try:
                                        ps = score_val.split('-')
                                        h_s = int(ps[0]); a_s = int(ps[1]); status = 'Finished'
                                    except:
                                        continue
                                    dt = None
                                    for i in range(0, score_idx):
                                        cand = vals[i]
                                        if len(cand.split()) >= 3:
                                            try:
                                                base = cand.split()[:3]
                                                from datetime import datetime as _dt
                                                base_dt = _dt.strptime(" ".join(base), "%a %d %b")
                                                y = season_guess.year - 1 if base_dt.month >= 8 else season_guess.year
                                                from django.utils import timezone as _tz
                                                dt = _tz.make_aware(_dt(y, base_dt.month, base_dt.day))
                                                break
                                            except:
                                                continue
                                    if _same(home_name, team1.name):
                                        h = team1; a = team2
                                    elif _same(home_name, team2.name):
                                        h = team2; a = team1
                                    else:
                                        continue
                                    m_kwargs = {
                                        'league': league,
                                        'season': season_guess,
                                        'home_team': h,
                                        'away_team': a,
                                        'home_score': h_s,
                                        'away_score': a_s,
                                        'status': status
                                    }
                                    if dt:
                                        m_kwargs['date'] = dt
                                    # Build unsaved Match instance to feed the template without touching DB
                                    tmp_match = Match(**m_kwargs)
                                    scraped.append(tmp_match)
                                except Exception:
                                    continue
                            return len(scraped)
                        scraped_matches = []
                        for u in ss_urls:
                            try:
                                r = _rq.get(u, headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
                                if r.status_code != 200: 
                                    continue
                                try:
                                    dfs = _pd.read_html(_SIO(r.text))
                                except ValueError:
                                    dfs = []
                                for df in dfs:
                                    scraped = []
                                    def _assign_scraped(lst): 
                                        nonlocal scraped
                                        scraped = lst
                                        return len(lst)
                                    # Localize scraped list inside parser
                                    scraped = []
                                    # Rebind scraped name used in _process_df
                                    locals()['scraped'] = scraped
                                    _process_df(df)
                                    scraped_matches.extend(scraped)
                            except Exception:
                                continue
                        if scraped_matches:
                            # Sort newest first if dates exist
                            scraped_matches.sort(key=lambda x: (x.date if getattr(x, 'date', None) else timezone.now()), reverse=True)
                            context['matches'] = scraped_matches
                            h2h_stats = {
                                'gp': 0, 't1_wins': 0, 't2_wins': 0, 'draws': 0,
                                't1_goals': 0, 't2_goals': 0,
                                't1_win_pct': 0, 't2_win_pct': 0, 'draw_pct': 0, 'avg_goals': 0.0
                            }
                            for m in scraped_matches:
                                h2h_stats['gp'] += 1
                                if m.home_team == team1:
                                    s1 = m.home_score; s2 = m.away_score
                                else:
                                    s1 = m.away_score; s2 = m.home_score
                                s1 = s1 or 0; s2 = s2 or 0
                                h2h_stats['t1_goals'] += s1; h2h_stats['t2_goals'] += s2
                                if s1 > s2: h2h_stats['t1_wins'] += 1
                                elif s2 > s1: h2h_stats['t2_wins'] += 1
                                else: h2h_stats['draws'] += 1
                            if h2h_stats['gp'] > 0:
                                h2h_stats['t1_win_pct'] = int((h2h_stats['t1_wins'] / h2h_stats['gp']) * 100)
                                h2h_stats['t2_win_pct'] = int((h2h_stats['t2_wins'] / h2h_stats['gp']) * 100)
                                h2h_stats['draw_pct'] = int((h2h_stats['draws'] / h2h_stats['gp']) * 100)
                                h2h_stats['avg_goals'] = round((h2h_stats['t1_goals'] + h2h_stats['t2_goals']) / h2h_stats['gp'], 2)
                            context['h2h_stats'] = h2h_stats
                except Exception:
                    pass

            
            if h2h_stats['gp'] == 0 and league and league.name == 'First League' and league.country == 'Republica Tcheca':
                from math import exp, factorial
                s1 = LeagueStanding.objects.filter(league=league, team=team1).order_by('-season__year').first()
                s2 = LeagueStanding.objects.filter(league=league, team=team2).order_by('-season__year').first()
                if s1 and s2:
                    def per_game(g, p): 
                        return round((g / p), 3) if p and g is not None else 0.0
                    t1_ppg = round((s1.points / s1.played), 2) if s1.played else 0.0
                    t2_ppg = round((s2.points / s2.played), 2) if s2.played else 0.0
                    t1_gfpg = per_game(s1.goals_for, s1.played)
                    t1_gapg = per_game(s1.goals_against, s1.played)
                    t2_gfpg = per_game(s2.goals_for, s2.played)
                    t2_gapg = per_game(s2.goals_against, s2.played)
                    qs = LeagueStanding.objects.filter(league=league)
                    lg_gf = sum(ls.goals_for for ls in qs)
                    lg_gp = sum(ls.played for ls in qs)
                    lg_avg_goals = per_game(lg_gf, lg_gp)
                    lam_home = max((t1_gfpg + t2_gapg) / 2.0, 0.01)
                    lam_away = max((t2_gfpg + t1_gapg) / 2.0, 0.01)
                    def pois(k, lam):
                        return (lam**k) * exp(-lam) / factorial(k)
                    max_g = 6
                    mat = []
                    for i in range(0, max_g+1):
                        for j in range(0, max_g+1):
                            p = pois(i, lam_home) * pois(j, lam_away)
                            mat.append((i, j, p))
                    p_home = sum(p for i, j, p in mat if i > j)
                    p_draw = sum(p for i, j, p in mat if i == j)
                    p_away = sum(p for i, j, p in mat if i < j)
                    over_05 = sum(p for i, j, p in mat if (i + j) > 0)
                    over_15 = sum(p for i, j, p in mat if (i + j) > 1)
                    over_25 = sum(p for i, j, p in mat if (i + j) > 2)
                    over_35 = sum(p for i, j, p in mat if (i + j) > 3)
                    btts = sum(p for i, j, p in mat if (i >= 1 and j >= 1))
                    mat.sort(key=lambda x: x[2], reverse=True)
                    top_scores = [{'home': i, 'away': j, 'prob': round(p*100, 1)} for i, j, p in mat[:5]]
                    context['fallback_h2h'] = {
                        't1': {'ppg': t1_ppg, 'gfpg': round(t1_gfpg,2), 'gapg': round(t1_gapg,2)},
                        't2': {'ppg': t2_ppg, 'gfpg': round(t2_gfpg,2), 'gapg': round(t2_gapg,2)},
                        'league_avg_goals': round(lg_avg_goals,2),
                        'probs': {'home': round(p_home*100,1), 'draw': round(p_draw*100,1), 'away': round(p_away*100,1)},
                        'totals': {
                            'over_05': round(over_05*100,1),
                            'over_15': round(over_15*100,1),
                            'over_25': round(over_25*100,1),
                            'over_35': round(over_35*100,1),
                            'btts': round(btts*100,1)
                        },
                        'top_scores': top_scores
                    }
            # Latest Season for stats
            # Prefer seasons with matches for this league
            latest_season = Season.objects.filter(matches__league=league).distinct().order_by('-year').first()
            if not latest_season:
                latest_season = Season.objects.filter(standings__league=league).order_by('-year').first()
            if not latest_season:
                latest_season = Season.objects.filter(standings__league=league).order_by('-year').first()
            
            context['season'] = latest_season
            context['latest_season'] = latest_season
            
            if latest_season:
                context['t1_stats'] = calculate_team_season_stats(team1, league, latest_season)
                context['t2_stats'] = calculate_team_season_stats(team2, league, latest_season)
            else:
                def calc_team_stats_no_season(team, lg):
                    ms = Match.objects.filter(
                        league=lg,
                        status__in=FINISHED_STATUSES
                    ).filter(
                        models.Q(home_team=team) | models.Q(away_team=team)
                    ).order_by('date')
                    
                    def calc_stats(match_qs, filter_type='all'):
                        lst = list(match_qs)
                        gp = 0; w = 0; d = 0; l = 0; gf = 0; ga = 0; pts = 0
                        cs = 0; fts = 0; bts = 0
                        over_05 = 0; over_15 = 0; over_25 = 0; over_35 = 0

                        for m in lst:
                            is_home = (m.home_team_id == team.id)
                            if filter_type == 'home' and not is_home: 
                                continue
                            if filter_type == 'away' and is_home: 
                                continue
                            team_score = m.home_score if is_home else m.away_score
                            opp_score = m.away_score if is_home else m.home_score
                            team_score = team_score or 0
                            opp_score = opp_score or 0
                            
                            total_g = team_score + opp_score

                            gp += 1
                            gf += team_score
                            ga += opp_score
                            if team_score > opp_score: 
                                w += 1; pts += 3
                            elif team_score == opp_score: 
                                d += 1; pts += 1
                            else: 
                                l += 1
                            
                            if opp_score == 0: cs += 1
                            if team_score == 0: fts += 1
                            if team_score > 0 and opp_score > 0: bts += 1
                            
                            if total_g > 0.5: over_05 += 1
                            if total_g > 1.5: over_15 += 1
                            if total_g > 2.5: over_25 += 1
                            if total_g > 3.5: over_35 += 1

                        ppg = round(pts / gp, 2) if gp > 0 else 0.0
                        avg_gf = round(gf / gp, 2) if gp > 0 else 0.0
                        avg_ga = round(ga / gp, 2) if gp > 0 else 0.0
                        
                        return {
                            'gp': gp, 'w': w, 'd': d, 'l': l, 'gf': gf, 'ga': ga, 'pts': pts, 'ppg': ppg,
                            'avg_gf': avg_gf, 'avg_ga': avg_ga,
                            'cs': cs, 'fts': fts, 'bts': bts,
                            'over_05': over_05, 'over_15': over_15, 'over_25': over_25, 'over_35': over_35,
                            'over_05_pct': int((over_05 / gp) * 100) if gp > 0 else 0,
                            'over_15_pct': int((over_15 / gp) * 100) if gp > 0 else 0,
                            'over_25_pct': int((over_25 / gp) * 100) if gp > 0 else 0,
                            'over_35_pct': int((over_35 / gp) * 100) if gp > 0 else 0,
                            'cs_pct': int((cs / gp) * 100) if gp > 0 else 0,
                            'fts_pct': int((fts / gp) * 100) if gp > 0 else 0,
                            'bts_pct': int((bts / gp) * 100) if gp > 0 else 0,
                            'win_pct': int((w / gp) * 100) if gp > 0 else 0,
                        }
                    
                    overall = calc_stats(ms)
                    home = calc_stats(ms, 'home')
                    away = calc_stats(ms, 'away')
                    desc = sorted(ms, key=lambda x: (x.date if x.date else timezone.now(), x.id), reverse=True)
                    last_8 = calc_stats(desc[:8])
                    return {'overall': overall, 'home': home, 'away': away, 'last_8': last_8, 'total': overall}
                
                context['t1_stats'] = calc_team_stats_no_season(team1, league)
                context['t2_stats'] = calc_team_stats_no_season(team2, league)
                
            # Standings Positions
            s1 = LeagueStanding.objects.filter(league=league, season=latest_season, team=team1).first()
            s2 = LeagueStanding.objects.filter(league=league, season=latest_season, team=team2).first()
            context['t1_standing'] = s1
            context['t2_standing'] = s2
            
            # Full Match Lists (Played)
            def get_matches(team, status='Finished'):
                if latest_season:
                    qs = Match.objects.filter(
                        league=league, season=latest_season
                    ).filter(
                        models.Q(home_team=team) | models.Q(away_team=team)
                    )
                else:
                    qs = Match.objects.filter(
                        league=league
                    ).filter(
                        models.Q(home_team=team) | models.Q(away_team=team)
                    )
                if status == 'Finished':
                    # Reverse order for played matches (newest first)
                    return list(qs.filter(status__in=FINISHED_STATUSES).order_by('-date'))
                else:
                    return qs.filter(status='Scheduled').order_by('date')
            
            context['t1_matches'] = get_matches(team1, 'Finished')
            context['t2_matches'] = get_matches(team2, 'Finished')
            
            # Helper to calculate PPG for a team at a specific venue
            def get_venue_ppg(team, venue):
                # venue: 'home' or 'away'
                if venue == 'home':
                    ms = Match.objects.filter(league=league, season=latest_season, home_team=team, status__in=FINISHED_STATUSES)
                    pts = 0
                    for m in ms:
                        if m.home_score > m.away_score: pts += 3
                        elif m.home_score == m.away_score: pts += 1
                    return round(pts / ms.count(), 2) if ms.exists() else 0.0
                else:
                    ms = Match.objects.filter(league=league, season=latest_season, away_team=team, status__in=FINISHED_STATUSES)
                    pts = 0
                    for m in ms:
                        if m.away_score > m.home_score: pts += 3
                        elif m.away_score == m.home_score: pts += 1
                    return round(pts / ms.count(), 2) if ms.exists() else 0.0

            # Fixtures (Run-in) with Analysis
            def process_fixtures(team):
                fixtures = get_matches(team, 'Scheduled')
                processed = []
                opp_ppg_sum = 0
                count = 0
                
                for m in fixtures:
                    is_home = m.home_team == team
                    opponent = m.away_team if is_home else m.home_team
                    
                    # We want Opponent's PPG at the venue they will play
                    # If Team is Home, Opponent is Away -> Get Opponent Away PPG
                    # If Team is Away, Opponent is Home -> Get Opponent Home PPG
                    opp_venue = 'away' if is_home else 'home'
                    opp_ppg = get_venue_ppg(opponent, opp_venue)
                    
                    # Also get Team's PPG at this venue for comparison? 
                    # Or just display Opponent PPG as requested.
                    # The image shows "Home", "Away", "Opponent". 
                    # Usually: Team Home PPG (if home), Team Away PPG (if away) vs Opponent PPG.
                    
                    my_venue = 'home' if is_home else 'away'
                    my_ppg = get_venue_ppg(team, my_venue)
                    
                    opp_ppg_sum += opp_ppg
                    count += 1
                    
                    processed.append({
                        'match': m,
                        'is_home': is_home,
                        'opponent': opponent,
                        'my_ppg': my_ppg,
                        'opp_ppg': opp_ppg,
                        'bar_width': min(int((opp_ppg / 3.0) * 100), 100)
                    })
                
                avg_opp_ppg = round(opp_ppg_sum / count, 2) if count > 0 else 0
                return processed, avg_opp_ppg

            t1_fixt_data, t1_avg_opp = process_fixtures(team1)
            t2_fixt_data, t2_avg_opp = process_fixtures(team2)

            context['t1_fixtures'] = t1_fixt_data
            context['t2_fixtures'] = t2_fixt_data
            context['t1_avg_opp_ppg'] = t1_avg_opp
            context['t2_avg_opp_ppg'] = t2_avg_opp

            # --- Historical Statistics & Comparison ---
            def get_previous_season_stats(team, lg, current_yr):
                try:
                    # current_yr is int (e.g., 2026)
                    prev_yr = current_yr - 1
                    # Try finding by match league first
                    prev_season = Season.objects.filter(matches__league=lg, year=prev_yr).distinct().first()
                    if not prev_season:
                        prev_season = Season.objects.filter(standings__league=lg, year=prev_yr).first()
                    
                    if not prev_season:
                         # Fallback: Just get previous by ID/order
                         prev_season = Season.objects.filter(matches__league=lg, year__lt=current_yr).distinct().order_by('-year').first()
                    
                    if prev_season:
                        return calculate_team_season_stats(team, lg, prev_season), prev_season
                except Exception as e:
                    print(f"Error getting prev stats: {e}")
                    pass
                return None, None

            if latest_season:
                t1_prev_stats, t1_prev_season = get_previous_season_stats(team1, league, latest_season.year)
                t2_prev_stats, t2_prev_season = get_previous_season_stats(team2, league, latest_season.year)
                
                context['t1_prev_stats'] = t1_prev_stats
                context['t1_prev_season'] = t1_prev_season
                context['t2_prev_stats'] = t2_prev_stats
                context['t2_prev_season'] = t2_prev_season
                
                # Comparison with Past Seasons (Fixed GP)
                def get_past_records(team, lg, limit_gp, current_pts=None):
                    if limit_gp <= 0: return []
                    
                    records = []
                    # Get all seasons for this team in this league (via matches or standings)
                    seasons = Season.objects.filter(
                        models.Q(matches__league=lg, matches__home_team=team) | 
                        models.Q(standings__league=lg, standings__team=team)
                    ).distinct().order_by('-year')
                    
                    for s in seasons:
                        # Skip current if we want only past? Or include all.
                        # Image shows current at top, then others.
                        
                        matches = Match.objects.filter(
                            league=lg, season=s
                        ).filter(
                            models.Q(home_team=team) | models.Q(away_team=team)
                        ).filter(status__in=FINISHED_STATUSES).order_by('date')[:limit_gp]
                        
                        # Must have exactly limit_gp matches? 
                        # Image says "after 24 matches". If a season had fewer, maybe skip or show what exists.
                        # Usually we only show if count == limit_gp.
                        
                        matches_list = list(matches)
                        if len(matches_list) < limit_gp:
                            # Special case: Current season might have exactly limit_gp. 
                            # Past seasons usually have more.
                            # If past season had fewer (relegated/promoted/short season), skip.
                            if s != latest_season: continue
                        
                        # Calculate Stats
                        w = 0; d = 0; l = 0; gf = 0; ga = 0; pts = 0
                        for m in matches_list:
                            is_home = m.home_team == team
                            my_score = m.home_score if is_home else m.away_score
                            opp_score = m.away_score if is_home else m.home_score
                            if my_score is None: my_score = 0
                            if opp_score is None: opp_score = 0
                            
                            gf += my_score
                            ga += opp_score
                            if my_score > opp_score: w += 1; pts += 3
                            elif my_score == opp_score: d += 1; pts += 1
                            else: l += 1
                        
                        diff = None
                        if current_pts is not None and s != latest_season:
                            diff = current_pts - pts

                        records.append({
                            'season': s,
                            'gp': len(matches_list),
                            'w': w, 'd': d, 'l': l,
                            'gf': gf, 'ga': ga, 'pts': pts,
                            'diff': diff
                        })
                        
                    return records

                # Current GP
                t1_gp = context['t1_stats']['total']['gp']
                t2_gp = context['t2_stats']['total']['gp']
                
                t1_current_pts = context['t1_stats']['total']['pts']
                t2_current_pts = context['t2_stats']['total']['pts']

                context['t1_past_records'] = get_past_records(team1, league, t1_gp, t1_current_pts)
                context['t2_past_records'] = get_past_records(team2, league, t2_gp, t2_current_pts)

                # --- Current Streaks Calculation ---
                def calculate_streaks(team, lg, season):
                    # Get matches for this season, finished, ordered by date desc
                    all_matches = Match.objects.filter(
                        league=lg, season=season, status__in=FINISHED_STATUSES
                    ).filter(
                        models.Q(home_team=team) | models.Q(away_team=team)
                    ).order_by('-date')

                    # Helper to check streaks
                    def get_seq(matches_subset):
                        # Initialize streaks
                        s = {
                            'wins': 0, 'draws': 0, 'defeats': 0,
                            'no_win': 0, 'no_draw': 0, 'no_defeat': 0,
                            'score_1plus': 0, 'concede_1plus': 0,
                            'no_score': 0, 'no_concede': 0,
                            'over_25': 0, 'under_25': 0,
                            'score_2plus': 0
                        }
                        
                        # Flags to stop counting when streak breaks
                        active = {k: True for k in s.keys()}
                        
                        for m in matches_subset:
                            is_home = m.home_team == team
                            my_score = m.home_score if is_home else m.away_score
                            opp_score = m.away_score if is_home else m.home_score
                            if my_score is None: my_score = 0
                            if opp_score is None: opp_score = 0
                            total_goals = my_score + opp_score
                            
                            # Wins
                            if active['wins']:
                                if my_score > opp_score: s['wins'] += 1
                                else: active['wins'] = False
                            
                            # Draws
                            if active['draws']:
                                if my_score == opp_score: s['draws'] += 1
                                else: active['draws'] = False
                            
                            # Defeats
                            if active['defeats']:
                                if my_score < opp_score: s['defeats'] += 1
                                else: active['defeats'] = False
                                
                            # No Win (Draw or Defeat)
                            if active['no_win']:
                                if my_score <= opp_score: s['no_win'] += 1
                                else: active['no_win'] = False
                            
                            # No Draw (Win or Defeat)
                            if active['no_draw']:
                                if my_score != opp_score: s['no_draw'] += 1
                                else: active['no_draw'] = False
                            
                            # No Defeat (Win or Draw)
                            if active['no_defeat']:
                                if my_score >= opp_score: s['no_defeat'] += 1
                                else: active['no_defeat'] = False
                            
                            # 1 goal scored or more
                            if active['score_1plus']:
                                if my_score >= 1: s['score_1plus'] += 1
                                else: active['score_1plus'] = False
                            
                            # 1 goal conceded or more
                            if active['concede_1plus']:
                                if opp_score >= 1: s['concede_1plus'] += 1
                                else: active['concede_1plus'] = False
                            
                            # No goal scored
                            if active['no_score']:
                                if my_score == 0: s['no_score'] += 1
                                else: active['no_score'] = False
                            
                            # No goal conceded (Clean Sheet)
                            if active['no_concede']:
                                if opp_score == 0: s['no_concede'] += 1
                                else: active['no_concede'] = False
                                
                            # GF+GA over 2.5
                            if active['over_25']:
                                if total_goals > 2.5: s['over_25'] += 1
                                else: active['over_25'] = False
                            
                            # GF+GA under 2.5
                            if active['under_25']:
                                if total_goals < 2.5: s['under_25'] += 1
                                else: active['under_25'] = False
                            
                            # Scored at least twice
                            if active['score_2plus']:
                                if my_score >= 2: s['score_2plus'] += 1
                                else: active['score_2plus'] = False
                                
                            # Optimization: if all active are False, break
                            if not any(active.values()):
                                break
                                
                        return s

                    # Filter subsets
                    matches_home = [m for m in all_matches if m.home_team == team]
                    matches_away = [m for m in all_matches if m.away_team == team]
                    
                    return {
                        'total': get_seq(all_matches),
                        'home': get_seq(matches_home),
                        'away': get_seq(matches_away)
                    }

                context['t1_streaks'] = calculate_streaks(team1, league, latest_season)
                context['t2_streaks'] = calculate_streaks(team2, league, latest_season)

                # --- League Comparison Calculation ---
                def calculate_league_avg(lg, season):
                    matches = Match.objects.filter(league=lg, season=season, status__in=FINISHED_STATUSES)
                    total_matches = matches.count()
                    if total_matches == 0: return {}
                    
                    total_goals = 0
                    wins = 0
                    draws = 0
                    clean_sheets = 0
                    failed_to_score = 0
                    won_to_nil = 0
                    lost_to_nil = 0
                    both_teams_scored = 0
                    over_15 = 0
                    over_25 = 0
                    over_35 = 0
                    
                    # New accumulators for advanced stats
                    sum_minute_scored_first = 0
                    count_scored_first = 0
                    
                    leads_taken = 0
                    leads_defended = 0 # Won after scoring first
                    
                    deficits_faced = 0
                    deficits_overcome = 0 # Avoided defeat (W or D) after conceding first
                    
                    points_scored_first = 0
                    points_conceded_first = 0
                    
                    total_minutes_leading = 0
                    total_minutes_level = 0
                    # Trailing time is symmetric to Leading time in league context
                    
                    for m in matches:
                        h_score = m.home_score or 0
                        a_score = m.away_score or 0
                        match_goals = h_score + a_score
                        total_goals += match_goals
                        
                        if h_score > a_score: wins += 1
                        elif a_score > h_score: wins += 1
                        else: draws += 1
                        
                        if a_score == 0: clean_sheets += 1
                        if h_score == 0: clean_sheets += 1
                        if h_score == 0: failed_to_score += 1
                        if a_score == 0: failed_to_score += 1
                        if h_score > 0 and a_score == 0: won_to_nil += 1
                        if a_score > 0 and h_score == 0: won_to_nil += 1
                        if h_score == 0 and a_score > 0: lost_to_nil += 1
                        if a_score == 0 and h_score > 0: lost_to_nil += 1
                        if h_score > 0 and a_score > 0: both_teams_scored += 1
                        if match_goals > 1.5: over_15 += 1
                        if match_goals > 2.5: over_25 += 1
                        if match_goals > 3.5: over_35 += 1
                        
                        # Advanced stats from goals
                        goals = list(m.goals.all().order_by('minute'))
                        
                        # Time Leading/Level
                        # We can approximate or calculate exactly. Let's calculate exactly.
                        current_h_score = 0
                        current_a_score = 0
                        last_minute = 0
                        # state: 0 level, 1 home leads, -1 away leads
                        current_state = 0 
                        
                        for g in goals:
                            minute = min(g.minute, 90)
                            duration = max(0, minute - last_minute)
                            
                            if current_state == 0: total_minutes_level += (duration * 2) # Both teams level
                            elif current_state == 1: total_minutes_leading += duration # Home leads (so Away trails)
                            else: total_minutes_leading += duration # Away leads (so Home trails)
                            
                            if g.team == m.home_team: current_h_score += 1
                            else: current_a_score += 1
                            
                            if current_h_score > current_a_score: current_state = 1
                            elif current_a_score > current_h_score: current_state = -1
                            else: current_state = 0
                            last_minute = minute
                            
                        # Remaining time
                        duration = max(0, 90 - last_minute)
                        if current_state == 0: total_minutes_level += (duration * 2)
                        else: total_minutes_leading += duration
                        
                        # First Goal Analysis
                        if goals:
                            first_goal = goals[0]
                            sum_minute_scored_first += (first_goal.minute * 2) # Count for both Scored First and Conceded First avg
                            count_scored_first += 2 # One team scored, one conceded
                            
                            # Who scored first?
                            scorer_is_home = (first_goal.team == m.home_team)
                            
                            # Home Perspective
                            if scorer_is_home:
                                leads_taken += 1
                                if h_score > a_score: 
                                    leads_defended += 1
                                    points_scored_first += 3
                                elif h_score == a_score:
                                    points_scored_first += 1
                                    
                                # Away Perspective (Conceded first)
                                deficits_faced += 1
                                if a_score >= h_score: deficits_overcome += 1
                                if a_score > h_score: points_conceded_first += 3
                                elif a_score == h_score: points_conceded_first += 1
                            else:
                                # Away scored first
                                leads_taken += 1 # Away took lead
                                if a_score > h_score: 
                                    leads_defended += 1
                                    points_scored_first += 3
                                elif a_score == h_score:
                                    points_scored_first += 1
                                    
                                # Home Perspective (Conceded first)
                                deficits_faced += 1
                                if h_score >= a_score: deficits_overcome += 1
                                if h_score > a_score: points_conceded_first += 3
                                elif h_score == a_score: points_conceded_first += 1

                    n_matches = total_matches
                    n_team_games = total_matches * 2
                    avg = {}
                    
                    avg['ppg'] = ((wins * 3) + (draws * 2)) / n_team_games
                    avg['win_pct'] = (wins / n_team_games) * 100
                    avg['draw_pct'] = ((draws * 2) / n_team_games) * 100
                    avg['defeat_pct'] = (wins / n_team_games) * 100
                    avg['gf_pg'] = total_goals / n_team_games
                    avg['ga_pg'] = total_goals / n_team_games
                    avg['clean_sheet_pct'] = (clean_sheets / n_team_games) * 100
                    avg['failed_to_score_pct'] = (failed_to_score / n_team_games) * 100
                    avg['won_to_nil_pct'] = (won_to_nil / n_team_games) * 100
                    avg['lost_to_nil_pct'] = (lost_to_nil / n_team_games) * 100
                    avg['total_goals_pg'] = total_goals / n_matches
                    avg['btts_pct'] = (both_teams_scored / n_matches) * 100
                    avg['over_15_pct'] = (over_15 / n_matches) * 100
                    avg['over_25_pct'] = (over_25 / n_matches) * 100
                    avg['over_35_pct'] = (over_35 / n_matches) * 100
                    
                    # New League Averages
                    avg['team_scored_first_pct'] = (leads_taken / n_team_games) * 100
                    avg['opponent_scored_first_pct'] = (deficits_faced / n_team_games) * 100
                    
                    if leads_taken > 0:
                        avg['avg_minute_scored_first'] = sum_minute_scored_first / count_scored_first # Symmetric
                        avg['avg_minute_conceded_first'] = avg['avg_minute_scored_first']
                        avg['lead_defending_rate'] = (leads_defended / leads_taken) * 100
                        avg['ppg_scored_first'] = points_scored_first / leads_taken
                    else:
                        avg['avg_minute_scored_first'] = 0
                        avg['avg_minute_conceded_first'] = 0
                        avg['lead_defending_rate'] = 0
                        avg['ppg_scored_first'] = 0
                        
                    if deficits_faced > 0:
                        avg['equalizing_rate'] = (deficits_overcome / deficits_faced) * 100
                        avg['ppg_conceded_first'] = points_conceded_first / deficits_faced
                    else:
                        avg['equalizing_rate'] = 0
                        avg['ppg_conceded_first'] = 0
                        
                    # Time percentages
                    total_minutes = n_matches * 90
                    # total_minutes_leading contains total duration one team was leading.
                    # Since it's symmetric, Avg Time Leading per team = total_minutes_leading / n_team_games ?
                    # No. In a 90 min match, if Home leads 30, Away leads 0, Level 60.
                    # Home: 30L, 0T, 60Lv. Away: 0L, 30T, 60Lv.
                    # Sum Leading = 30. Sum Trailing = 30. Sum Level = 120.
                    # Avg Leading = 30 / 2 = 15.
                    # total_minutes_leading accumulated `duration` whenever state != 0.
                    # So it already sums (Home Leading + Away Leading).
                    avg['time_leading_pct'] = ((total_minutes_leading / 2) / (n_matches * 90)) * 100 # Per team
                    avg['time_trailing_pct'] = avg['time_leading_pct']
                    avg['time_level_pct'] = ((total_minutes_level / 2) / (n_matches * 90)) * 100 # Per team
                    
                    return avg

                def calculate_team_comparison(team, lg, season, league_avg):

                    matches = Match.objects.filter(league=lg, season=season, status__in=FINISHED_STATUSES).filter(models.Q(home_team=team) | models.Q(away_team=team))
                    n_matches = matches.count()
                    if n_matches == 0: return []
                    
                    stats = {k: 0 for k in league_avg.keys()}
                    points, wins, draws, defeats = 0, 0, 0, 0
                    gf, ga = 0, 0
                    clean_sheets, failed_to_score = 0, 0
                    won_to_nil, lost_to_nil = 0, 0
                    btts, over_15, over_25, over_35 = 0, 0, 0, 0
                    
                    minutes_scored_first, minutes_conceded_first = [], []
                    scored_first_count, conceded_first_count = 0, 0
                    won_when_scored_first, pts_when_scored_first = 0, 0
                    pts_when_conceded_first, avoid_defeat_when_conceded_first = 0, 0
                    
                    for m in matches:
                        is_home = m.home_team == team
                        my_score = m.home_score if is_home else m.away_score
                        opp_score = m.away_score if is_home else m.home_score
                        if my_score is None: my_score = 0
                        if opp_score is None: opp_score = 0
                        match_goals = my_score + opp_score
                        
                        gf += my_score; ga += opp_score
                        if my_score > opp_score: wins += 1; points += 3
                        elif my_score == opp_score: draws += 1; points += 1
                        else: defeats += 1
                        
                        if opp_score == 0: clean_sheets += 1
                        if my_score == 0: failed_to_score += 1
                        if my_score > 0 and opp_score == 0: won_to_nil += 1
                        if my_score == 0 and opp_score > 0: lost_to_nil += 1
                        if my_score > 0 and opp_score > 0: btts += 1
                        if match_goals > 1.5: over_15 += 1
                        if match_goals > 2.5: over_25 += 1
                        if match_goals > 3.5: over_35 += 1
                        
                        goals = m.goals.all().order_by('minute')
                        if goals.exists():
                            first_goal = goals.first()
                            if first_goal.team == team:
                                scored_first_count += 1
                                minutes_scored_first.append(first_goal.minute)
                                if my_score > opp_score: won_when_scored_first += 1; pts_when_scored_first += 3
                                elif my_score == opp_score: pts_when_scored_first += 1
                            else:
                                conceded_first_count += 1
                                minutes_conceded_first.append(first_goal.minute)
                                if my_score >= opp_score: avoid_defeat_when_conceded_first += 1
                                if my_score > opp_score: pts_when_conceded_first += 3
                                elif my_score == opp_score: pts_when_conceded_first += 1

                    stats['ppg'] = points / n_matches
                    stats['win_pct'] = (wins / n_matches) * 100
                    stats['draw_pct'] = (draws / n_matches) * 100
                    stats['defeat_pct'] = (defeats / n_matches) * 100
                    stats['gf_pg'] = gf / n_matches
                    stats['ga_pg'] = ga / n_matches
                    stats['clean_sheet_pct'] = (clean_sheets / n_matches) * 100
                    stats['failed_to_score_pct'] = (failed_to_score / n_matches) * 100
                    stats['won_to_nil_pct'] = (won_to_nil / n_matches) * 100
                    stats['lost_to_nil_pct'] = (lost_to_nil / n_matches) * 100
                    stats['total_goals_pg'] = (gf + ga) / n_matches
                    stats['btts_pct'] = (btts / n_matches) * 100
                    stats['over_15_pct'] = (over_15 / n_matches) * 100
                    stats['over_25_pct'] = (over_25 / n_matches) * 100
                    stats['over_35_pct'] = (over_35 / n_matches) * 100
                    
                    if n_matches > 0:
                        stats['team_scored_first_pct'] = (scored_first_count / n_matches) * 100
                        stats['opponent_scored_first_pct'] = (conceded_first_count / n_matches) * 100
                    if scored_first_count > 0:
                        stats['avg_minute_scored_first'] = sum(minutes_scored_first) / len(minutes_scored_first)
                        stats['lead_defending_rate'] = (won_when_scored_first / scored_first_count) * 100
                        stats['ppg_scored_first'] = pts_when_scored_first / scored_first_count
                    if conceded_first_count > 0:
                        stats['avg_minute_conceded_first'] = sum(minutes_conceded_first) / len(minutes_conceded_first)
                        stats['equalizing_rate'] = (avoid_defeat_when_conceded_first / conceded_first_count) * 100
                        stats['ppg_conceded_first'] = pts_when_conceded_first / conceded_first_count
                        
                    output = []
                    def add_row(label, key, type='higher_better', is_pct=False, decimals=0):
                        t_val = stats.get(key, 0)
                        l_val = league_avg.get(key, 0)
                        is_good = (t_val >= l_val) if type == 'higher_better' else (t_val <= l_val)
                        ref = 100
                        if 'ppg' in key: ref = 3
                        elif 'pg' in key and 'ppg' not in key: ref = 4
                        elif 'minute' in key: ref = 90
                        
                        status_class = 'good' if is_good else 'bad'
                        if type == 'neutral': status_class = 'neutral'

                        output.append({
                            'label': label,
                            'team_val': t_val,
                            'league_val': l_val,
                            'is_good': is_good,
                            'type': type,
                            'is_pct': is_pct,
                            'decimals': decimals,
                            'team_width': min((t_val / ref) * 100, 100),
                            'league_width': min((l_val / ref) * 100, 100),
                            'status_class': status_class
                        })

                    add_row('Points per game', 'ppg', decimals=2)
                    add_row('% Wins', 'win_pct', is_pct=True)
                    add_row('% Draws', 'draw_pct', is_pct=True, type='neutral')
                    add_row('% Defeats', 'defeat_pct', type='lower_better', is_pct=True)
                    add_row('Goals scored per game', 'gf_pg', decimals=2)
                    add_row('Goals conceded per game', 'ga_pg', type='lower_better', decimals=2)
                    add_row('% Clean sheets', 'clean_sheet_pct', is_pct=True)
                    add_row('% Failed To Score', 'failed_to_score_pct', type='lower_better', is_pct=True)
                    add_row('% Won To Nil', 'won_to_nil_pct', is_pct=True)
                    add_row('% Lost To Nil', 'lost_to_nil_pct', type='lower_better', is_pct=True)
                    add_row('% Team scored first', 'team_scored_first_pct', is_pct=True)
                    add_row('% Opponent scored first', 'opponent_scored_first_pct', type='lower_better', is_pct=True)
                    add_row('Average minute scored first', 'avg_minute_scored_first', type='lower_better')
                    add_row('Average minute conceded first', 'avg_minute_conceded_first', type='higher_better')
                    add_row('Lead-defending rate', 'lead_defending_rate', is_pct=True)
                    add_row('Equalizing rate', 'equalizing_rate', is_pct=True)
                    add_row('% Time leading', 'time_leading_pct', is_pct=True)
                    add_row('% Time level in goals', 'time_level_pct', is_pct=True)
                    add_row('% Time trailing', 'time_trailing_pct', type='lower_better', is_pct=True)
                    add_row('PPG when scored first', 'ppg_scored_first', decimals=2)
                    add_row('PPG when conceded first', 'ppg_conceded_first', decimals=2)
                    add_row('Total goals per game', 'total_goals_pg', decimals=2)
                    add_row('% over 1.5 goals', 'over_15_pct', is_pct=True)
                    add_row('% over 2.5 goals', 'over_25_pct', is_pct=True)
                    add_row('% over 3.5 goals', 'over_35_pct', is_pct=True)
                    add_row('% both teams scored', 'btts_pct', is_pct=True)
                    return output

                def calculate_leading_trailing_stats(team, lg, season):
                    matches = Match.objects.filter(
                        models.Q(home_team=team) | models.Q(away_team=team),
                        league=lg, 
                        season=season, 
                        status__in=FINISHED_STATUSES
                    )
                    
                    n_matches = matches.count()
                    if n_matches == 0:
                        return None
                
                    stats = {
                        'matches_played': n_matches,
                        'team_scored_first': 0,
                        'opponent_scored_first': 0,
                        'scored_first_w': 0, 'scored_first_d': 0, 'scored_first_l': 0,
                        'conceded_first_w': 0, 'conceded_first_d': 0, 'conceded_first_l': 0,
                        'leading_at_ht': 0,
                        'opponent_leading_at_ht': 0,
                        'minutes_leading': 0,
                        'minutes_level': 0,
                        'minutes_trailing': 0,
                        'goals_giving_lead': 0,
                        'equalizer_goals_conceded': 0,
                        'goals_giving_lead_to_opponent': 0,
                        'equalizer_goals_scored': 0,
                        'non_crucial_scored': 0,
                        'non_crucial_conceded': 0,
                        'sum_minute_scored_first': 0,
                        'sum_minute_conceded_first': 0,
                        'avg_minute_scored_first': 0,
                        'avg_minute_conceded_first': 0,
                    }
                
                    for m in matches:
                        is_home = (m.home_team == team)
                        team_score = m.home_score if is_home else m.away_score
                        opp_score = m.away_score if is_home else m.home_score
                        
                        if team_score is None or opp_score is None: continue

                        if team_score > opp_score: result = 'W'
                        elif team_score == opp_score: result = 'D'
                        else: result = 'L'
                        
                        # HT Stats
                        if m.ht_home_score is not None and m.ht_away_score is not None:
                            ht_team = m.ht_home_score if is_home else m.ht_away_score
                            ht_opp = m.ht_away_score if is_home else m.ht_home_score
                            if ht_team > ht_opp:
                                stats['leading_at_ht'] += 1
                            elif ht_opp > ht_team:
                                stats['opponent_leading_at_ht'] += 1
                
                        # Goals analysis
                        goals = list(m.goals.all().order_by('minute'))
                        
                        # Opening Goal
                        if goals:
                            first_goal = goals[0]
                            if first_goal.team == team:
                                stats['team_scored_first'] += 1
                                stats['sum_minute_scored_first'] += first_goal.minute
                                if result == 'W': stats['scored_first_w'] += 1
                                elif result == 'D': stats['scored_first_d'] += 1
                                else: stats['scored_first_l'] += 1
                            else:
                                stats['opponent_scored_first'] += 1
                                stats['sum_minute_conceded_first'] += first_goal.minute
                                if result == 'W': stats['conceded_first_w'] += 1
                                elif result == 'D': stats['conceded_first_d'] += 1
                                else: stats['conceded_first_l'] += 1
                        
                        # Minute-by-minute & Goal types
                        current_team_score = 0
                        current_opp_score = 0
                        last_minute = 0
                        current_state = 0 # 0: Level, 1: Leading, -1: Trailing
                        
                        for g in goals:
                            minute = min(g.minute, 90)
                            duration = max(0, minute - last_minute)
                            
                            if current_state == 0:
                                stats['minutes_level'] += duration
                            elif current_state == 1:
                                stats['minutes_leading'] += duration
                            else:
                                stats['minutes_trailing'] += duration
                            
                            prev_diff = current_team_score - current_opp_score
                            
                            if g.team == team:
                                current_team_score += 1
                            else:
                                current_opp_score += 1
                                
                            new_diff = current_team_score - current_opp_score
                            
                            # Analyze Goal Type
                            if g.team == team:
                                if prev_diff == 0: stats['goals_giving_lead'] += 1
                                elif prev_diff == -1: stats['equalizer_goals_scored'] += 1
                                else: stats['non_crucial_scored'] += 1
                            else:
                                if prev_diff == 0: stats['goals_giving_lead_to_opponent'] += 1
                                elif prev_diff == 1: stats['equalizer_goals_conceded'] += 1
                                else: stats['non_crucial_conceded'] += 1
                            
                            if new_diff > 0: current_state = 1
                            elif new_diff < 0: current_state = -1
                            else: current_state = 0
                            
                            last_minute = minute
                        
                        duration = max(0, 90 - last_minute)
                        if current_state == 0: stats['minutes_level'] += duration
                        elif current_state == 1: stats['minutes_leading'] += duration
                        else: stats['minutes_trailing'] += duration
                
                    # Averages
                    stats['avg_minutes_leading'] = stats['minutes_leading'] / n_matches
                    stats['avg_minutes_level'] = stats['minutes_level'] / n_matches
                    stats['avg_minutes_trailing'] = stats['minutes_trailing'] / n_matches
                    
                    # Percentages
                    stats['pct_leading'] = (stats['avg_minutes_leading'] / 90) * 100
                    stats['pct_level'] = (stats['avg_minutes_level'] / 90) * 100
                    stats['pct_trailing'] = (stats['avg_minutes_trailing'] / 90) * 100
                    
                    stats['pct_scored_first'] = (stats['team_scored_first'] / n_matches) * 100
                    stats['pct_opp_scored_first'] = (stats['opponent_scored_first'] / n_matches) * 100
                    
                    stats['pct_leading_ht'] = (stats['leading_at_ht'] / n_matches) * 100
                    stats['pct_opp_leading_ht'] = (stats['opponent_leading_at_ht'] / n_matches) * 100
                    
                    if stats['team_scored_first'] > 0:
                        stats['avg_minute_scored_first'] = stats['sum_minute_scored_first'] / stats['team_scored_first']
                    
                    if stats['opponent_scored_first'] > 0:
                        stats['avg_minute_conceded_first'] = stats['sum_minute_conceded_first'] / stats['opponent_scored_first']

                    # Rates
                    if stats['goals_giving_lead'] > 0:
                        stats['lead_defending_rate'] = 100 - ((stats['equalizer_goals_conceded'] / stats['goals_giving_lead']) * 100)
                    else:
                        stats['lead_defending_rate'] = 0
                        
                    if stats['goals_giving_lead_to_opponent'] > 0:
                        stats['equalizing_rate'] = (stats['equalizer_goals_scored'] / stats['goals_giving_lead_to_opponent']) * 100
                    else:
                        stats['equalizing_rate'] = 0
                        
                    return stats

                context['t1_leading_trailing_stats'] = calculate_leading_trailing_stats(team1, league, latest_season)
                context['t2_leading_trailing_stats'] = calculate_leading_trailing_stats(team2, league, latest_season)

                # --- League Comparison Calculation ---
                def calculate_league_avg(lg, season):
                    matches = Match.objects.filter(league=lg, season=season, status__in=FINISHED_STATUSES)
                    total_matches = matches.count()
                    if total_matches == 0: return {}
                    
                    total_goals = 0
                    wins = 0
                    draws = 0
                    clean_sheets = 0
                    failed_to_score = 0
                    won_to_nil = 0
                    lost_to_nil = 0
                    both_teams_scored = 0
                    over_15 = 0
                    over_25 = 0
                    over_35 = 0
                    
                    for m in matches:
                        h_score = m.home_score or 0
                        a_score = m.away_score or 0
                        match_goals = h_score + a_score
                        total_goals += match_goals
                        
                        if h_score > a_score: wins += 1
                        elif a_score > h_score: wins += 1
                        else: draws += 1
                        
                        if a_score == 0: clean_sheets += 1
                        if h_score == 0: clean_sheets += 1
                        if h_score == 0: failed_to_score += 1
                        if a_score == 0: failed_to_score += 1
                        if h_score > 0 and a_score == 0: won_to_nil += 1
                        if a_score > 0 and h_score == 0: won_to_nil += 1
                        if h_score == 0 and a_score > 0: lost_to_nil += 1
                        if a_score == 0 and h_score > 0: lost_to_nil += 1
                        if h_score > 0 and a_score > 0: both_teams_scored += 1
                        if match_goals > 1.5: over_15 += 1
                        if match_goals > 2.5: over_25 += 1
                        if match_goals > 3.5: over_35 += 1

                    n_matches = total_matches
                    n_team_games = total_matches * 2
                    avg = {}
                    
                    avg['ppg'] = ((wins * 3) + (draws * 2)) / n_team_games
                    avg['win_pct'] = (wins / n_team_games) * 100
                    avg['draw_pct'] = ((draws * 2) / n_team_games) * 100
                    avg['defeat_pct'] = (wins / n_team_games) * 100
                    avg['gf_pg'] = total_goals / n_team_games
                    avg['ga_pg'] = total_goals / n_team_games
                    avg['clean_sheet_pct'] = (clean_sheets / n_team_games) * 100
                    avg['failed_to_score_pct'] = (failed_to_score / n_team_games) * 100
                    avg['won_to_nil_pct'] = (won_to_nil / n_team_games) * 100
                    avg['lost_to_nil_pct'] = (lost_to_nil / n_team_games) * 100
                    avg['total_goals_pg'] = total_goals / n_matches
                    avg['btts_pct'] = (both_teams_scored / n_matches) * 100
                    avg['over_15_pct'] = (over_15 / n_matches) * 100
                    avg['over_25_pct'] = (over_25 / n_matches) * 100
                    avg['over_35_pct'] = (over_35 / n_matches) * 100
                    return avg

                def calculate_team_comparison(team, lg, season, league_avg):
                    # Get leading/trailing stats first for complex metrics
                    lt_stats = calculate_leading_trailing_stats(team, lg, season)
                    
                    matches = Match.objects.filter(league=lg, season=season, status__in=FINISHED_STATUSES).filter(models.Q(home_team=team) | models.Q(away_team=team))
                    n_matches = matches.count()
                    if n_matches == 0: return []
                    
                    stats = {k: 0 for k in league_avg.keys()}
                    points, wins, draws, defeats = 0, 0, 0, 0
                    gf, ga = 0, 0
                    clean_sheets, failed_to_score = 0, 0
                    won_to_nil, lost_to_nil = 0, 0
                    btts, over_15, over_25, over_35 = 0, 0, 0, 0
                    
                    # We use lt_stats for these, so no need to accumulate them manually in the loop
                    # But we keep the loop for other stats
                    
                    for m in matches:
                        is_home = m.home_team == team
                        my_score = m.home_score if is_home else m.away_score
                        opp_score = m.away_score if is_home else m.home_score
                        if my_score is None: my_score = 0
                        if opp_score is None: opp_score = 0
                        match_goals = my_score + opp_score
                        
                        gf += my_score; ga += opp_score
                        if my_score > opp_score: wins += 1; points += 3
                        elif my_score == opp_score: draws += 1; points += 1
                        else: defeats += 1
                        
                        if opp_score == 0: clean_sheets += 1
                        if my_score == 0: failed_to_score += 1
                        if my_score > 0 and opp_score == 0: won_to_nil += 1
                        if my_score == 0 and opp_score > 0: lost_to_nil += 1
                        if my_score > 0 and opp_score > 0: btts += 1
                        if match_goals > 1.5: over_15 += 1
                        if match_goals > 2.5: over_25 += 1
                        if match_goals > 3.5: over_35 += 1
                        
                    stats['ppg'] = points / n_matches
                    stats['win_pct'] = (wins / n_matches) * 100
                    stats['draw_pct'] = (draws / n_matches) * 100
                    stats['defeat_pct'] = (defeats / n_matches) * 100
                    stats['gf_pg'] = gf / n_matches
                    stats['ga_pg'] = ga / n_matches
                    stats['clean_sheet_pct'] = (clean_sheets / n_matches) * 100
                    stats['failed_to_score_pct'] = (failed_to_score / n_matches) * 100
                    stats['won_to_nil_pct'] = (won_to_nil / n_matches) * 100
                    stats['lost_to_nil_pct'] = (lost_to_nil / n_matches) * 100
                    stats['total_goals_pg'] = (gf + ga) / n_matches
                    stats['btts_pct'] = (btts / n_matches) * 100
                    stats['over_15_pct'] = (over_15 / n_matches) * 100
                    stats['over_25_pct'] = (over_25 / n_matches) * 100
                    stats['over_35_pct'] = (over_35 / n_matches) * 100
                    
                    # Populate from lt_stats
                    if lt_stats:
                        stats['team_scored_first_pct'] = lt_stats['pct_scored_first']
                        stats['opponent_scored_first_pct'] = lt_stats['pct_opp_scored_first']
                        stats['avg_minute_scored_first'] = lt_stats['avg_minute_scored_first']
                        stats['avg_minute_conceded_first'] = lt_stats['avg_minute_conceded_first']
                        stats['lead_defending_rate'] = lt_stats['lead_defending_rate']
                        stats['equalizing_rate'] = lt_stats['equalizing_rate']
                        stats['time_leading_pct'] = lt_stats['pct_leading']
                        stats['time_level_pct'] = lt_stats['pct_level']
                        stats['time_trailing_pct'] = lt_stats['pct_trailing']
                        
                        if lt_stats['team_scored_first'] > 0:
                            pts = (lt_stats['scored_first_w'] * 3) + (lt_stats['scored_first_d'] * 1)
                            stats['ppg_scored_first'] = pts / lt_stats['team_scored_first']
                        
                        if lt_stats['opponent_scored_first'] > 0:
                            pts = (lt_stats['conceded_first_w'] * 3) + (lt_stats['conceded_first_d'] * 1)
                            stats['ppg_conceded_first'] = pts / lt_stats['opponent_scored_first']
                        
                    output = []
                    def add_row(label, key, type='higher_better', is_pct=False, decimals=0):
                        t_val = stats.get(key, 0)
                        l_val = league_avg.get(key, 0)
                        is_good = (t_val >= l_val) if type == 'higher_better' else (t_val <= l_val)
                        ref = 100
                        if 'ppg' in key: ref = 3
                        elif 'pg' in key and 'ppg' not in key: ref = 4
                        elif 'minute' in key: ref = 90
                        
                        output.append({
                            'label': label,
                            'team_val': t_val,
                            'league_val': l_val,
                            'is_good': is_good,
                            'type': type,
                            'is_pct': is_pct,
                            'decimals': decimals,
                            'team_width': min((t_val / ref) * 100, 100),
                            'league_width': min((l_val / ref) * 100, 100)
                        })

                    add_row('Points per game', 'ppg', decimals=2)
                    add_row('% Wins', 'win_pct', is_pct=True)
                    add_row('% Draws', 'draw_pct', is_pct=True, type='neutral')
                    add_row('% Defeats', 'defeat_pct', type='lower_better', is_pct=True)
                    add_row('Goals scored per game', 'gf_pg', decimals=2)
                    add_row('Goals conceded per game', 'ga_pg', type='lower_better', decimals=2)
                    add_row('% Clean sheets', 'clean_sheet_pct', is_pct=True)
                    add_row('% Failed To Score', 'failed_to_score_pct', type='lower_better', is_pct=True)
                    add_row('% Won To Nil', 'won_to_nil_pct', is_pct=True)
                    add_row('% Lost To Nil', 'lost_to_nil_pct', type='lower_better', is_pct=True)
                    add_row('% Team scored first', 'team_scored_first_pct', is_pct=True)
                    add_row('% Opponent scored first', 'opponent_scored_first_pct', type='lower_better', is_pct=True)
                    add_row('Average minute scored first', 'avg_minute_scored_first', type='lower_better')
                    add_row('Average minute conceded first', 'avg_minute_conceded_first', type='higher_better')
                    add_row('Lead-defending rate', 'lead_defending_rate', is_pct=True)
                    add_row('Equalizing rate', 'equalizing_rate', is_pct=True)
                    add_row('% Time leading', 'time_leading_pct', is_pct=True)
                    add_row('% Time level in goals', 'time_level_pct', is_pct=True)
                    add_row('% Time trailing', 'time_trailing_pct', type='lower_better', is_pct=True)
                    add_row('PPG when scored first', 'ppg_scored_first', decimals=2)
                    add_row('PPG when conceded first', 'ppg_conceded_first', decimals=2)
                    add_row('Total goals per game', 'total_goals_pg', decimals=2)
                    add_row('% over 1.5 goals', 'over_15_pct', is_pct=True)
                    add_row('% over 2.5 goals', 'over_25_pct', is_pct=True)
                    add_row('% over 3.5 goals', 'over_35_pct', is_pct=True)
                    add_row('% both teams scored', 'btts_pct', is_pct=True)
                    return output

                league_avg_stats = calculate_league_avg(league, latest_season)
                context['t1_league_comparison'] = calculate_team_comparison(team1, league, latest_season, league_avg_stats)
                context['t2_league_comparison'] = calculate_team_comparison(team2, league, latest_season, league_avg_stats)

        else:
            context['matches'] = []

        return context
