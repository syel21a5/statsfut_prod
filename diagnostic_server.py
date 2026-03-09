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
    
    for l in leagues:
        teams = Team.objects.filter(league=l).order_by('name')
        print(f"  -> League ID: {l.id} | Total Teams: {teams.count()}")
        print(f"     All Teams: {[t.name for t in teams]}")

print("=== SERVER FULL TEAM LIST ===")
check_league('Bundesliga', 'Austria')
check_league('Brasileirão', 'Brasil')
check_league('Superliga', 'Dinamarca')
check_league('Pro League', 'Belgica')
