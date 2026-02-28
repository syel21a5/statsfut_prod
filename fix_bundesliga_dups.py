import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from matches.models import League, LeagueStanding, Team, Match
from django.db.models import Q

def clean_bundesliga():
    try:
        league = League.objects.get(name='Bundesliga', country='Alemanha')
        print(f"Checking {league} (ID: {league.id})...")
        
        # Get all standings for 2026
        standings = LeagueStanding.objects.filter(league=league, season__year=2026)
        print(f"\nTotal Teams in Standings (2026): {standings.count()}")
        
        # List of expected teams (from localhost verification)
        expected_teams = [
            'Bayern Munich', 'Dortmund', 'Hoffenheim', 'Stuttgart', 'Leipzig', 
            'Leverkusen', 'Freiburg', 'Augsburg', 'Frankfurt', 'Union Berlin', 
            'Hamburg', 'Koln', 'Mainz', 'M Gladbach', 'St Pauli', 
            'Wolfsburg', 'Werder Bremen', 'Heidenheim'
        ]
        
        print("\n--- TEAMS TO REMOVE ---")
        count_removed = 0
        
        # We need to iterate over a list because we might modify the queryset
        for s in list(standings):
            # STRICT MODE: If it's not in the expected list, it goes.
            if s.team.name not in expected_teams:
                 print(f"REMOVING INTRUDER: {s.team.name} (Played: {s.played}, Points: {s.points})")
                 
                 # CRITICAL: Also remove the MATCHES associated with this team in this league!
                 # If we don't, recalculate_standings will just bring them back.
                 matches_to_delete = Match.objects.filter(
                     league=league,
                     season__year=2026
                 ).filter(
                     Q(home_team=s.team) | Q(away_team=s.team)
                 )
                 
                 matches_count = matches_to_delete.count()
                 if matches_count > 0:
                     print(f"   -> Deleting {matches_count} matches for {s.team.name} in Bundesliga...")
                     matches_to_delete.delete()
                 
                 s.delete()
                 count_removed += 1

            elif s.played < 10:
                # Still check for legitimate teams with suspiciously low games (duplicates/ghosts)
                print(f"REMOVING GHOST: {s.team.name} (Played: {s.played}, Points: {s.points})")
                
                # Also delete matches for ghosts
                 matches_to_delete = Match.objects.filter(
                      league=league,
                      season__year=2026
                 ).filter(
                     Q(home_team=s.team) | Q(away_team=s.team)
                 )
                 matches_to_delete.delete()
                 
                 s.delete()
                 count_removed += 1
        
        print(f"\nTotal removed: {count_removed}")
        print("Recalculating standings to ensure consistency...")
        
        from django.core.management import call_command
        call_command('recalculate_standings', league_name='Bundesliga', country='Alemanha')
        
    except League.DoesNotExist:
        print("League not found")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    clean_bundesliga()
