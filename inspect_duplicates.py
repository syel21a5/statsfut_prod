import os
import django
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Match, Season, Team
from django.db.models import Count, Q

def inspect_matches():
    league = League.objects.filter(name__icontains="Bundesliga", country="Austria").first()
    if not league:
        print("Liga não encontrada.")
        return

    # Get latest season
    season = Season.objects.filter(matches__league=league).order_by('-year').first()
    print(f"Inspecionando Season {season.year} da liga: {league.name}")
    
    # Check Season 2025
    season_2025 = Season.objects.filter(year=2025).first()
    if season_2025:
        print(f"Inspecionando Season {season_2025.year} da liga: {league.name}")
        matches_2025 = Match.objects.filter(league=league, season=season_2025, home_team__name__icontains="Salzburg") | \
                       Match.objects.filter(league=league, season=season_2025, away_team__name__icontains="Salzburg")
        print(f"Total de jogos do Salzburg na Season 2025: {matches_2025.count()}")

if __name__ == "__main__":
    inspect_matches()
