
import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from matches.models import League, Match, Team

def inspect():
    try:
        league = League.objects.get(name='Superliga', country='Dinamarca')
        team = Team.objects.get(name='Fredericia', league=league)
        print(f"Team: {team.name}")
        
        matches = Match.objects.filter(league=league, season__year=2026).filter(home_team=team)
        print(f"Home Matches in Season 2026: {matches.count()}")
        for m in matches:
            print(f"  vs {m.away_team.name} ({m.date})")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect()
