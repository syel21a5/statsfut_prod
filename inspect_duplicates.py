import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Match, Team, Season
from django.db.models import Count, Q

def inspect_matches():
    league = League.objects.filter(name__icontains="Bundesliga", country="Austria").first()
    if not league:
        print("Liga não encontrada.")
        return

    print(f"Inspecionando liga: {league.name}")
    
    # Check for duplicate teams
    teams = Team.objects.filter(name__icontains="Salzburg")
    print("\nTimes 'Salzburg':")
    for t in teams:
        print(f"  ID: {t.id} | Name: {t.name}")
        
    teams = Team.objects.filter(name__icontains="LASK")
    print("\nTimes 'LASK':")
    for t in teams:
        print(f"  ID: {t.id} | Name: {t.name}")

    # Check matches between LASK and Salzburg across ALL seasons
    print("\nJogos LASK vs Salzburg (All Time):")
    matches = Match.objects.filter(
        league=league,
        home_team__name__icontains="LASK",
        away_team__name__icontains="Salzburg"
    ).order_by('date')
    
    for m in matches:
        season_year = m.season.year if m.season else "None"
        print(f"ID: {m.id} | Date: {m.date} | Season: {season_year} | {m.home_team.name}({m.home_team.id}) vs {m.away_team.name}({m.away_team.id}) | Score: {m.home_score}-{m.away_score}")

if __name__ == "__main__":
    inspect_matches()
