import os
import django
import sys
from django.db.models import Q

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from matches.models import Team, League, Match

def inspect_all_leagues():
    print("Listing all leagues...")
    for l in League.objects.all():
        print(f"ID: {l.id} | Name: {l.name} | Country: {l.country}")

    print("\n--- Searching for Spain ---")
    leagues = League.objects.filter(country__icontains='Spain')
    print(f"Found {leagues.count()} leagues with country 'Spain'")
    
    leagues_name = League.objects.filter(name__icontains='La Liga')
    print(f"Found {leagues_name.count()} leagues with name 'La Liga'")

if __name__ == "__main__":
    inspect_all_leagues()
