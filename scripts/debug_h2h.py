import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, League, Match
from django.db.models import Q
from django.utils.text import slugify

def debug_h2h(country_slug, league_slug, team1_slug, team2_slug):
    print(f"Debug H2H: {country_slug} / {league_slug} / {team1_slug} vs {team2_slug}")
    
    # 1. League
    name = league_slug.replace('-', ' ')
    leagues = League.objects.filter(Q(name__iexact=name) | Q(name__iexact=league_slug))
    print(f"Leagues matching '{name}': {leagues.count()}")
    for l in leagues:
        print(f"  - ID: {l.id}, Name: {l.name}, Country: {l.country}")
    
    # Filter by country
    country_clean = country_slug.replace('-', ' ')
    from matches.utils import COUNTRY_REVERSE_TRANSLATIONS
    db_country = COUNTRY_REVERSE_TRANSLATIONS.get(country_clean.lower(), country_clean)
    print(f"Searching for country: {db_country}")
    
    league = leagues.filter(country__iexact=db_country).first()
    if not league:
        print("League NOT found with country filter!")
        return
    
    print(f"Found League: {league.name} (ID: {league.id})")
    
    # 2. Teams
    def find_team(slug, lg):
        name = slug.replace('-', ' ')
        t = Team.objects.filter(league=lg, name__iexact=name).first()
        if not t:
            t = Team.objects.filter(league=lg, name__icontains=name).first()
        if not t:
            # Try global fallback
            t = Team.objects.filter(name__iexact=name).first()
        return t

    t1 = find_team(team1_slug, league)
    t2 = find_team(team2_slug, league)
    
    print(f"Team 1: {t1.name if t1 else 'NOT FOUND'} (ID: {t1.id if t1 else 'N/A'})")
    print(f"Team 2: {t2.name if t2 else 'NOT FOUND'} (ID: {t2.id if t2 else 'N/A'})")
    
    if not t1 or not t2:
        return

    # 3. Matches
    FINISHED_STATUSES = ['Finished', 'FT', 'AET', 'PEN', 'FINISHED']
    matches = Match.objects.filter(
        (Q(home_team=t1) & Q(away_team=t2)) |
        (Q(home_team=t2) & Q(away_team=t1))
    ).filter(status__in=FINISHED_STATUSES).order_by('-date')
    
    print(f"H2H Matches found: {matches.count()}")
    for m in matches[:5]:
        print(f"  - {m.date}: {m.home_team.name} {m.home_score}-{m.away_score} {m.away_team.name} ({m.status})")

if __name__ == "__main__":
    debug_h2h('switzerland', 'super-league', 'fc-st-gallen-1879', 'basel')
