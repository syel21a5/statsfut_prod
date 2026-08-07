import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Team, Match

def verify_australia():
    print("--- Verifying Australia A-League Men ---")
    try:
        league = League.objects.get(country__iexact='Australia', name='A-League Men')
    except Exception as e:
        print(f"League not found: {e}")
        return

    teams = Team.objects.filter(league=league)
    print(f"Total Teams: {teams.count()}")
    print(f"Teams: {[t.name for t in teams]}")
    
    matches = Match.objects.filter(league=league)
    print(f"Total Matches: {matches.count()}")
    
    seasons = Match.objects.filter(league=league).values_list('season__year', flat=True).distinct().order_by('season__year')
    print(f"Seasons: {list(seasons)}")
    
    # Check for Rugby teams just in case
    rugby_teams = teams.filter(name__icontains='Stade Toulousain')
    if rugby_teams.exists():
        print("CRITICAL: Rugby teams still present!")
    else:
        print("Success: No Rugby teams found.")

if __name__ == '__main__':
    verify_australia()
