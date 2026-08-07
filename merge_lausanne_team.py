import os, sys, django
# Adjust path if necessary
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, Match, LeagueStanding, League
from django.db import transaction

def merge_lausanne():
    print("=== Cleanup: Merging Lausanne Duplicates ===")
    
    # IDs found locally (might be different on server, so we fetch by name and league)
    try:
        league = League.objects.get(id=40)
        print(f"League found: {league.name} ({league.country})")
    except League.DoesNotExist:
        print("League with ID 40 not found!")
        return

    # 1. Identify teams
    correct_team = Team.objects.filter(name='FC Lausanne-Sport', league=league).first()
    wrong_team = Team.objects.filter(name='Lausanne', league=league).first()

    if not correct_team:
        print("Correct team 'FC Lausanne-Sport' not found!")
        return
    if not wrong_team:
        print("Wrong team 'Lausanne' (duplicate) not found! Nothing to do.")
        return

    print(f"Merging Team '{wrong_team.name}' (ID {wrong_team.id}) into '{correct_team.name}' (ID {correct_team.id})...")

    with transaction.atomic():
        # A. Move Matches
        home_matches_updated = Match.objects.filter(home_team=wrong_team).update(home_team=correct_team)
        away_matches_updated = Match.objects.filter(away_team=wrong_team).update(away_team=correct_team)
        print(f"  Moved {home_matches_updated} home matches and {away_matches_updated} away matches.")

        # B. Delete Standings for the wrong team
        standings_deleted = LeagueStanding.objects.filter(team=wrong_team).delete()[0]
        print(f"  Deleted {standings_deleted} standing records for the duplicate team.")

        # C. Delete the wrong team
        wrong_team.delete()
        print(f"  Deleted duplicate team record.")

    print("\nCleanup complete! Don't forget to run recalculate_standings.")
    
    # 2. Trigger recalculation for the league
    print("\nRecalculating standings for Super League (Suica)...")
    from django.core.management import call_command
    call_command('recalculate_standings', league_name='Super League', country='Suica', season_year=2026)
    
    print("\n=== All Done! ===")

if __name__ == "__main__":
    merge_lausanne()
