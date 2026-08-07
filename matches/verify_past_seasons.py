import os
import django
import sys

# Setup Django environment
# Add the project root to sys.path
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'betstats_python.settings')
django.setup()

from matches.models import Team, Season, League, Match, LeagueStanding
from django.db import models

def verify_past_seasons(league_name, team_name):
    # This logic mimics TeamDetailView
    league = League.objects.filter(name__icontains=league_name).first()
    team = Team.objects.filter(league=league, name__icontains=team_name).first()
    
    latest_season = Season.objects.filter(standings__league=league).order_by('-year').first()
    standing = LeagueStanding.objects.filter(league=league, season=latest_season, team=team).first()
    
    print(f"Team: {team}")
    print(f"Current Season: {latest_season}")
    print(f"Current Stats: Played={standing.played}, Pts={standing.points}")
    
    current_gp = standing.played
    current_pts = standing.points
    
    past_seasons = Season.objects.filter(standings__league=league).exclude(id=latest_season.id).order_by('-year')
    
    print("\n--- Past Seasons Data ---")
    for season in past_seasons:
        season_matches = Match.objects.filter(
            league=league, season=season, status='Finished'
        ).filter(models.Q(home_team=team) | models.Q(away_team=team)).order_by('date')
        
        subset = season_matches[:current_gp]
        gp = len(subset)
        
        if gp > 0:
            pts = 0
            for m in subset:
                is_home = m.home_team == team
                s = m.home_score if is_home else m.away_score
                o = m.away_score if is_home else m.home_score
                if s > o: pts += 3
                elif s == o: pts += 1
            
            diff = current_pts - pts
            print(f"Season {season}: GP={gp}, Pts={pts}, Diff={diff}")
        else:
            print(f"Season {season}: No comparable data")

verify_past_seasons('Premier League', 'Arsenal')
