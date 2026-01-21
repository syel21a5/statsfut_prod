import os
import django
from datetime import datetime, timedelta
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, Match, League, Season

def seed_future():
    arsenal = Team.objects.get(name='Arsenal')
    league = League.objects.first()
    season = Season.objects.last()
    
    # Get other teams
    opponents = list(Team.objects.filter(league=league).exclude(id=arsenal.id))
    if not opponents:
        print("No opponents found!")
        return

    # Clear existing future matches for Arsenal to avoid duplicates if re-run
    Match.objects.filter(
        models.Q(home_team=arsenal) | models.Q(away_team=arsenal),
        status='Scheduled',
        date__gte=datetime.now()
    ).delete()

    print("Seeding future matches for Arsenal...")
    
    start_date = datetime.now() + timedelta(days=2)
    
    for i in range(15): # Create 15 matches
        match_date = start_date + timedelta(days=i*7) # One match per week
        opponent = random.choice(opponents)
        
        is_home = i % 2 == 0 # Alternate home/away
        
        if is_home:
            home = arsenal
            away = opponent
        else:
            home = opponent
            away = arsenal
            
        Match.objects.create(
            league=league,
            season=season,
            date=match_date,
            home_team=home,
            away_team=away,
            status='Scheduled'
        )
        print(f"Created {'Home' if is_home else 'Away'} match vs {opponent.name} on {match_date.strftime('%d %b')}")

if __name__ == '__main__':
    from django.db import models
    seed_future()
