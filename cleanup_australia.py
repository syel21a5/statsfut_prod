import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Team, Match, LeagueStanding

def cleanup_australia():
    print("--- Cleaning up Australia league ---")
    
    # Identify the league
    try:
        league = League.objects.get(country__iexact='Australia', name='A-League Men')
    except League.DoesNotExist:
        print("League 'A-League Men' (Australia) not found.")
        return
    except League.MultipleObjectsReturned:
        print("Multiple leagues found, cleaning all.")
        leagues = League.objects.filter(country__iexact='Australia', name='A-League Men')
        for l in leagues:
             clean_league(l)
        return

    clean_league(league)

def clean_league(league):
    print(f"Cleaning League: {league.name} (ID: {league.id})")
    
    # 1. Delete Standings
    s_count = LeagueStanding.objects.filter(league=league).count()
    LeagueStanding.objects.filter(league=league).delete()
    print(f"Deleted {s_count} standings.")
    
    # 2. Delete Matches
    m_count = Match.objects.filter(league=league).count()
    Match.objects.filter(league=league).delete()
    print(f"Deleted {m_count} matches.")
    
    # 3. Delete Teams
    t_count = Team.objects.filter(league=league).count()
    Team.objects.filter(league=league).delete()
    print(f"Deleted {t_count} teams.")

if __name__ == '__main__':
    cleanup_australia()
