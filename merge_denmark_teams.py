
import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from matches.models import Team, Match, LeagueStanding, League

def merge_teams(league_name, team_map):
    try:
        league = League.objects.get(name=league_name, country='Dinamarca')
        print(f"Processing league: {league} (ID: {league.id})")
        
        all_teams = {t.name: t for t in Team.objects.filter(league=league)}
        print(f"Found {len(all_teams)} teams in league.")
        print("Teams found:", list(all_teams.keys()))
        
        for old_name, new_name in team_map.items():
            if old_name not in all_teams:
                print(f"  - Skip: Old Team '{old_name}' not found in DB.")
                continue
            if new_name not in all_teams:
                print(f"  - Skip: New Team '{new_name}' not found in DB.")
                continue
                
            old_team = all_teams[old_name]
            new_team = all_teams[new_name]
            
            try:
                print(f"\nMerging '{old_team.name}' (ID {old_team.id}) into '{new_team.name}' (ID {new_team.id})...")
                
                # Update Home Matches
                updated_home = Match.objects.filter(home_team=old_team).update(home_team=new_team)
                print(f"  - Updated {updated_home} home matches.")
                
                # Update Away Matches
                updated_away = Match.objects.filter(away_team=old_team).update(away_team=new_team)
                print(f"  - Updated {updated_away} away matches.")
                
                # Handle Standings
                for standing in LeagueStanding.objects.filter(team=old_team):
                    if not LeagueStanding.objects.filter(team=new_team, season=standing.season, league=standing.league).exists():
                        standing.team = new_team
                        standing.save()
                        print(f"  - Moved standing for Season {standing.season.year}.")
                    else:
                        standing.delete()
                        print(f"  - Deleted duplicate standing for Season {standing.season.year}.")
                
                # Delete Old Team
                old_team.delete()
                print(f"  - Deleted old team '{old_name}'.")
                
            except Team.DoesNotExist:
                print(f"  - Skip: Team '{old_name}' or '{new_name}' not found.")
            except Exception as e:
                print(f"  - Error merging '{old_name}': {e}")
                
    except League.DoesNotExist:
        print(f"League '{league_name}' not found.")

if __name__ == "__main__":
    # Map: Old Name -> New Name
    mapping = {
        'Aarhus': 'AGF Aarhus',
        'Brondby': 'Brondby IF',
        'FC Copenhagen': 'FC Kobenhavn',
        'Midtjylland': 'FC Midtjylland',
        'Odense': 'Odense BK',
        'Vejle': 'Vejle BK'
    }
    
    merge_teams('Superliga', mapping)
