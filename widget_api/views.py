from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from matches.models import LeagueStanding, League, Match
from django.utils import timezone

from django.db.models import Q

@cache_page(60 * 15)  # Cache por 15 minutos (proteção do servidor)
def widget_brasileirao_view(request):
    try:
        # Busca a Série A do Brasil com mais flexibilidade (aceita Brasil ou Brazil)
        league = League.objects.filter(
            Q(country__icontains='Brazil') | Q(country__icontains='Brasil')
        ).filter(
            Q(name__icontains='Serie A') | Q(name__icontains='Série A') | Q(name__icontains='Brasileir') | Q(division=1)
        ).first()
        
        if not league:
            # Para depuração: lista o que tem de Brasil
            br_leagues = list(League.objects.filter(country='Brazil').values_list('name', flat=True)[:5])
            return JsonResponse({'error': 'League not found', 'available_brazil_leagues': br_leagues}, status=404)
        
        # Pega a tabela da temporada mais recente, ordenado pela posição
        standings = LeagueStanding.objects.filter(league=league)\
                                          .select_related('team')\
                                          .order_by('-season__year', 'position')[:10]  # Top 10
        
        data = []
        for s in standings:
            # Pega a URL do logo e garante que tenha o domínio completo
            logo = s.team.logo_url
            if logo and logo.startswith('/'):
                logo = f"https://statsfut.com{logo}"
                
            data.append({
                'position': s.position,
                'team': s.team.name,
                'logo_url': logo,
                'points': s.points,
                'played': s.played,
                'won': s.won,
                'drawn': s.drawn,
                'lost': s.lost,
                'goals_for': s.goals_for,
                'goals_against': s.goals_against,
            })
            
        return JsonResponse({'league': 'Série A - Brasil', 'standings': data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@cache_page(60 * 15)
def widget_league_view(request, country, league):
    try:
        limit = int(request.GET.get('limit', 20))
        country_clean = country.replace('-', ' ')
        league_clean = league.replace('-', ' ')
        
        # Busca a liga pelo pais e nome
        league_obj = League.objects.filter(
            Q(country__icontains=country_clean) | Q(country__icontains=country_clean.replace('z', 's'))
        ).filter(
            Q(name__icontains=league_clean)
        ).first()
        
        if not league_obj:
            return JsonResponse({'error': 'League not found'}, status=404)
            
        standings = LeagueStanding.objects.filter(league=league_obj)\
                                          .select_related('team')\
                                          .order_by('-season__year', 'position')[:limit]
        
        data = []
        for s in standings:
            logo = s.team.logo_url
            if logo and logo.startswith('/'):
                logo = f"https://statsfut.com{logo}"
                
            data.append({
                'position': s.position,
                'team': s.team.name,
                'logo_url': logo,
                'points': s.points,
                'played': s.played,
                'won': s.won,
                'drawn': s.drawn,
                'lost': s.lost,
                'goals_for': s.goals_for,
                'goals_against': s.goals_against,
            })
            
        return JsonResponse({'league': f"{league_obj.name} - {league_obj.country}", 'standings': data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@cache_page(60 * 15)
def widget_upcoming_matches_view(request, country, league):
    try:
        limit = int(request.GET.get('limit', 10))
        country_clean = country.replace('-', ' ')
        league_clean = league.replace('-', ' ')
        
        league_obj = League.objects.filter(
            Q(country__icontains=country_clean) | Q(country__icontains=country_clean.replace('z', 's'))
        ).filter(
            Q(name__icontains=league_clean)
        ).first()
        
        if not league_obj:
            return JsonResponse({'error': 'League not found'}, status=404)
            
        now = timezone.now()
        upcoming = Match.objects.filter(
            league=league_obj, 
            date__gte=now
        ).select_related('home_team', 'away_team').order_by('date')[:limit]
        
        data = []
        for m in upcoming:
            home_logo = m.home_team.logo_url
            away_logo = m.away_team.logo_url
            if home_logo and home_logo.startswith('/'): home_logo = f"https://statsfut.com{home_logo}"
            if away_logo and away_logo.startswith('/'): away_logo = f"https://statsfut.com{away_logo}"
            
            slug = f"{m.home_team.name.lower().replace(' ', '-')}-vs-{m.away_team.name.lower().replace(' ', '-')}"
            
            data.append({
                'id': m.id,
                'date': m.date.isoformat() if m.date else None,
                'home_team': m.home_team.name,
                'home_logo': home_logo,
                'away_team': m.away_team.name,
                'away_logo': away_logo,
                'match_url': f"https://statsfut.com/match/{m.id}/{slug}/"
            })
            
        return JsonResponse({'league': f"{league_obj.name} - {league_obj.country}", 'matches': data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

