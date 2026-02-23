import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, LeagueStanding

def inspect_standings():
    try:
        league = League.objects.get(pk=27)
        print(f"Checking standings for {league.name} (ID: 27)")
        
        standings = LeagueStanding.objects.filter(league=league).select_related('team').order_by('team__name')
        
        print(f"Found {standings.count()} standing entries")
        
        unique_teams = set()
        for s in standings:
            unique_teams.add(f"{s.team.name} (ID: {s.team.id})")
            
        for t in sorted(list(unique_teams)):
            print(t)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_standings()
