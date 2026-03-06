
import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from matches.models import Team

print("Searching for teams with name containing 'Brondby'...")
teams = Team.objects.filter(name__icontains='Brondby')

if not teams.exists():
    print("No teams found.")
else:
    print(f"{'ID':<6} {'Name':<30} {'League':<30} {'League ID':<10}")
    for t in teams:
        print(f"{t.id:<6} {t.name:<30} {t.league.name:<30} {t.league.id:<10}")

print("\nSearching for teams with name containing 'Copenhagen'...")
teams = Team.objects.filter(name__icontains='Copenhagen')
if not teams.exists():
    print("No teams found.")
else:
    for t in teams:
        print(f"{t.id:<6} {t.name:<30} {t.league.name:<30} {t.league.id:<10}")
