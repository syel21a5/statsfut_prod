
import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from matches.models import Team

team_ids = [515, 519, 510, 514, 512, 525] # IDs from previous investigation (Brondby, FC Copenhagen, Midtjylland, Aarhus, Odense, Vejle)

print(f"{'ID':<6} {'Name':<20} {'League':<30} {'League ID':<10}")
print("-" * 70)

for tid in team_ids:
    try:
        t = Team.objects.get(id=tid)
        print(f"{t.id:<6} {t.name:<20} {t.league.name:<30} {t.league.id:<10}")
    except Team.DoesNotExist:
        print(f"{tid:<6} {'NOT FOUND':<20}")
