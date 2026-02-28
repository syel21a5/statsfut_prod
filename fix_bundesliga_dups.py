import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from matches.models import League, LeagueStanding, Team, Match

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
        for s in standings:
            # Criteria for removal: Less than 10 games played OR not in expected list
            # We use a safe threshold (e.g., < 5 games) because valid teams have ~22 games
            if s.played < 10: 
                print(f"REMOVING: {s.team.name} (Played: {s.played}, Points: {s.points})")
                s.delete()
                count_removed += 1
            elif s.team.name not in expected_teams:
                 # Check if it's just a name variation
                 print(f"POTENTIAL REMOVAL (Name Mismatch): {s.team.name} (Played: {s.played})")
                 # Decide to remove if played count is suspicious compared to others
                 if s.played < 15:
                     print(f"   -> CONFIRMED REMOVE (Low Games): {s.team.name}")
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
