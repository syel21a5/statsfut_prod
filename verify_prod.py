import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Team, Match, Season

print("--- LEAGUES ---")
for l in League.objects.all():
    print(f"ID: {l.id} | {l.name} ({l.country})")

print("\n--- SEASONS ---")
for s in Season.objects.all().order_by('-year'):
    print(f"ID: {s.id} | Year: {s.year}")

print("\n--- DATA CHECKS ---")
for country in ['Australia', 'Austria']:
    leagues = League.objects.filter(country=country)
    for l in leagues:
        teams = Team.objects.filter(league=l)
        matches = Match.objects.filter(league=l)
        print(f"League: {l.name} ({l.country})")
        print(f"  Teams: {teams.count()}")
        print(f"  Matches: {matches.count()}")
        
        t = teams.first()
        if t:
            from matches.templatetags.team_tags import get_team_logo
            print(f"  Sample Team: {t.name} (API: {t.api_id})")
            print(f"  get_team_logo: {get_team_logo(t)}")
    print("-" * 20)
