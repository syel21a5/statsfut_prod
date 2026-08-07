import os, sys, django
# Adjust path if necessary
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, LeagueStanding, League, Season

def diagnose_lausanne():
    print("=== Diagnostic: Switzerland Super League (ID 40) ===")
    
    try:
        league = League.objects.get(id=40)
        print(f"League found: {league.name}")
    except League.DoesNotExist:
        print("League with ID 40 not found!")
        return

    # 1. Find all teams with "Lausanne" in their name
    print("\n--- Teams named 'Lausanne' ---")
    lausanne_teams = Team.objects.filter(name__icontains='Lausanne')
    for team in lausanne_teams:
        standings_count = LeagueStanding.objects.filter(team=team).count()
        matches_as_home = team.home_matches.count()
        matches_as_away = team.away_matches.count()
        print(f"ID={team.id}, Name={team.name}, Standings={standings_count}, Matches(H/A)={matches_as_home}/{matches_as_away}")

    # 2. Check current standings for League 40
    # Let's see all seasons for this league
    print("\n--- Standings by Season ---")
    standings = LeagueStanding.objects.filter(league=league).order_by('-season_id', 'position')
    
    current_season_id = None
    if standings.exists():
        current_season_id = standings.first().season_id
    
    from collections import defaultdict
    by_season = defaultdict(list)
    for s in standings:
        by_season[s.season_id].append(s)
        
    for season_id, entries in sorted(by_season.items(), reverse=True):
        print(f"\nSeason ID: {season_id} ({len(entries)} teams)")
        for s in entries:
            print(f"  #{s.position} {s.team.name} (ID:{s.team_id}) - PTS={s.points}, GP={s.played}")

    print("\n=== End of Diagnostic ===")

if __name__ == "__main__":
    diagnose_lausanne()
