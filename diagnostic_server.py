import os
import django
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import League, Team

def check_league(db_name, country):
    print(f"\n--- Checking League: {db_name} ({country}) ---")
    leagues = League.objects.filter(name__iexact=db_name, country__iexact=country)
    print(f"Found {leagues.count()} leagues with this (exact/iexact) name/country.")
    
    # Try case/accent insensitive and partial
    if leagues.count() == 0:
        print("Searching for partial match...")
        partial = League.objects.filter(name__icontains=db_name, country__icontains=country)
        print(f"Partial matches found: {partial.count()}")
        for l in partial:
            print(f"  ? League ID: {l.id} | Name: [{l.name}] | Country: [{l.country}]")
    
    for l in leagues:
        teams_count = Team.objects.filter(league=l).count()
        print(f"  -> League ID: {l.id} | Teams: {teams_count}")
        if teams_count > 0:
            print(f"     Sample teams: {[t.name for t in Team.objects.filter(league=l)[:5]]}")

print("=== SERVER DIAGNOSTIC STATSFUT ===")
check_league('Bundesliga', 'Austria')
check_league('Brasileirão', 'Brasil')
check_league('A-League Men', 'Australia')
check_league('Superliga', 'Dinamarca')
check_league('Pro League', 'Belgica')
