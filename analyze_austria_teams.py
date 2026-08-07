import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Season, Team, Match
from collections import defaultdict

def analyze_teams():
    league = League.objects.filter(name='Bundesliga', country='Austria').first()
    if not league:
        print("Liga não encontrada")
        return

    seasons = Season.objects.filter(year__gte=2017, year__lte=2025).order_by('year')
    print(f"--- Análise de Times por Temporada: {league.name} ---")
    
    for season in seasons:
        # Pega todos os matches desta temporada
        matches = Match.objects.filter(league=league, season=season)
        
        # Extrai os IDs de todos os times que jogaram (home e away)
        team_ids = set()
        for m in matches:
            if m.home_team_id: team_ids.add(m.home_team_id)
            if m.away_team_id: team_ids.add(m.away_team_id)
            
        teams = Team.objects.filter(id__in=team_ids).order_by('name')
        
        print(f"\nTemporada {season.year-1}/{season.year} ({matches.count()} jogos): {teams.count()} times")
        for t in teams:
            print(f"  - {t.name}")

if __name__ == '__main__':
    analyze_teams()
