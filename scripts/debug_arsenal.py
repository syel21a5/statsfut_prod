from matches.models import Team, Match, League
from django.utils import timezone

def check_arsenal():
    try:
        league = League.objects.get(name="Premier League")
        arsenal = Team.objects.get(name="Arsenal", league=league)
        
        matches = Match.objects.filter(
            league=league
        ).filter(
            home_team=arsenal
        ) | Match.objects.filter(
            league=league
        ).filter(
            away_team=arsenal
        )
        
        print(f"Total Matches Found: {matches.count()}")
        
        print("\n--- Games Played (Status='Finished') ---")
        played = matches.filter(status='Finished').order_by('date')
        print(f"Count: {played.count()}")
        for m in played:
            print(f"{m.date.date()} - {m.home_team} {m.home_score}x{m.away_score} {m.away_team} [Status: {m.status}, ID: {m.api_id}]")
            
        print("\n--- Future Games ---")
        future = matches.exclude(status='Finished').order_by('date')
        for m in future:
            print(f"{m.date.date() if m.date else 'No Date'} - {m.home_team} vs {m.away_team} [Status: {m.status}]")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_arsenal()
