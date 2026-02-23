import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db.models import Q
from matches.models import Team, League, Match

def inspect_spain():
    print("Starting inspection...", flush=True)
    try:
        leagues = League.objects.filter(pk=27)
        print(f"Leagues found: {leagues.count()}", flush=True)
        
        for league in leagues:
            print(f"League: {league.name} (ID: {league.id})", flush=True)
            
            matches = Match.objects.filter(league=league).select_related('home_team', 'away_team')
            print(f"Matches count: {matches.count()}", flush=True)
            
            teams = set()
            for m in matches:
                teams.add(m.home_team)
                teams.add(m.away_team)
            
            print(f"Teams found via matches: {len(teams)}", flush=True)
            
            sorted_teams = sorted(list(teams), key=lambda t: t.name)
            for team in sorted_teams:
                print(f"  - {team.name} (ID: {team.id})", flush=True)

    except Exception as e:
        print(f"Error: {e}", flush=True)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    inspect_spain()
