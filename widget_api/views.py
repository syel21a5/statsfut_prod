from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from matches.models import LeagueStanding, League

@cache_page(60 * 15)  # Cache por 15 minutos (proteção do servidor)
def widget_brasileirao_view(request):
    try:
        # Busca a Série A do Brasil
        league = League.objects.filter(country='Brazil', name__icontains='Serie A').first()
        if not league:
            return JsonResponse({'error': 'League not found'}, status=404)
        
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
