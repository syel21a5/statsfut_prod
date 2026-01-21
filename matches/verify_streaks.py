import os
import django
import sys
from datetime import date

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Match, Team, League, Season, LeagueStanding
from matches.views import TeamDetailView
from django.db import models

# Mocking the request/object for view method
class MockView(TeamDetailView):
    def __init__(self):
        self.object = None

try:
    # 1. Fetch a team and league (Arsenal, Premier League) - Adjust names if needed
    league = League.objects.filter(name__icontains="Premier League").first()
    if not league:
        print("League not found for testing. Using first available.")
        league = League.objects.first()
    
    if not league:
        print("No leagues in DB. Skipping test.")
        exit(0)

    team = Team.objects.filter(league=league).first()
    if not team:
        print("No teams in DB. Skipping test.")
        exit(0)
    
    print(f"Testing with Team: {team.name}, League: {league.name}")

    # 2. Get latest season
    latest_season = Season.objects.filter(standings__league=league).order_by('-year').first()
    if not latest_season:
        print("No season found.")
        exit(0)

    # 3. Simulate get_context_data logic (partially)
    # We just want to call calculate_streaks and checking historical stats logic
    
    view = MockView()
    
    # Get all matches for this team
    all_matches = Match.objects.filter(
        league=league, season=latest_season
    ).filter(
        models.Q(home_team=team) | models.Q(away_team=team)
    ).order_by('date')
    
    print(f"Total Matches found: {len(all_matches)}")
    
    # Test calculate_streaks
    try:
        streaks = view.calculate_streaks(all_matches, team)
        print("\n--- Streaks Calculation Success ---")
        print(f"Current Wins Streak (Total): {streaks['total']['win']}")
        print(f"Current No-Defeat Streak (Home): {streaks['home']['no_defeat']}")
    except Exception as e:
        print(f"Error in calculate_streaks: {e}")
        import traceback
        traceback.print_exc()

    # Test Historical Stats Logic
    past_seasons = Season.objects.filter(standings__league=league).exclude(id=latest_season.id).distinct().order_by('-year')
    if past_seasons:
        prev_season = past_seasons[0]
        print(f"\nPrevious Season found: {prev_season.year}")
        
        # Copied logic snippet from views.py for validation
        def calc_historical(matches_qs, t):
                stats = {'pld': 0, 'pts': 0, 'gf': 0, 'ga': 0, 'w': 0, 'd': 0, 'l': 0, 'cs': 0, 'fts': 0}
                if not matches_qs: return stats
                stats['pld'] = len(matches_qs)
                for m in matches_qs:
                    is_home = m.home_team == t
                    my_score = m.home_score if is_home else m.away_score
                    opp_score = m.away_score if is_home else m.home_score
                    
                    if my_score is None or opp_score is None: continue 
                    
                    stats['gf'] += my_score
                    stats['ga'] += opp_score
                    
                    if my_score > opp_score: 
                        stats['w'] += 1
                        stats['pts'] += 3
                    elif my_score == opp_score: 
                        stats['d'] += 1
                        stats['pts'] += 1
                    else: 
                        stats['l'] += 1
                        
                    if opp_score == 0: stats['cs'] += 1
                    if my_score == 0: stats['fts'] += 1
                
                if stats['pld'] > 0:
                    stats['w_pct'] = round((stats['w'] / stats['pld']) * 100)
                return stats

        prev_matches = Match.objects.filter(
                league=league, season=prev_season, status='Finished'
            ).filter(models.Q(home_team=team) | models.Q(away_team=team))
        
        hist_stats = calc_historical(prev_matches, team)
        print(f"Previous Season Stats (Overall): Matches={hist_stats['pld']}, Pts={hist_stats['pts']}")
    else:
        print("No past seasons to test historical logic.")

except Exception as e:
    print(f"General Error: {e}")
    import traceback
    traceback.print_exc()
