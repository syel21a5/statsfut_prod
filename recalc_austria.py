from matches.models import League, Season, LeagueStanding
from matches.utils import calculate_standings
from django.utils import timezone

try:
    league = League.objects.get(name='Bundesliga', country='Austria')
    print(f"League found: {league}")
    
    seasons = Season.objects.filter(match__league=league).distinct()
    print(f"Seasons found with matches: {[s.year for s in seasons]}")
    
    for season in seasons:
        print(f"Recalculating standings for {season.year}...")
        calculate_standings(league, season)
        
        count = LeagueStanding.objects.filter(league=league, season=season).count()
        print(f"  -> Standings count: {count}")

    print("Done.")

except League.DoesNotExist:
    print("League 'Bundesliga' (Austria) not found.")
except Exception as e:
    print(f"Error: {e}")
