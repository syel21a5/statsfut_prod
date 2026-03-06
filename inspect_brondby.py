
import os
import django
import sys
from django.db.models import Count

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from matches.models import Team, Match, League

def inspect():
    try:
        team_name = 'Brondby IF'
        team = Team.objects.filter(name=team_name).first()
        if not team:
            print(f"Team {team_name} not found.")
            return

        print(f"Team: {team.name} (ID: {team.id})")
        print(f"Total Matches: {Match.objects.filter(home_team=team).count() + Match.objects.filter(away_team=team).count()}")

        print("\n--- Matches by League ---")
        # Group matches by league
        matches = Match.objects.filter(home_team=team).values('league__name', 'league__country', 'league__id').annotate(count=Count('id')).order_by('-count')
        
        for m in matches:
            print(f"League: {m['league__name']} ({m['league__country']}) ID: {m['league__id']} - {m['count']} matches")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect()
